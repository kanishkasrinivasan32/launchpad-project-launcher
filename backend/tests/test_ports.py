import json
import os
import socket
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.services.port_service import choose_port, command_for_port, port_available, with_port, url_port
from backend.tests.test_lifecycle import project, free_port, wait_status


def test_bound_but_not_listening_port_is_skipped():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        assert not port_available(port)
        chosen = choose_port(port, [port + 1])
        assert chosen not in (port, port + 1)
        assert port_available(chosen)


@pytest.mark.parametrize('command,expected', [
    ('python -m http.server 8000 --bind 127.0.0.1', 'python -m http.server 4321 --bind 127.0.0.1'),
    ('python -m http.server --bind 127.0.0.1', 'python -m http.server 4321 --bind 127.0.0.1'),
    ('uvicorn main:app --port=8000', 'uvicorn main:app --port 4321'),
    ('python -m uvicorn main:app', 'python -m uvicorn main:app --port 4321'),
    ('streamlit run app.py --server.port 8501', 'streamlit run app.py --server.port 4321'),
    ('python -m streamlit run app.py', 'python -m streamlit run app.py --server.port 4321'),
    ('npx next dev -p 3000', 'npx next dev -p 4321'),
    ('vite --port 5173', 'vite --port 4321 --strictPort'),
    ('flask --app main run', 'flask --app main run --port 4321'),
    ('python app.py --listen {port}', 'python app.py --listen 4321'),
    ('node server.js', 'node server.js'),
    ('echo test && python app.py --port 9000', 'echo test && python app.py --port 9000'),
])
def test_command_adapters(tmp_path, command, expected):
    actual, env = command_for_port(command, tmp_path, 4321)
    assert actual == expected
    assert env['PORT'] == '4321'


def test_npm_script_detection_preserves_files(tmp_path):
    file = tmp_path / 'package.json'
    contents = json.dumps({'scripts': {'dev': 'vite --port 9999', 'start': 'react-scripts start', 'custom': 'node server.js'}})
    file.write_text(contents)
    assert command_for_port('npm run dev', tmp_path, 4321)[0] == 'npm run dev -- --port 4321 --strictPort'
    assert command_for_port('npm run dev -- --port=3000', tmp_path, 4321)[0] == 'npm run dev -- --port 4321 --strictPort'
    assert command_for_port('npm start', tmp_path, 4321)[0] == 'npm start'
    assert command_for_port('npm run custom', tmp_path, 4321)[0] == 'npm run custom'
    assert file.read_text() == contents


def test_urls_preserve_scheme_path_and_query():
    assert with_port('https://[::1]:8501/docs?q=1#top', 4321) == 'https://[::1]:4321/docs?q=1#top'
    assert with_port('http://localhost/path', 4321) == 'http://localhost:4321/path'


def test_simultaneous_projects_with_same_preferred_port(client, tmp_path):
    port = free_port()
    one, _ = project(client, tmp_path, port=port)
    two, _ = project(client, tmp_path, port=port)
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda p: client.post(f'/api/launcher/launch/{p["id"]}'), [one, two]))
    assert all(response.status_code == 202 for response in responses)
    try:
        sessions = [wait_status(client, response.json()['id'], 'running') for response in responses]
        assert len({s['actual_url'] for s in sessions}) == 2
    finally:
        for response in responses:
            client.post(f'/api/launcher/stop/{response.json()["id"]}')


def test_custom_server_reads_chosen_environment_port(client, tmp_path):
    script = tmp_path / 'server.py'
    script.write_text('import os\nfrom http.server import HTTPServer, SimpleHTTPRequestHandler\nHTTPServer(("127.0.0.1", int(os.environ["PORT"])), SimpleHTTPRequestHandler).serve_forever()\n')
    with socket.socket() as occupied:
        occupied.bind(('127.0.0.1', 0))
        port = occupied.getsockname()[1]
        p, _ = project(client, tmp_path, f'"{sys.executable}" -u "{script}"', port)
        response = client.post(f'/api/launcher/launch/{p["id"]}')
        assert response.status_code == 202, response.text
        try:
            running = wait_status(client, response.json()['id'], 'running')
            assert url_port(running['actual_url']) != port
        finally:
            client.post(f'/api/launcher/stop/{response.json()["id"]}')


def test_ipv6_listener_is_not_selected():
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        sock.bind(('::1', 0))
    except OSError:
        pytest.skip('IPv6 loopback is disabled')
    with sock:
        port = sock.getsockname()[1]
        assert choose_port(port) != port


@pytest.mark.skipif(os.name != 'nt', reason='Windows PowerShell integration')
def test_powershell_wrapper_receives_port_and_native_module_path(client, tmp_path, monkeypatch):
    monkeypatch.setenv('PSModulePath', str(tmp_path / 'not-a-powershell-module-directory'))
    script = tmp_path / 'start.ps1'
    script.write_text("$ErrorActionPreference = 'Stop'\nGet-Command Get-FileHash -ErrorAction Stop | Out-Null\n" +
                      f"& '{sys.executable}' -u -m http.server $env:LAUNCHPAD_PORT --bind 127.0.0.1\n")
    p, _ = project(client, tmp_path, f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{script}"')
    response = client.post(f'/api/launcher/launch/{p["id"]}')
    assert response.status_code == 202, response.text
    try:
        running = wait_status(client, response.json()['id'], 'running')
        assert running['actual_url'] == p['url']
    finally:
        client.post(f'/api/launcher/stop/{response.json()["id"]}')
