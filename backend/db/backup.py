import logging
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from backend.config import settings

logger = logging.getLogger(__name__)

_BACKUP_ROOT = Path(os.getcwd()) / "backups"


def _safe_backup_path(output_dir: Path, filename: str) -> Path:
    resolved = (output_dir / filename).resolve()
    if not str(resolved).startswith(str(output_dir.resolve())):
        raise ValueError("Invalid backup output path.")
    return resolved


def create_backup(output_dir: str | None = None) -> str:
    safe_dir = Path(output_dir).resolve() if output_dir else _BACKUP_ROOT
    safe_dir.mkdir(parents=True, exist_ok=True)

    database_url = settings.database_url
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if database_url.startswith("sqlite"):
        db_path = database_url.replace("sqlite:///", "").lstrip("./")
        db_full = (Path(os.getcwd()) / db_path).resolve()
        backup_path = _safe_backup_path(safe_dir, f"backup_{timestamp}.sql")
        with sqlite3.connect(str(db_full)) as connection:
            with open(backup_path, "w", encoding="utf-8") as f:
                for line in connection.iterdump():
                    f.write(f"{line}\n")
        logger.info("SQLite backup created: %s", backup_path)
        return str(backup_path)

    if database_url.startswith("postgresql"):
        backup_path = _safe_backup_path(safe_dir, f"backup_{timestamp}.dump")
        result = subprocess.run(
            ["pg_dump", "--no-password", "-f", str(backup_path)],
            env={**os.environ, "DATABASE_URL": database_url},
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            logger.error("pg_dump failed: %s", result.stderr.decode(errors="replace"))
        return str(backup_path)

    raise ValueError("Unsupported database URL format.")
