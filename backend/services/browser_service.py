import os
import shutil
import webbrowser
from pathlib import Path

from backend.config import settings


def open_browser(url: str):
    if not settings.auto_open_browser:
        return None
    candidates = [settings.chrome_path, shutil.which('chrome'), shutil.which('google-chrome')]
    for variable in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
        if os.getenv(variable):
            candidates.append(str(Path(os.environ[variable]) / 'Google/Chrome/Application/chrome.exe'))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            # BackgroundBrowser takes an argument list, preserving spaces in Windows paths.
            if webbrowser.BackgroundBrowser([candidate, '%s']).open(url, new=2):
                return None
    if webbrowser.open(url, new=2):
        return 'Chrome was not found. Opened your default browser instead. Set CHROME_PATH in .env to use Chrome.'
    return 'The browser could not be opened. Use Open app, or set CHROME_PATH in .env.'
