"""Unit and integration tests for LangGraph multi-agent orchestrator and chat workflow."""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.agents.orchestrator import classify_intent, build_orchestrator_graph
from backend.app.database.connection import init_db
from backend.app.schemas.resume import ResumeProfile

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_chat_apps.db")
    monkeypatch.setattr("backend.app.database.connection.get_db_path", lambda: test_db_path)
    init_db(test_db_path)
    yield
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_classify_intent_patterns():
    # Apply patterns
    intent, idx = classify_intent("Please apply to job 3", [])
    assert intent == "apply_job"
    assert idx == 2  # 0-indexed

    intent, idx = classify_intent("Apply to #1", [])
    assert intent == "apply_job"
    assert idx == 0

    # Applications list
    intent, _ = classify_intent("Show my applied jobs", [])
    assert intent == "view_applications"

    # Filter
    intent, _ = classify_intent("Show only remote jobs", [])
    assert intent == "filter_remote"

    # Search
    intent, _ = classify_intent("Find Python developer jobs", [])
    assert intent == "search_jobs"

    # Match
    intent, _ = classify_intent("Recommend suitable jobs for my profile", [])
    assert intent == "match_profile"


def test_langgraph_graph_build():
    graph = build_orchestrator_graph()
    assert graph is not None


def test_multiturn_conversational_workflow():
    session_id = "test_user_session_42"
    sample_profile = {
        "name": "Demo Candidate",
        "email": "demo.candidate@example.com",
        "designation": "Java Developer",
        "skills": ["Java", "Spring Boot", "MySQL", "Docker"],
        "experience_years": 1.5,
    }

    # Turn 1: Recommend jobs based on profile
    r1 = client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "message": "Recommend jobs matching my profile",
            "resume_profile": sample_profile,
        }
    )
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["action_type"] == "jobs_found"
    assert len(data1["jobs"]) > 0
    first_job_title = data1["jobs"][0]["job"]["title"]

    # Turn 2: Filter only remote
    r2 = client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "message": "Show only remote jobs",
        }
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["action_type"] == "jobs_found"
    assert len(data2["jobs"]) > 0
    for j in data2["jobs"]:
        assert j["job"]["work_mode"] == "Remote"

    # Turn 3: Apply to job 1
    r3 = client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "message": "Apply to job 1",
        }
    )
    assert r3.status_code == 200
    data3 = r3.json()
    assert data3["action_type"] == "applied"
    assert data3["application"] is not None
    assert data3["application"]["status"] == "Applied"
    assert "source_link" in data3["application"]

    # Turn 4: Check applied jobs
    r4 = client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "message": "Show my applied jobs",
        }
    )
    assert r4.status_code == 200
    data4 = r4.json()
    assert data4["action_type"] == "application_list"
    assert len(data4["applications"]) == 1
    assert data4["applications"][0]["job_title"] == data3["application"]["job_title"]

    # Turn 5: Prevent duplicate application to job 1
    r5 = client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "message": "Apply to job 1",
        }
    )
    assert r5.status_code == 200
    data5 = r5.json()
    assert data5["action_type"] == "duplicate_application"
    assert "already applied" in data5["reply"].lower()

