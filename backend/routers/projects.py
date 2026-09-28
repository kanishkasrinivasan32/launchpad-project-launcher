from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select

from backend.database.db import SessionLocal
from backend.database.models import Project, ProjectSession
from backend.services.process_manager import manager
from backend.services.project_service import ProjectInput, as_dict, get_project, list_projects

router = APIRouter(prefix='/api/projects', tags=['Projects'])


@router.get('')
def index():
    return list_projects()


@router.post('', status_code=201)
def create(payload: ProjectInput):
    with SessionLocal.begin() as db:
        project = Project(**payload.model_dump())
        db.add(project)
        db.flush()
        return as_dict(project)


@router.get('/{project_id}')
def show(project_id: int):
    project = get_project(project_id)
    with SessionLocal() as db:
        sessions = db.scalars(select(ProjectSession).where(ProjectSession.project_id == project_id).order_by(ProjectSession.id.desc()).limit(100)).all()
        return {**project, 'sessions': [as_dict(s) for s in sessions]}


@router.put('/{project_id}')
def update(project_id: int, payload: ProjectInput):
    with manager.guard:
        get_project(project_id)
        if manager.active_for(project_id):
            raise HTTPException(409, 'Stop this project before editing its configuration.')
        with SessionLocal.begin() as db:
            project = db.get(Project, project_id)
            for key, value in payload.model_dump().items():
                setattr(project, key, value)
            db.flush()
            return as_dict(project)


@router.delete('/{project_id}', status_code=204)
def delete(project_id: int):
    with manager.guard:
        get_project(project_id)
        if manager.active_for(project_id):
            raise HTTPException(409, 'Stop this project before deleting it.')
        with SessionLocal.begin() as db:
            db.delete(db.get(Project, project_id))
    return Response(status_code=204)
