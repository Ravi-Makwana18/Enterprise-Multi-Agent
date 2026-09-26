import os
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


def get_db_session() -> Session:
    session = SessionLocal()
    try:
        return session
    finally:
        pass


def initialize_database(force: bool = False) -> None:
    if force:
        try:
            from sqlalchemy import inspect

            if inspect(engine).has_table("tickets"):
                Base.metadata.drop_all(bind=engine)
        except Exception:
            pass

    Base.metadata.create_all(bind=engine)

    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    if migrations_dir.exists():
        for migration_file in sorted(migrations_dir.glob("*.sql")):
            with engine.begin() as connection:
                sql = migration_file.read_text(encoding="utf-8")
                if sql.strip():
                    for statement in [part.strip() for part in sql.split(";") if part.strip()]:
                        connection.execute(text(statement))

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id TEXT UNIQUE NOT NULL, summary TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'submitted', category TEXT DEFAULT 'general', priority TEXT DEFAULT 'normal', requester TEXT, assignee TEXT, reviewed_by TEXT, review_notes TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP);"))
        connection.execute(text("CREATE TABLE IF NOT EXISTS employees (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT UNIQUE NOT NULL, employee_name TEXT NOT NULL, basic_salary REAL, hra REAL, bonus REAL, pan TEXT, account_number TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);"))
        connection.execute(text("CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, review_id TEXT UNIQUE NOT NULL, review_type TEXT NOT NULL, content TEXT, score REAL, approved BOOLEAN, issues TEXT, recommendations TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);"))
        connection.execute(text("CREATE TABLE IF NOT EXISTS security_checks (id INTEGER PRIMARY KEY AUTOINCREMENT, security_id TEXT UNIQUE NOT NULL, employee_id TEXT, employee_name TEXT, passport TEXT, aadhaar TEXT, address TEXT, police_verification TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);"))
        connection.execute(text("CREATE TABLE IF NOT EXISTS workflow_states (id INTEGER PRIMARY KEY AUTOINCREMENT, workflow_id TEXT UNIQUE NOT NULL, user_input TEXT, route TEXT, response TEXT, score REAL, approved BOOLEAN, iteration INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP);"))
        connection.execute(text("CREATE TABLE IF NOT EXISTS user_actions (id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL, username TEXT, role TEXT, details TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);"))

    # Ensure the existing tickets table includes enterprise workflow columns for older SQLite databases.
    try:
        with engine.begin() as connection:
            result = connection.execute(text("PRAGMA table_info('tickets');")).fetchall()
            existing = {row[1] for row in result}
            if "category" not in existing:
                connection.execute(text("ALTER TABLE tickets ADD COLUMN category TEXT DEFAULT 'general';"))
            if "priority" not in existing:
                connection.execute(text("ALTER TABLE tickets ADD COLUMN priority TEXT DEFAULT 'normal';"))
            if "requester" not in existing:
                connection.execute(text("ALTER TABLE tickets ADD COLUMN requester TEXT;"))
            if "assignee" not in existing:
                connection.execute(text("ALTER TABLE tickets ADD COLUMN assignee TEXT;"))
            if "reviewed_by" not in existing:
                connection.execute(text("ALTER TABLE tickets ADD COLUMN reviewed_by TEXT;"))
            if "review_notes" not in existing:
                connection.execute(text("ALTER TABLE tickets ADD COLUMN review_notes TEXT;"))
            if "updated_at" not in existing:
                connection.execute(text("ALTER TABLE tickets ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP;"))
    except Exception:
        pass

    # Ensure the existing reviews table includes title, reviewer, status columns.
    try:
        with engine.begin() as connection:
            result = connection.execute(text("PRAGMA table_info('reviews');")).fetchall()
            existing = {row[1] for row in result}
            if "title" not in existing:
                connection.execute(text("ALTER TABLE reviews ADD COLUMN title TEXT;"))
            if "reviewer" not in existing:
                connection.execute(text("ALTER TABLE reviews ADD COLUMN reviewer TEXT;"))
            if "status" not in existing:
                connection.execute(text("ALTER TABLE reviews ADD COLUMN status TEXT DEFAULT 'pending';"))
            if "updated_at" not in existing:
                connection.execute(text("ALTER TABLE reviews ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP;"))
    except Exception:
        pass

    return None
