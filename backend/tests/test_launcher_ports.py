import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import httpx
import psutil
import pytest


def test_dashboard_falls_back_and_reuses_saved_ports(tmp_path):
    root = Path(__file__).resolve().parents[2]
    if os.name != 'nt' or not (root / 'frontend/node_modules/vite').is_dir():
        pytest.skip('Windows and installed frontend dependencies required')
    with socket.socket() as backend_block, socket.socket() as frontend_block:
        backend_block.bind(('127.0.0.1', 0))
        frontend_block.bind(('127.0.0.1', 0))
        backend_port, frontend_port = backend_block.getsockname()[1], frontend_block.getsockname()[1]
        data = tmp_path / 'dashboard'
        env = {**os.environ, 'DATA_DIR': str(data), 'AUTO_OPEN_BROWSER': 'false',
               'BACKEND_PORT': str(backend_port), 'FRONTEND_URL': f'http://localhost:{frontend_port}'}
        command = [sys.executable, '-c', 'from scripts.launcher import main; main()']
        state_file = data / 'dashboard-processes.json'
        try:
            start = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=60)
            assert start.returncode == 0, start.stdout + start.stderr
            state = json.loads(state_file.read_text())
            assert state['backend']['url'] != f'http://127.0.0.1:{backend_port}'
            assert state['frontend']['url'] != f'http://localhost:{frontend_port}'
            with httpx.Client(trust_env=False) as client:
                # Vite proxy must point at the newly selected backend port.
                response = client.get(state['frontend']['url'] + '/api/health')
                assert response.json()['application'] == 'project-launcher'
                preflight = client.options(state['backend']['url'] + '/api/projects', headers={
                    'Origin': state['frontend']['url'], 'Access-Control-Request-Method': 'POST'})
                assert preflight.status_code == 200
                assert preflight.headers['access-control-allow-origin'] == state['frontend']['url']
            repeated = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=30)
            assert repeated.returncode == 0, repeated.stderr
            assert json.loads(state_file.read_text()) == state
        finally:
            stop = subprocess.run(command + ['--stop'], cwd=root, env=env, capture_output=True, text=True, timeout=30)
            assert stop.returncode == 0, stop.stderr
        assert not state_file.exists()
        for record in state.values():
            try:
                assert abs(psutil.Process(record['pid']).create_time() - record['created']) > .01
            except psutil.NoSuchProcess:
                pass
