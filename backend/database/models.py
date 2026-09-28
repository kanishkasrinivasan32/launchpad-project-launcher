from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default='')
    folder: Mapped[str] = mapped_column(Text)
    startup_command: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(50), default='Application')
    technologies: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[str] = mapped_column(String, default=now_iso)


class ProjectSession(Base):
    __tablename__ = 'project_sessions'
    __table_args__ = {'sqlite_autoincrement': True}
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    started_at: Mapped[str] = mapped_column(String, default=now_iso)
    ended_at: Mapped[str | None] = mapped_column(String, nullable=True)
    total_runtime: Mapped[int] = mapped_column(Integer, default=0)
    avg_cpu: Mapped[float] = mapped_column(Float, default=0)
    avg_ram: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String, default='starting')
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    browser_warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_command: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProcessMetric(Base):
    __tablename__ = 'process_metrics'
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey('project_sessions.id', ondelete='CASCADE'), index=True)
    timestamp: Mapped[str] = mapped_column(String, default=now_iso)
    cpu_percent: Mapped[float] = mapped_column(Float)
    ram_mb: Mapped[float] = mapped_column(Float)
    pid: Mapped[int] = mapped_column(Integer)


class Setting(Base):
    __tablename__ = 'settings'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text)
