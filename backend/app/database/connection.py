"""SQLite database connection and schema initialization for application tracking."""

import os
import sqlite3
from typing import Optional
from backend.app.core.config import get_settings


def get_db_path() -> str:
    """Extract SQLite database file path from DATABASE_URL configuration."""
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith("sqlite:///"):
        path = db_url.replace("sqlite:///", "")
    else:
        path = db_url

    # Ensure parent directory exists
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
    return path


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize SQLite database schema and constraints."""
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(target_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                application_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                job_title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT NOT NULL,
                source_link TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Applied',
                applied_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(session_id, job_id)
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_apps_session ON applications(session_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_apps_job ON applications(job_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_apps_status ON applications(status);
        """)
        conn.commit()
    finally:
        conn.close()


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a row-factory enabled SQLite connection."""
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(target_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

