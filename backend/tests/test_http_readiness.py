from http.client import BadStatusLine, RemoteDisconnected

import pytest

from backend.services import process_manager
from scripts import launcher


@pytest.mark.parametrize('error', [BadStatusLine('GET /api/health HTTP/1.1'), RemoteDisconnected('Server is still starting')])
def test_dashboard_retries_incomplete_http_responses(monkeypatch, error):
    def incomplete(*args, **kwargs):
        raise error
    monkeypatch.setattr(launcher, 'request', incomplete)
    assert launcher.backend_ready() is False
    assert launcher.frontend_ready() is False


def test_project_retries_incomplete_http_response(monkeypatch):
    class IncompleteServer:
        def open(self, *args, **kwargs):
            raise BadStatusLine('GET / HTTP/1.1')
    monkeypatch.setattr(process_manager, 'build_opener', lambda *args: IncompleteServer())
    assert process_manager.http_ready('http://localhost:3000') is False
