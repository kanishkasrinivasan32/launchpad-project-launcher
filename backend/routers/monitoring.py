from datetime import datetime, timezone

from fastapi import APIRouter, Query
import psutil
from sqlalchemy import select

from backend.config import settings
from backend.database.db import SessionLocal
from backend.database.models import Project, ProjectSession
from backend.services.process_manager import manager
from backend.services.project_service import as_dict

router = APIRouter(prefix='/api', tags=['Monitoring'])


@router.get('/monitoring/{session_id}')
def metrics(session_id: int):
    return manager.status(session_id)


@router.get('/monitoring/{session_id}/logs')
def logs(session_id: int, limit: int = Query(default=60000, ge=100, le=200000)):
    manager.status(session_id)
    path = settings.storage / 'logs' / f'{session_id}.log'
    try:
        with path.open('rb') as stream:
            stream.seek(0, 2)
            size = stream.tell()
            stream.seek(max(0, size - limit))
            content = stream.read(limit).decode('utf-8', errors='replace')
    except FileNotFoundError:
        content = ''
        size = 0
    return {'session_id': session_id, 'content': content, 'truncated': size > limit}


@router.get('/summary')
def summary():
    now = datetime.now(timezone.utc)
    midnight = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    with SessionLocal() as db:
        projects = db.scalars(select(Project)).all()
        sessions = db.scalars(select(ProjectSession)).all()
        today = 0
        totals = {}
        active = []
        for session in sessions:
            start = datetime.fromisoformat(session.started_at)
            end = datetime.fromisoformat(session.ended_at) if session.ended_at else now
            today += max(0, (end - max(start, midnight)).total_seconds())
            runtime = session.total_runtime if session.ended_at else int((now - start).total_seconds())
            totals[session.project_id] = totals.get(session.project_id, 0) + runtime
            if session.ended_at is None:
                active.append(manager.status(session.id))
        most = max(projects, key=lambda p: totals.get(p.id, 0), default=None)
        return {'total_projects': len(projects), 'running_count': sum(s['status'] == 'running' for s in active),
                'active_count': len(active), 'runtime_today': int(today),
                'most_used': {'name': most.name, 'runtime_seconds': totals[most.id]} if most and totals.get(most.id, 0) else None,
                'sessions': active, 'system': {'cpu_percent': psutil.cpu_percent(None), 'ram_percent': psutil.virtual_memory().percent}}


@router.get('/history')
def history():
    with SessionLocal() as db:
        rows = db.execute(select(ProjectSession, Project.name).join(Project).order_by(ProjectSession.id.desc()).limit(200)).all()
        return [{**as_dict(session), 'project_name': name} for session, name in rows]


@router.get('/settings')
def configuration():
    return {'browser': 'Chrome (default browser fallback)', 'auto_open_browser': settings.auto_open_browser,
            'monitor_interval': settings.monitor_interval, 'startup_timeout': settings.startup_timeout,
            'frontend_url': settings.current_frontend_url, 'backend_port': settings.backend_port, 'data_dir': str(settings.storage)}
