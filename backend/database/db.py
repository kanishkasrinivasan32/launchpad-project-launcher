from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.config import settings
from backend.database.models import Base, ProjectSession

settings.storage.mkdir(parents=True, exist_ok=True)
engine = create_engine(
    f'sqlite:///{(settings.storage / "launcher.db").as_posix()}',
    connect_args={'check_same_thread': False, 'timeout': 15},
    pool_size=5, max_overflow=5,
)


@event.listens_for(engine, 'connect')
def configure_sqlite(connection, _):
    cursor = connection.cursor()
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.execute('PRAGMA journal_mode=WAL')
    cursor.close()


SessionLocal = sessionmaker(engine, expire_on_commit=False)


def init_db():
    Base.metadata.create_all(engine)
    # Additive migration keeps existing projects, history, and metrics intact.
    with engine.begin() as connection:
        columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(project_sessions)')}
        for name in ('actual_url', 'actual_command'):
            if name not in columns:
                connection.exec_driver_sql(f'ALTER TABLE project_sessions ADD COLUMN {name} TEXT')


def close_interrupted_sessions():
    # No process is reattached or killed using a potentially recycled stored PID.
    from datetime import datetime, timedelta
    with SessionLocal.begin() as db:
        for session in db.query(ProjectSession).filter(ProjectSession.ended_at.is_(None)).all():
            session.status = 'interrupted'
            session.ended_at = (datetime.fromisoformat(session.started_at) + timedelta(seconds=session.total_runtime)).isoformat()
            session.error = 'The dashboard closed unexpectedly. Check the project port before launching again.'


if __name__ == '__main__':
    init_db()
    print(f'Database ready: {settings.storage / "launcher.db"}')
