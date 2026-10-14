"""Database engine and session management."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

# For SQLite, check_same_thread=False is needed for FastAPI's async usage
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

# Enable WAL mode and foreign keys for SQLite
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables and perform light migrations if needed."""
    from app import models  # noqa: F401 — ensure models are imported
    Base.metadata.create_all(bind=engine)
    try:
        from sqlalchemy import inspect, text
        insp = inspect(engine)
        if "activities" in insp.get_table_names():
            cols = [c["name"] for c in insp.get_columns("activities")]
            if "eligible_rooms" not in cols:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE activities ADD COLUMN eligible_rooms VARCHAR(100)"))
                    conn.commit()
    except Exception:
        pass
