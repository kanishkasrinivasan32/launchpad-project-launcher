import asyncio
from contextlib import asynccontextmanager
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database.db import init_db, close_interrupted_sessions
from backend.routers import projects, launcher, monitoring
from backend.services.process_manager import manager
from backend.services.instance_lock import acquire_instance_lock


@asynccontextmanager
async def lifespan(app):
    settings.storage.mkdir(parents=True, exist_ok=True)
    instance_lock = acquire_instance_lock()
    handler = RotatingFileHandler(settings.storage / 'dashboard.log', maxBytes=2_000_000, backupCount=2, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
    init_db()
    close_interrupted_sessions()
    manager.closing = False
    try:
        yield
    finally:
        await asyncio.to_thread(manager.shutdown)
        logging.getLogger().removeHandler(handler)
        handler.close()
        instance_lock.close()


app = FastAPI(title='Project Launcher', version='1.0.0', lifespan=lifespan)


def allowed_origins():
    frontend = settings.current_frontend_url.rstrip('/')
    return {frontend, frontend.replace('localhost', '127.0.0.1'), frontend.replace('127.0.0.1', 'localhost'),
            f'http://localhost:{settings.backend_port}', f'http://127.0.0.1:{settings.backend_port}'}


class LocalCORS(CORSMiddleware):
    def is_allowed_origin(self, origin):
        return origin in allowed_origins()


app.add_middleware(LocalCORS, allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Content-Type', 'X-Launchpad-Request'])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost', '127.0.0.1', '[::1]'])


@app.middleware('http')
async def local_origin(request: Request, call_next):
    if request.headers.get('sec-fetch-site') == 'cross-site':
        return JSONResponse(status_code=403, content={'detail': 'Cross-site browser requests are not allowed.'})
    origin = request.headers.get('origin')
    if origin and origin not in allowed_origins():
        return JSONResponse(status_code=403, content={'detail': 'This dashboard only accepts requests from its local frontend.'})
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and request.headers.get('x-launchpad-request') != '1':
        return JSONResponse(status_code=403, content={'detail': 'Use the local dashboard, or include X-Launchpad-Request: 1 in your API request.'})
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logging.getLogger(__name__).error('Unhandled API error', exc_info=exc)
    return JSONResponse(status_code=500, content={'detail': 'The dashboard could not complete this action. Check data/dashboard.log for details.'})


@app.get('/api/health')
def health():
    return {'status': 'ok', 'application': 'project-launcher', 'version': '1.0.0'}


app.include_router(projects.router)
app.include_router(launcher.router)
app.include_router(monitoring.router)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=settings.backend_port, workers=1)
