import os
from pathlib import Path
import tempfile

# Isolate all tests from the user's real project database and browser.
TEST_STORAGE = tempfile.TemporaryDirectory(prefix='launcher-tests-')
os.environ['DATA_DIR'] = TEST_STORAGE.name
os.environ['AUTO_OPEN_BROWSER'] = 'false'
os.environ['MONITOR_INTERVAL'] = '0.15'
os.environ['STARTUP_TIMEOUT'] = '4'

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.db import engine


@pytest.fixture(scope='session')
def client():
    with TestClient(app, base_url='http://localhost', headers={'X-Launchpad-Request': '1'}) as test_client:
        yield test_client
    engine.dispose()
    TEST_STORAGE.cleanup()
