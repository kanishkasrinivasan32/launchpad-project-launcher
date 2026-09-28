"""Local dashboard bootstrap. Only processes recorded by this launcher are stopped."""
import json
import logging
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, ProxyHandler, build_opener
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psutil
from backend.config import settings
from backend.services.browser_service import open_browser
from backend.services.port_service import choose_port, url_port, with_port

settings.storage.mkdir(parents=True, exist_ok=True)
STATE_FILE = settings.storage / 'dashboard-processes.json'
BASE = f'http://127.0.0.1:{settings.backend_port}'
logging.basicConfig(filename=settings.storage / 'launcher.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
opener = build_opener(ProxyHandler({}))


def request(url, method='GET'):
    with opener.open(Request(url, method=method, headers={'X-Launchpad-Request': '1'}), timeout=15 if method == 'POST' else 2) as response:
        return response.read().decode('utf-8')


def backend_ready(url=None):
    try:
        return json.loads(request((url or BASE) + '/api/health')).get('application') == 'project-launcher'
    except (OSError, ValueError, URLError):
        return False


def frontend_ready(url=None):
    try:
        return 'Launchpad · Project Launcher' in request(url or settings.frontend_url)
    except (OSError, URLError):
        return False


def occupied(url):
    parsed = urlsplit(url)
    try:
        with socket.create_connection((parsed.hostname, parsed.port or 80), timeout=0.5):
            return True
    except OSError:
        return False


def wait_for(check, process):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if check():
            return
        if process.poll() is not None:
            raise RuntimeError('A dashboard server exited during startup. See data/launcher-servers.log.')
        time.sleep(0.3)
    raise RuntimeError('A dashboard server did not become ready within 45 seconds. See data/launcher-servers.log.')


def start(args, cwd, stream, env=None):
    process = subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                               env=env,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    return process, {'pid': process.pid, 'created': psutil.Process(process.pid).create_time()}


def stop_record(record):
    try:
        process = psutil.Process(record['pid'])
        if abs(process.create_time() - record['created']) > 0.01:
            return
        tree = [*process.children(recursive=True), process]
        for item in tree:
            try:
                item.terminate()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(tree, timeout=3)
        for item in alive:
            item.kill()
    except psutil.NoSuchProcess:
        pass


def record_alive(record):
    try:
        return bool(record) and abs(psutil.Process(record['pid']).create_time() - record['created']) < 0.01
    except (psutil.NoSuchProcess, KeyError):
        return False


def save_state(state):
    temporary = STATE_FILE.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, indent=2))
    temporary.replace(STATE_FILE)


def main():
    global BASE
    # Serialize double clicks so they cannot start a duplicate pair of servers.
    lock = (settings.storage / 'launcher.lock').open('a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            lock.seek(0); lock.write(b'0'); lock.flush(); lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
        BASE = state.get('backend', {}).get('url', BASE)
        settings.frontend_url = state.get('frontend', {}).get('url', settings.frontend_url)
        if '--stop' in sys.argv:
            if not state:
                print('No dashboard processes were started by this launcher.')
                return
            # Finish project sessions before terminating the owned backend.
            backend = state.get('backend')
            if backend and backend_ready():
                try:
                    process = psutil.Process(backend['pid'])
                    if abs(process.create_time() - backend['created']) < 0.01:
                        summary = json.loads(request(BASE + '/api/summary'))
                        for session in summary['sessions']:
                            request(BASE + f'/api/launcher/stop/{session["id"]}', 'POST')
                except psutil.NoSuchProcess:
                    pass
            for record in state.values():
                stop_record(record)
            STATE_FILE.unlink(missing_ok=True)
            print('Dashboard stopped. Project sessions were saved.')
            return
        started = []
        try:
            # Saved endpoints matter on repeat launches: defaults may still be occupied.
            reuse_backend = record_alive(state.get('backend')) and backend_ready()
            reuse_frontend = record_alive(state.get('frontend')) and frontend_ready()
            backend_port = url_port(BASE) if reuse_backend else choose_port(settings.backend_port)
            frontend_port = url_port(settings.frontend_url) if reuse_frontend else choose_port(url_port(settings.frontend_url), [backend_port])
            BASE = f'http://127.0.0.1:{backend_port}'
            settings.frontend_url = with_port(settings.frontend_url, frontend_port)
            env = {**os.environ, 'BACKEND_PORT': str(backend_port), 'FRONTEND_URL': settings.frontend_url}
            if reuse_frontend and state.get('frontend', {}).get('backend_url', BASE) != BASE:
                stop_record(state['frontend'])
                reuse_frontend = False
            with (settings.storage / 'launcher-servers.log').open('ab') as stream:
                if not reuse_backend:
                    python = ROOT / '.venv/Scripts/python.exe'
                    process, record = start([str(python), '-m', 'backend.main'], ROOT, stream, env)
                    record['url'] = BASE
                    started.append(record); state['backend'] = record
                    wait_for(backend_ready, process)
                if not reuse_frontend:
                    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
                    if not npm:
                        raise RuntimeError('npm was not found. Install Node.js LTS and try again.')
                    # Run Vite directly, without a cmd wrapper, for dependable PID ownership.
                    node = shutil.which('node')
                    process, record = start([node, str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', str(frontend_port), '--strictPort'], ROOT / 'frontend', stream, env)
                    record.update(url=settings.frontend_url, backend_url=BASE)
                    started.append(record); state['frontend'] = record
                    wait_for(frontend_ready, process)
            state['backend']['url'] = BASE
            state['frontend'].update(url=settings.frontend_url, backend_url=BASE)
            save_state(state)
            warning = open_browser(settings.frontend_url)
            if warning:
                logging.warning(warning)
            logging.info('Dashboard ready at %s', settings.frontend_url)
        except Exception:
            for record in started:
                stop_record(record)
            raise
    except OSError as exc:
        if getattr(exc, 'winerror', None) in (33, 36) or getattr(exc, 'errno', None) == 13:
            logging.info('Another launcher is already starting the dashboard.')
            return
        raise
    finally:
        lock.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        logging.exception('Dashboard launch failed')
        if os.name == 'nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, f'{exc}\n\nDetails: {settings.storage / "launcher.log"}', 'Launchpad', 0x10)
        else:
            print(str(exc), file=sys.stderr)
        sys.exit(1)
