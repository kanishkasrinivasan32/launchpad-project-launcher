import asyncio

from fastapi import APIRouter

from backend.services.process_manager import manager
from backend.services.project_service import get_project

router = APIRouter(prefix='/api/launcher', tags=['Launcher'])


@router.post('/launch/{project_id}', status_code=202)
async def launch(project_id: int):
    return await asyncio.to_thread(manager.launch, project_id)


@router.post('/stop/{session_id}')
async def stop(session_id: int):
    return await asyncio.to_thread(manager.stop, session_id)


@router.post('/restart/{project_id}', status_code=202)
async def restart(project_id: int):
    def restart_project():
        with manager.guard:
            get_project(project_id)
            session = manager.active_for(project_id)
            if session:
                manager.stop(session.id)
            return manager.launch(project_id)
    return await asyncio.to_thread(restart_project)


@router.get('/status/{session_id}')
def status(session_id: int):
    return manager.status(session_id)
