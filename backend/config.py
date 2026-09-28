from pathlib import Path
import json
from urllib.parse import urlsplit

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    backend_port: int = Field(default=8000, ge=1024, le=65535)
    frontend_url: str = 'http://localhost:5173'
    chrome_path: str = ''
    auto_open_browser: bool = True
    startup_timeout: float = Field(default=30, ge=1, le=300)
    monitor_interval: float = Field(default=2, ge=0.1, le=60)
    data_dir: Path = ROOT / 'data'

    @field_validator('frontend_url')
    @classmethod
    def local_frontend(cls, value):
        parsed = urlsplit(value)
        if (parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1')
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ('', '/') or not parsed.port):
            raise ValueError('FRONTEND_URL must be a local HTTP origin with an explicit port, e.g. http://localhost:5173.')
        return value.rstrip('/')

    @property
    def storage(self) -> Path:
        return self.data_dir if self.data_dir.is_absolute() else ROOT / self.data_dir

    @property
    def current_frontend_url(self):
        try:
            state = json.loads((self.storage / 'dashboard-processes.json').read_text())
            backend = urlsplit(state['backend']['url'])
            frontend = state['frontend']['url']
            parsed = urlsplit(frontend)
            if backend.port == self.backend_port and parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1'):
                return frontend
        except (OSError, KeyError, ValueError, TypeError):
            pass
        return self.frontend_url


settings = Settings()
