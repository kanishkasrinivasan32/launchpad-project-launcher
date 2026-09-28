from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import psutil
import pytest

from backend.config import settings
from backend.database.db import SessionLocal
from backend.database.models import ProcessMetric, ProjectSession
from backend.services import process_manager


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def eventually(fn, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(0.1)
    raise AssertionError('Condition did not become true before timeout.')


def project(client, tmp_path, command=None, port=None):
    port = port or free_port()
    payload = {'name': 'Integration project', 'folder': str(tmp_path),
               'startup_command': command or f'"{sys.executable}" -u -m http.server {port} --bind 127.0.0.1',
               'url': f'http://127.0.0.1:{port}', 'type': 'Python'}
    response = client.post('/api/projects', json=payload)
    assert response.status_code == 201, response.text
    return response.json(), payload


def wait_status(client, session_id, expected, timeout=10):
    def check():
        status = client.get(f'/api/monitoring/{session_id}').json()
        return status if status['status'] == expected else False
    return eventually(check, timeout)


def test_launch_monitor_browser_stop_and_persist(client, tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(process_manager, 'open_browser', lambda url: opened.append(url))
    p, _ = project(client, tmp_path)
    launch = client.post(f'/api/launcher/launch/{p["id"]}')
    assert launch.status_code == 202, launch.text
    session_id = launch.json()['id']
    try:
        running = wait_status(client, session_id, 'running')
        assert opened == [p['url']]
        assert running['ram_mb'] > 0
        assert running['pid'] > 0
        assert client.post(f'/api/launcher/launch/{p["id"]}').status_code == 409
        assert client.delete(f'/api/projects/{p["id"]}').status_code == 409
        eventually(lambda: client.get(f'/api/monitoring/{session_id}').json()['runtime_seconds'] >= 1)
        logs = eventually(lambda: (text if 'Serving HTTP' in (text := client.get(f'/api/monitoring/{session_id}/logs').json()['content']) else False))
        assert 'Serving HTTP' in logs
        summary = client.get('/api/summary').json()
        assert summary['running_count'] >= 1 and summary['runtime_today'] >= 1
        root = psutil.Process(running['pid'])
        tree = [root, *root.children(recursive=True)]
    finally:
        stopped = client.post(f'/api/launcher/stop/{session_id}')
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()['status'] == 'stopped'
    assert all(not proc.is_running() for proc in tree)
    assert not process_manager.port_in_use(p['url'])
    assert client.post(f'/api/launcher/stop/{session_id}').status_code == 200
    with SessionLocal() as db:
        persisted = db.get(ProjectSession, session_id)
        assert persisted.ended_at and persisted.total_runtime >= 1 and persisted.avg_ram > 0
        assert db.query(ProcessMetric).filter_by(session_id=session_id).count() > 0


def test_port_conflict_selects_new_port_without_killing_external_process(client, tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(process_manager, 'open_browser', lambda url: opened.append(url))
    port = free_port()
    external = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        p, _ = project(client, tmp_path, port=port)
        eventually(lambda: process_manager.port_in_use(p['url']))
        result = client.post(f'/api/launcher/launch/{p["id"]}')
        assert result.status_code == 202, result.text
        session_id = result.json()['id']
        try:
            running = wait_status(client, session_id, 'running')
            assert running['actual_url'] != p['url']
            assert opened == [running['actual_url']]
            assert process_manager.http_ready(running['actual_url'])
            assert client.get(f'/api/projects/{p["id"]}').json()['url'] == p['url']
        finally:
            client.post(f'/api/launcher/stop/{session_id}')
        assert external.poll() is None
    finally:
        external.terminate()
        external.wait(timeout=5)


def test_timeout_and_stop_during_startup(client, tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(process_manager, 'open_browser', lambda url: opened.append(url))
    monkeypatch.setattr(settings, 'startup_timeout', 1)
    script = tmp_path / 'sleep.py'
    script.write_text('import time\nprint("waiting", flush=True)\ntime.sleep(120)\n')
    p, _ = project(client, tmp_path, f'"{sys.executable}" -u "{script}"')
    first = client.post(f'/api/launcher/launch/{p["id"]}').json()
    failed = wait_status(client, first['id'], 'failed')
    assert 'No HTTP response' in failed['error']
    assert not psutil.pid_exists(first['pid'])
    assert not opened
    second = client.post(f'/api/launcher/launch/{p["id"]}').json()
    assert client.post(f'/api/launcher/stop/{second["id"]}').json()['status'] == 'stopped'
    assert not psutil.pid_exists(second['pid'])


def test_child_tree_survives_shell_and_is_stopped(client, tmp_path):
    port = free_port()
    child = tmp_path / 'spawn.py'
    child.write_text('import subprocess, sys, time\n' +
                     f'p = subprocess.Popen([sys.executable, "-u", "-m", "http.server", "{port}", "--bind", "127.0.0.1"])\n' +
                     'print("CHILD_PID=" + str(p.pid), flush=True)\ntime.sleep(0.6)\n')
    p, _ = project(client, tmp_path, f'"{sys.executable}" -u "{child}"', port)
    started = client.post(f'/api/launcher/launch/{p["id"]}')
    assert started.status_code == 202, started.text
    session_id = started.json()['id']
    try:
        wait_status(client, session_id, 'running')
        time.sleep(1)
        assert client.get(f'/api/monitoring/{session_id}').json()['status'] == 'running'
        contents = client.get(f'/api/monitoring/{session_id}/logs').json()['content']
        child_pid = int(contents.split('CHILD_PID=')[1].split()[0])
        assert psutil.pid_exists(child_pid)
    finally:
        client.post(f'/api/launcher/stop/{session_id}')
    assert not psutil.pid_exists(child_pid)
    assert not process_manager.port_in_use(p['url'])


def test_restart_and_concurrent_duplicate_launch(client, tmp_path):
    p, _ = project(client, tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post(f'/api/launcher/launch/{p["id"]}'), range(2)))
    assert sorted(r.status_code for r in responses) == [202, 409]
    session_id = next(r.json()['id'] for r in responses if r.status_code == 202)
    wait_status(client, session_id, 'running')
    restarted = client.post(f'/api/launcher/restart/{p["id"]}')
    assert restarted.status_code == 202, restarted.text
    new_id = restarted.json()['id']
    try:
        assert new_id != session_id
        wait_status(client, new_id, 'running')
        assert client.get(f'/api/monitoring/{session_id}').json()['status'] == 'stopped'
    finally:
        client.post(f'/api/launcher/stop/{new_id}')


def test_crud_validation_and_local_boundary(client, tmp_path):
    p, payload = project(client, tmp_path)
    assert client.get(f'/api/projects/{p["id"]}').json()['name'] == payload['name']
    payload['name'] = 'Renamed project'
    assert client.put(f'/api/projects/{p["id"]}', json=payload).json()['name'] == payload['name']
    for url in ('https://example.com', 'file:///etc/passwd', 'http://localhost:99999', 'http://user@localhost:3000'):
        assert client.post('/api/projects', json={**payload, 'url': url}).status_code == 422
    assert client.post('/api/projects', json={**payload, 'folder': str(tmp_path / 'missing')}).status_code == 422
    assert client.post('/api/projects', json={**payload, 'name': '  '}).status_code == 422
    assert client.post(f'/api/launcher/launch/{p["id"]}', headers={'Origin': 'https://untrusted.example'}).status_code == 403
    assert client.get('/api/projects', headers={'Host': 'untrusted.example'}).status_code == 400
    assert client.delete(f'/api/projects/{p["id"]}').status_code == 204
    assert client.get(f'/api/projects/{p["id"]}').status_code == 404
    assert client.get('/api/monitoring/999999').status_code == 404


def test_bad_command_captures_stderr(client, tmp_path):
    script = tmp_path / 'fail.py'
    script.write_text('import sys, time\nprint("intentional failure", file=sys.stderr, flush=True)\ntime.sleep(0.3)\nsys.exit(7)\n')
    p, _ = project(client, tmp_path, f'"{sys.executable}" -u "{script}"')
    response = client.post(f'/api/launcher/launch/{p["id"]}')
    assert response.status_code == 202, response.text
    failed = wait_status(client, response.json()['id'], 'failed')
    assert 'exited' in failed['error']
    assert 'intentional failure' in client.get(f'/api/monitoring/{failed["id"]}/logs').json()['content']
