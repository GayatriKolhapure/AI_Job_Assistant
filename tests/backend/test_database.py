"""Tests for SQLite application tracking and deduplication."""

import pytest
import tempfile
import os
from backend.app.database.connection import init_db
from backend.app.services.application_service import (
    ApplicationService,
    DuplicateApplicationError,
)
from backend.app.schemas.application import (
    ApplicationCreateRequest,
    ApplicationStatus,
)


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Provide a fresh isolated SQLite database for each test."""
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_apps.db")
    monkeypatch.setattr("backend.app.database.connection.get_db_path", lambda: test_db_path)
    init_db(test_db_path)
    yield
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_create_application():
    req = ApplicationCreateRequest(
        session_id="sess_101",
        job_id="job_java_01",
        job_title="Junior Java Developer",
        company="Acme Corp",
        location="Remote",
        source_link="https://example.com/apply/1",
    )
    record = ApplicationService.create_application(req)
    assert record.application_id.startswith("APP-")
    assert record.job_id == "job_java_01"
    assert record.status == ApplicationStatus.APPLIED
    assert record.session_id == "sess_101"


def test_prevent_duplicate_application():
    req = ApplicationCreateRequest(
        session_id="sess_102",
        job_id="job_py_01",
        job_title="Python Developer",
        company="Tech Innovations",
        location="Pune",
        source_link="https://example.com/apply/2",
    )
    ApplicationService.create_application(req)

    with pytest.raises(DuplicateApplicationError):
        ApplicationService.create_application(req)


def test_list_and_update_status():
    req1 = ApplicationCreateRequest(
        session_id="sess_103",
        job_id="job_react_01",
        job_title="Frontend Engineer",
        company="PixelCraft",
        location="Remote",
        source_link="https://example.com/apply/3",
    )
    req2 = ApplicationCreateRequest(
        session_id="sess_103",
        job_id="job_react_02",
        job_title="Fullstack React Engineer",
        company="NextGen",
        location="Bangalore",
        source_link="https://example.com/apply/4",
    )
    app1 = ApplicationService.create_application(req1)
    app2 = ApplicationService.create_application(req2)

    apps = ApplicationService.list_applications(session_id="sess_103")
    assert len(apps) == 2

    # Update status of app1
    updated = ApplicationService.update_status(
        application_id=app1.application_id,
        new_status=ApplicationStatus.INTERVIEW,
        session_id="sess_103"
    )
    assert updated is not None
    assert updated.status == ApplicationStatus.INTERVIEW

