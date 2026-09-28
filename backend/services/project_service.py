from pathlib import Path
from urllib.parse import urlsplit

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from backend.database.db import SessionLocal
from backend.database.models import Project, ProjectSession


class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=2000)
    folder: str = Field(min_length=1, max_length=2048)
    startup_command: str = Field(min_length=1, max_length=4096)
    url: str = Field(default='http://localhost:3000', min_length=1, max_length=2048)
    type: str = Field(default='Application', max_length=50)
    technologies: str = Field(default='', max_length=500)

    @field_validator('name', 'folder', 'startup_command', mode='before')
    @classmethod
    def nonempty(cls, value):
        if not isinstance(value, str):
            raise ValueError('Enter a text value.')
        value = value.strip()
        if not value or '\x00' in value or '\n' in value or '\r' in value:
            raise ValueError('Enter a non-empty, single-line value.')
        return value

    @field_validator('folder')
    @classmethod
    def folder_exists(cls, value):
        path = Path(value).expanduser()
        if not path.is_absolute() or not path.is_dir():
            raise ValueError('Project folder does not exist. Choose an existing absolute folder path.')
        return str(path.resolve())

    @field_validator('url')
    @classmethod
    def localhost_only(cls, value):
        value = value.strip()
        try:
            parsed = urlsplit(value)
            port = parsed.port
            valid = parsed.scheme in ('http', 'https') and parsed.hostname in ('localhost', '127.0.0.1', '::1')
            valid = valid and not parsed.username and not parsed.password and (port is None or port > 0)
        except ValueError:
            valid = False
        if not valid:
            raise ValueError('Use a localhost URL, for example http://localhost:3000.')
        return value


def as_dict(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def get_project(project_id):
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        if project is None:
            raise HTTPException(404, 'Project not found.')
        return as_dict(project)


def list_projects():
    with SessionLocal() as db:
        projects = db.scalars(select(Project).order_by(Project.created_at.desc())).all()
        result = []
        for project in projects:
            latest = db.scalars(select(ProjectSession).where(ProjectSession.project_id == project.id).order_by(ProjectSession.id.desc()).limit(1)).first()
            result.append({**as_dict(project), 'session': as_dict(latest) if latest else None})
        return result
