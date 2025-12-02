from sqlmodel import SQLModel, Session, create_engine

from .settings import settings


engine = create_engine(settings.database_url, echo=False)


def get_session():
    with Session(engine) as session:
        yield session


def init_db():
    SQLModel.metadata.create_all(engine)
    _ensure_recordings_metrics_columns()


def _ensure_recordings_metrics_columns():
    """Add missing analytics columns if the DB already existed."""
    with engine.connect() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(recordings)").fetchall()}
        to_add = []
        if "word_count" not in existing:
            to_add.append("ALTER TABLE recordings ADD COLUMN word_count INTEGER")
        if "wpm" not in existing:
            to_add.append("ALTER TABLE recordings ADD COLUMN wpm REAL")
        for stmt in to_add:
            conn.exec_driver_sql(stmt)
