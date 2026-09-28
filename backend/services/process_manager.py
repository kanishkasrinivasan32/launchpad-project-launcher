import codecs
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import signal
import socket
import subprocess
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener

import psutil
from fastapi import HTTPException
from sqlalchemy import select

from backend.config import settings
from backend.database.db import SessionLocal
from backend.database.models import ProcessMetric, ProjectSession, now_iso
from backend.services.browser_service import open_browser
from backend.services.monitoring_service import sample_processes
from backend.services.project_service import as_dict, get_project
from backend.services.windows_job import WindowsJob
from backend.services.port_service import choose_port, command_for_port, url_port, with_port

logger = logging.getLogger(__name__)
ACTIVE = ('starting', 'running', 'stopping')


def port_in_use(url):
    parsed = urlsplit(url)
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    # Check IPv4 and IPv6 loopback to catch localhost/address alias conflicts.
    for host in ('127.0.0.1', '::1'):
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return True
        except OSError:
            pass
    return False


def http_ready(url):
    try:
        # Do not send local requests through environment-configured proxies.
        with build_opener(ProxyHandler({})).open(url, timeout=0.6) as response:
            return response.status < 500
    except HTTPError as exc:
        # Auth and missing root routes still prove that the HTTP server is up.
        return exc.code < 500
    except (URLError, OSError, ValueError):
        return False


class RunningProcess:
    def __init__(self, session_id, project, process, job):
        self.session_id = session_id
        self.project = project
        self.process = process
        self.job = job
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.started = time.monotonic()
        self.status = 'starting'
        self.known = {}
        self.samples = 0
        self.cpu_sum = 0.0
        self.ram_sum = 0.0
        self.reader_threads = []
        log_dir = settings.storage / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f'{session_id}.log'
        # Also protect older databases whose SQLite row IDs can be reused after deletion.
        log_path.write_text('', encoding='utf-8')
        log_path.with_suffix('.log.1').unlink(missing_ok=True)
        self.log = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=1, encoding='utf-8')
        self.log.setFormatter(logging.Formatter('%(message)s'))

    def log_text(self, text):
        self.log.handle(logging.LogRecord('project', logging.INFO, '', 0, text, (), None))

    def read_pipe(self, pipe, label):
        decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        try:
            while data := pipe.read1(4096):
                self.log_text(f'[{label}] ' + decoder.decode(data))
            tail = decoder.decode(b'', final=True)
            if tail:
                self.log_text(f'[{label}] ' + tail)
        except (OSError, ValueError):
            pass
        finally:
            pipe.close()

    def processes(self):
        pids = self.job.pids() if os.name == 'nt' else [self.process.pid]
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                key = (pid, proc.create_time())
                if key not in self.known:
                    proc.cpu_percent(None)
                    self.known[key] = proc
            except psutil.NoSuchProcess:
                pass
        for proc in list(self.known.values()):
            try:
                for child in proc.children(recursive=True):
                    key = (child.pid, child.create_time())
                    if key not in self.known:
                        child.cpu_percent(None)
                        self.known[key] = child
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return list(self.known.values())

    def owns_port(self):
        port = url_port(self.project['url'])
        for process in self.processes():
            try:
                if any(c.status == psutil.CONN_LISTEN and c.laddr.port == port
                       for c in process.net_connections(kind='inet')):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def terminate(self):
        processes = self.processes()
        # Stop children before their shell; the Windows job catches late descendants.
        for proc in reversed(processes):
            try:
                proc.terminate()
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                logger.warning('Unable to terminate PID %s gracefully', proc.pid)
        _, alive = psutil.wait_procs(processes, timeout=2)
        for proc in alive:
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass
        if os.name != 'nt':
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.job.close()
        self.process.wait(timeout=5)
        for thread in self.reader_threads:
            thread.join(timeout=1)


