"""Unit and API tests for JobService search, ranking, and transparent matching."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.job import JobListing, JobSearchQuery
from backend.app.schemas.resume import ResumeProfile
from backend.app.services.job_service import get_job_service

client = TestClient(app)


def test_job_dataset_loaded():
    service = get_job_service()
    assert service.total_count >= 1500, f"Expected at least 1500 jobs, found {service.total_count}"


def test_search_jobs_by_skill_and_remote():
    service = get_job_service()
    query = JobSearchQuery(skills=["Python"], work_mode="Remote", limit=5)
    total, results = service.search_jobs(query)
    assert total > 0
    assert len(results) <= 5
    for j in results:
        assert j.work_mode == "Remote"
        assert any(s.lower() == "python" for s in j.skills)


def test_get_job_by_id():
    service = get_job_service()
    # Grab the first available job
    first_job = service._jobs[0]
    fetched = service.get_job(first_job.job_id)
    assert fetched is not None
    assert fetched.job_id == first_job.job_id
    assert fetched.title == first_job.title


def test_calculate_match_transparent_scoring():
    service = get_job_service()
    profile = ResumeProfile(
        name="Demo Candidate",
        designation="Java Developer",
        skills=["Java", "Spring Boot", "MySQL", "Docker"],
        experience_years=2.0,
    )
    job = JobListing(
        job_id="test_job_1",
        title="Junior Java Developer",
        company="FinTech Core",
        location="Remote",
        work_mode="Remote",
        experience_required="1-2 years",
        min_experience_years=1.0,
        skills=["Java", "Spring Boot", "MySQL"],
        description="Developing banking microservices.",
        source="Arbeitnow",
        source_link="https://example.com/apply/java1",
    )
    match_result = service.calculate_match(profile, job)
    # Since candidate has all 3 job skills, matching title, compatible experience, and remote location:
    assert match_result.match_score >= 85.0
    assert "Java" in match_result.matching_skills
    assert "Spring Boot" in match_result.matching_skills
    assert len(match_result.missing_skills) == 0
    assert "Java Developer" in match_result.match_reason


def test_api_list_jobs():
    response = client.get("/api/jobs?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 5
    assert data["total"] >= 1500


def test_api_match_jobs():
    profile = {
        "name": "Priya Test",
        "designation": "Python Developer",
        "skills": ["Python", "Django", "PostgreSQL"],
        "experience_years": 1.0,
    }
    response = client.post("/api/jobs/match?limit=5", json=profile)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["matches"]) == 5
    # Verify score descending order
    scores = [m["match_score"] for m in data["matches"]]
    assert scores == sorted(scores, reverse=True)

