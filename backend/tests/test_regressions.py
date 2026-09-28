from datetime import datetime, timedelta, timezone
import sys
import time
from pathlib import Path
import shutil
import psutil

from backend.database.db import SessionLocal
from backend.database.models import ProjectSession, Project
from backend.services.instance_lock import acquire_instance_lock
from backend.tests.test_lifecycle import project, wait_status, free_port
import pytest


def test_port_is_reserved_while_starting_and_finished_project_can_be_deleted(client, tmp_path):
    script = tmp_path / 'sleep.py'
    script.write_text('import time\ntime.sleep(120)\n')
    port = free_port()
    first, _ = project(client, tmp_path, f'"{sys.executable}" "{script}"', port=port)
    second, _ = project(client, tmp_path, port=port)
    session = client.post(f'/api/launcher/launch/{first["id"]}').json()
    try:
        response = client.post(f'/api/launcher/launch/{second["id"]}')
        assert response.status_code == 202, response.text
        try:
            running = wait_status(client, response.json()['id'], 'running')
            assert running['actual_url'] != session['actual_url']
        finally:
            client.post(f'/api/launcher/stop/{response.json()["id"]}')
    finally:
        client.post(f'/api/launcher/stop/{session["id"]}')
    assert client.delete(f'/api/projects/{first["id"]}').status_code == 204
    # Shutdown must not retain a deleted session or kill a recycled stored PID.
    from backend.services.process_manager import manager
    assert session['id'] not in manager.handles


def test_duplicate_backend_lock(client):
    with pytest.raises(RuntimeError, match='already using'):
        acquire_instance_lock()


def test_cross_midnight_summary(client, tmp_path):
    p, _ = project(client, tmp_path)
    midnight = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    # Only the part after local midnight belongs in today's total.
    before = client.get('/api/summary').json()['runtime_today']
    with SessionLocal.begin() as db:
        db.add(ProjectSession(project_id=p['id'], started_at=(midnight - timedelta(seconds=120)).isoformat(),
                              ended_at=(midnight + timedelta(seconds=120)).isoformat(), total_runtime=240, status='stopped'))
    after = client.get('/api/summary').json()['runtime_today']
    assert after - before == 120
    assert client.delete(f'/api/projects/{p["id"]}').status_code == 204


def test_real_npm_vite_process_tree(client, monkeypatch):
    frontend = Path(__file__).resolve().parents[2] / 'frontend'
    if not shutil.which('npm') or not (frontend / 'node_modules/vite').is_dir():
        pytest.skip('Install frontend dependencies and Node.js to verify the real Vite tree.')
    from backend.config import settings
    from backend.services.process_manager import port_in_use
    monkeypatch.setattr(settings, 'startup_timeout', 20)
    port = free_port()
    p, _ = project(client, frontend, f'npm run dev -- --host 127.0.0.1 --port {port} --strictPort', port=port)
    response = client.post(f'/api/launcher/launch/{p["id"]}')
    assert response.status_code == 202, response.text
    session_id = response.json()['id']
    try:
        running = wait_status(client, session_id, 'running', timeout=25)
        root = psutil.Process(running['pid'])
        tree = [root, *root.children(recursive=True)]
        assert any('node' in proc.name().lower() for proc in tree)
        assert running['ram_mb'] > 0
    finally:
        assert client.post(f'/api/launcher/stop/{session_id}').status_code == 200
    assert all(not proc.is_running() for proc in tree)
    assert not port_in_use(p['url'])


def test_new_session_never_replays_stale_log_file(client, tmp_path):
    from backend.config import settings
    from sqlalchemy import func, select
    with SessionLocal() as db:
        next_id = db.scalar(select(func.max(ProjectSession.id))) + 1
    log_dir = settings.storage / 'logs'
    log_dir.mkdir(exist_ok=True)
    stale = log_dir / f'{next_id}.log'
    stale.write_text('OLD_SESSION_SECRET_SHOULD_NOT_APPEAR')
    p, _ = project(client, tmp_path)
    response = client.post(f'/api/launcher/launch/{p["id"]}')
    assert response.status_code == 202, response.text
    session_id = response.json()['id']
    try:
        wait_status(client, session_id, 'running')
        content = client.get(f'/api/monitoring/{session_id}/logs').json()['content']
        assert 'OLD_SESSION_SECRET_SHOULD_NOT_APPEAR' not in content
    finally:
        client.post(f'/api/launcher/stop/{session_id}')
