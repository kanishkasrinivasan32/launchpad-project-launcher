import pytest
from pydantic import ValidationError

from backend.config import Settings


def test_untrusted_browser_cannot_read_or_execute(client):
    assert client.get('/api/projects', headers={'Sec-Fetch-Site': 'cross-site'}).status_code == 403
    assert client.post('/api/launcher/launch/999999', headers={'Origin': 'https://attacker.example'}).status_code == 403
    assert client.post('/api/launcher/launch/999999', headers={'X-Launchpad-Request': ''}).status_code == 403
    assert client.post('/api/launcher/launch/999999', headers={'X-Launchpad-Request': '', 'Content-Type': 'application/x-www-form-urlencoded'}, content='').status_code == 403
    assert client.get('/api/projects', headers={'Origin': 'null'}).status_code == 403
    assert client.get('/api/projects', headers={'Host': 'attacker.example'}).status_code == 400


def test_local_cors_and_sensitive_response_headers(client):
    response = client.options('/api/projects', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'X-Launchpad-Request, Content-Type'})
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
    response = client.get('/api/projects')
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-frame-options'] == 'DENY'
    assert response.headers['x-content-type-options'] == 'nosniff'


@pytest.mark.parametrize('url', ['http://0.0.0.0:5173', 'https://attacker.example:5173', 'http://user:password@localhost:5173', 'http://localhost:5173/path', 'http://localhost:5173?token=example'])
def test_frontend_origin_must_stay_local(url):
    with pytest.raises(ValidationError):
        Settings(frontend_url=url)