class ProcessManager:
    def __init__(self):
        self.guard = threading.RLock()
        self.handles = {}
        self.closing = False

    def active_for(self, project_id):
        with SessionLocal() as db:
            return db.scalars(select(ProjectSession).where(ProjectSession.project_id == project_id, ProjectSession.ended_at.is_(None))).first()

    def launch(self, project_id):
        with self.guard:
            if self.closing:
                raise HTTPException(503, 'The dashboard is shutting down.')
            project = get_project(project_id)
            if self.active_for(project_id):
                raise HTTPException(409, 'This project is already starting or running.')
            if not Path(project['folder']).is_dir():
                raise HTTPException(400, 'Project folder is missing. Edit the project and choose an existing folder.')
            reserved = [url_port(running.project['url']) for running in list(self.handles.values()) if running.status in ACTIVE]
            try:
                port = choose_port(url_port(project['url']), reserved)
            except RuntimeError as exc:
                raise HTTPException(409, str(exc)) from None
            command, port_env = command_for_port(project['startup_command'], project['folder'], port)
            project = {**project, 'url': with_port(project['url'], port), 'startup_command': command}
            with SessionLocal.begin() as db:
                session = ProjectSession(project_id=project_id, actual_url=project['url'], actual_command=command)
                db.add(session)
                db.flush()
                session_id = session.id
            process = None
            job = None
            try:
                env = os.environ.copy()
                env.update(port_env)
                env['PYTHONUNBUFFERED'] = '1'
                # Do not inherit the dashboard virtualenv as the project's environment.
                env.pop('VIRTUAL_ENV', None)
                if os.name == 'nt' and 'powershell' in command.lower():
                    # Windows PowerShell must build its own module paths instead of
                    # inheriting incompatible PowerShell 7 paths from the dashboard shell.
                    for key in list(env):
                        if key.lower() == 'psmodulepath':
                            env.pop(key)
                process = subprocess.Popen(
                    project['startup_command'], cwd=project['folder'], shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                    env=env, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                    start_new_session=os.name != 'nt',
                )
                job = WindowsJob(process.pid)
                handle = RunningProcess(session_id, project, process, job)
                handle.log_text(f'[launcher] Selected free port {port}: {project["url"]}\n[launcher] {command}')
                self.handles[session_id] = handle
                with SessionLocal.begin() as db:
                    db.get(ProjectSession, session_id).pid = process.pid
                for pipe, label in ((process.stdout, 'stdout'), (process.stderr, 'stderr')):
                    thread = threading.Thread(target=handle.read_pipe, args=(pipe, label), daemon=True)
                    handle.reader_threads.append(thread)
                    thread.start()
                handle.worker = threading.Thread(target=self._watch, args=(handle,), daemon=True)
                handle.worker.start()
                return self.status(session_id)
            except Exception:
                logger.exception('Project %s failed to start', project_id)
                failed_handle = self.handles.pop(session_id, None)
                if failed_handle:
                    failed_handle.stop_event.set()
                if job:
                    job.close()
                if process:
                    try:
                        parent = psutil.Process(process.pid)
                        for child in parent.children(recursive=True):
                            child.kill()
                        parent.kill()
                    except psutil.NoSuchProcess:
                        pass
                    process.wait(timeout=5)
                    for pipe in (process.stdout, process.stderr):
                        if pipe:
                            pipe.close()
                if failed_handle:
                    failed_handle.log.close()
                with SessionLocal.begin() as db:
                    session = db.get(ProjectSession, session_id)
                    session.status = 'failed'
                    session.ended_at = now_iso()
                    session.error = 'Could not start the command. Check the command, folder permissions, and installed tools.'
                raise HTTPException(400, 'Could not start the command. Check the command, folder permissions, and installed tools.') from None

    def _watch(self, handle):
        try:
            while not handle.stop_event.is_set():
                with handle.lock:
                    if handle.status not in ACTIVE:
                        return
                    cpu, ram, live = sample_processes(handle.processes())
                    elapsed = time.monotonic() - handle.started
                    if not live:
                        code = handle.process.poll()
                        self._finish(handle, 'failed' if handle.status == 'starting' or code not in (0, None) else 'stopped',
                                     f'The startup command exited (code {code}). Check the captured logs.' if handle.status == 'starting' or code not in (0, None) else None)
                        return
                    if handle.status == 'starting':
                        if handle.owns_port() and http_ready(handle.project['url']):
                            handle.status = 'running'
                            warning = None
                            try:
                                warning = open_browser(handle.project['url'])
                            except Exception:
                                logger.exception('Could not open browser')
                                warning = 'Project is running, but the browser could not open. Use Open app.'
                            with SessionLocal.begin() as db:
                                db.get(ProjectSession, handle.session_id).browser_warning = warning
                        elif elapsed >= settings.startup_timeout:
                            self._finish(handle, 'failed', f'No HTTP response from this project within {settings.startup_timeout:g} seconds at {handle.project["url"]}. For a custom command, use {{port}} in its port argument or read the PORT environment variable. The process tree was stopped.')
                            return
                    handle.samples += 1
                    handle.cpu_sum += cpu
                    handle.ram_sum += ram
                    with SessionLocal.begin() as db:
                        session = db.get(ProjectSession, handle.session_id)
                        session.status = handle.status
                        session.total_runtime = int(elapsed)
                        session.avg_cpu = handle.cpu_sum / handle.samples
                        session.avg_ram = handle.ram_sum / handle.samples
                        db.add(ProcessMetric(session_id=handle.session_id, cpu_percent=cpu, ram_mb=ram, pid=handle.process.pid))
                handle.stop_event.wait(settings.monitor_interval)
        except Exception:
            logger.exception('Monitoring failed for session %s', handle.session_id)
            with handle.lock:
                self._finish(handle, 'failed', 'Monitoring encountered an error. The project was stopped; see dashboard logs for details.')

    def _finish(self, handle, status, error=None):
        if handle.status not in ACTIVE:
            return
        handle.stop_event.set()
        handle.terminate()
        handle.status = status
        with SessionLocal.begin() as db:
            session = db.get(ProjectSession, handle.session_id)
            session.status = status
            session.error = error
            session.ended_at = now_iso()
            session.total_runtime = int(time.monotonic() - handle.started)
        handle.log_text(f'[launcher] {error or "Project stopped."}')
        handle.log.close()
        self.handles.pop(handle.session_id, None)

    def stop(self, session_id):
        handle = self.handles.get(session_id)
        if handle:
            with handle.lock:
                self._finish(handle, 'stopped')
        return self.status(session_id)

    def status(self, session_id):
        with SessionLocal() as db:
            session = db.get(ProjectSession, session_id)
            if not session:
                raise HTTPException(404, 'Session not found.')
            result = as_dict(session)
            latest = db.scalars(select(ProcessMetric).where(ProcessMetric.session_id == session_id).order_by(ProcessMetric.id.desc()).limit(1)).first()
            handle = self.handles.get(session_id)
            active = session.ended_at is None and handle is not None
            result.update(runtime_seconds=int(time.monotonic() - handle.started) if active else session.total_runtime,
                          cpu_percent=latest.cpu_percent if active and latest else 0,
                          ram_mb=latest.ram_mb if active and latest else 0)
            return result

    def shutdown(self):
        with self.guard:
            self.closing = True
        handles = list(self.handles.values())
        for handle in handles:
            self.stop(handle.session_id)
        for handle in handles:
            handle.worker.join(timeout=3)


manager = ProcessManager()
