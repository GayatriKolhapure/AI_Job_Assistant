"""Service layer for job application tracking, persistence, and deduplication."""

from datetime import datetime, timezone
import secrets
import sqlite3
from typing import List, Optional

from backend.app.database.connection import get_db_connection
from backend.app.schemas.application import (
    ApplicationCreateRequest,
    ApplicationRecord,
    ApplicationStatus,
    get_utc_now_iso,
)


class DuplicateApplicationError(ValueError):
    """Raised when an application for the same job already exists in this session."""
    pass


class ApplicationService:
    @staticmethod
    def generate_application_id() -> str:
        """Generate a clean, professional application identifier, e.g. APP-7A2B9F4C."""
        rand_hex = secrets.token_hex(4).upper()
        return f"APP-{rand_hex}"

    @classmethod
    def is_already_applied(cls, session_id: str, job_id: str) -> bool:
        """Check if an application for job_id already exists within session_id."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM applications WHERE session_id = ? AND job_id = ? LIMIT 1",
                (session_id, job_id)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    @classmethod
    def create_application(cls, req: ApplicationCreateRequest) -> ApplicationRecord:
        """
        Record a confirmed job application into SQLite.
        Enforces uniqueness on (session_id, job_id).
        """
        if cls.is_already_applied(req.session_id, req.job_id):
            raise DuplicateApplicationError(
                f"You have already applied to '{req.job_title}' at {req.company} in this session."
            )

        app_id = cls.generate_application_id()
        now_iso = get_utc_now_iso()
        applied_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO applications (
                    application_id, session_id, job_id, job_title, company,
                    location, source_link, status, applied_date, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    app_id,
                    req.session_id,
                    req.job_id,
                    req.job_title,
                    req.company,
                    req.location,
                    req.source_link,
                    ApplicationStatus.APPLIED.value,
                    applied_date_str,
                    now_iso,
                    now_iso,
                )
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise DuplicateApplicationError(
                f"Duplicate record: an application for job ID '{req.job_id}' already exists."
            )
        finally:
            conn.close()

        return ApplicationRecord(
            application_id=app_id,
            session_id=req.session_id,
            job_id=req.job_id,
            job_title=req.job_title,
            company=req.company,
            location=req.location,
            source_link=req.source_link,
            status=ApplicationStatus.APPLIED,
            applied_date=applied_date_str,
            created_at=now_iso,
            updated_at=now_iso,
        )

    @classmethod
    def get_application(cls, application_id: str, session_id: Optional[str] = None) -> Optional[ApplicationRecord]:
        """Retrieve single application by ID with optional session isolation."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if session_id:
                cursor.execute(
                    """
                    SELECT application_id, session_id, job_id, job_title, company,
                           location, source_link, status, applied_date, created_at, updated_at
                    FROM applications
                    WHERE application_id = ? AND session_id = ?
                    """,
                    (application_id, session_id)
                )
            else:
                cursor.execute(
                    """
                    SELECT application_id, session_id, job_id, job_title, company,
                           location, source_link, status, applied_date, created_at, updated_at
                    FROM applications
                    WHERE application_id = ?
                    """,
                    (application_id,)
                )
            row = cursor.fetchone()
            if not row:
                return None
            return ApplicationRecord(
                application_id=row["application_id"],
                session_id=row["session_id"],
                job_id=row["job_id"],
                job_title=row["job_title"],
                company=row["company"],
                location=row["location"],
                source_link=row["source_link"],
                status=ApplicationStatus(row["status"]),
                applied_date=row["applied_date"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        finally:
            conn.close()

    @classmethod
    def list_applications(cls, session_id: str, status_filter: Optional[str] = None) -> List[ApplicationRecord]:
        """List all applications for a specific session with optional status filter."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if status_filter:
                cursor.execute(
                    """
                    SELECT application_id, session_id, job_id, job_title, company,
                           location, source_link, status, applied_date, created_at, updated_at
                    FROM applications
                    WHERE session_id = ? AND status = ?
                    ORDER BY created_at DESC
                    """,
                    (session_id, status_filter)
                )
            else:
                cursor.execute(
                    """
                    SELECT application_id, session_id, job_id, job_title, company,
                           location, source_link, status, applied_date, created_at, updated_at
                    FROM applications
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    """,
                    (session_id,)
                )
            rows = cursor.fetchall()
            return [
                ApplicationRecord(
                    application_id=r["application_id"],
                    session_id=r["session_id"],
                    job_id=r["job_id"],
                    job_title=r["job_title"],
                    company=r["company"],
                    location=r["location"],
                    source_link=r["source_link"],
                    status=ApplicationStatus(r["status"]),
                    applied_date=r["applied_date"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
                for r in rows
            ]
        finally:
            conn.close()

    @classmethod
    def update_status(
        cls, application_id: str, new_status: ApplicationStatus, session_id: Optional[str] = None
    ) -> Optional[ApplicationRecord]:
        """Update the workflow status of an existing application record."""
        now_iso = get_utc_now_iso()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if session_id:
                cursor.execute(
                    """
                    UPDATE applications
                    SET status = ?, updated_at = ?
                    WHERE application_id = ? AND session_id = ?
                    """,
                    (new_status.value, now_iso, application_id, session_id)
                )
            else:
                cursor.execute(
                    """
                    UPDATE applications
                    SET status = ?, updated_at = ?
                    WHERE application_id = ?
                    """,
                    (new_status.value, now_iso, application_id)
                )
            conn.commit()
            if cursor.rowcount == 0:
                return None
        finally:
            conn.close()

        return cls.get_application(application_id, session_id)

