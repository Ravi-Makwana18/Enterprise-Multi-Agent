import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=settings.database_echo,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_db_session():
    """Yield a database session and ensure it is always closed."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def initialize_database(force: bool = False) -> None:
    if force:
        try:
            from sqlalchemy import inspect
            if inspect(engine).has_table("tickets"):
                Base.metadata.drop_all(bind=engine)
        except Exception:
            pass

    # Let SQLAlchemy create all tables from the ORM models first
    Base.metadata.create_all(bind=engine)

    # Run any SQL migration files
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    if migrations_dir.exists():
        for migration_file in sorted(migrations_dir.glob("*.sql")):
            with engine.begin() as connection:
                sql = migration_file.read_text(encoding="utf-8")
                if sql.strip():
                    for statement in [part.strip() for part in sql.split(";") if part.strip()]:
                        connection.execute(text(statement))

    # Always run column migrations to ensure schema is up to date
    _run_column_migrations(engine)
    return None


def _run_column_migrations(engine) -> None:
    """Safely add missing columns to existing tables (fully idempotent)."""
    migrations = {
        "tickets": [
            ("category",     "ALTER TABLE tickets ADD COLUMN category TEXT DEFAULT 'general';"),
            ("priority",     "ALTER TABLE tickets ADD COLUMN priority TEXT DEFAULT 'normal';"),
            ("requester",    "ALTER TABLE tickets ADD COLUMN requester TEXT;"),
            ("assignee",     "ALTER TABLE tickets ADD COLUMN assignee TEXT;"),
            ("reviewed_by",  "ALTER TABLE tickets ADD COLUMN reviewed_by TEXT;"),
            ("review_notes", "ALTER TABLE tickets ADD COLUMN review_notes TEXT;"),
            ("updated_at",   "ALTER TABLE tickets ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP;"),
        ],
        "reviews": [
            ("title",      "ALTER TABLE reviews ADD COLUMN title TEXT;"),
            ("reviewer",   "ALTER TABLE reviews ADD COLUMN reviewer TEXT;"),
            ("status",     "ALTER TABLE reviews ADD COLUMN status TEXT DEFAULT 'pending';"),
            ("updated_at", "ALTER TABLE reviews ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP;"),
        ],
        "workflow_states": [
            ("status",            "ALTER TABLE workflow_states ADD COLUMN status TEXT DEFAULT 'submitted';"),
            ("execution_history", "ALTER TABLE workflow_states ADD COLUMN execution_history TEXT;"),
            ("updated_at",        "ALTER TABLE workflow_states ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP;"),
        ],
    }
    for table, columns in migrations.items():
        try:
            with engine.begin() as conn:
                existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info('{table}');")).fetchall()}
                for col_name, alter_sql in columns:
                    if col_name not in existing:
                        conn.execute(text(alter_sql))
        except Exception:
            pass
