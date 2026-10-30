"""Unit tests for job scraping, normalization, and validation modules."""

import pytest
from scraper.normalizer import (
    determine_work_mode,
    extract_experience,
    extract_skills_from_text,
    generate_stable_job_id,
    normalize_raw_job,
    strip_html,
)
from scraper.validator import validate_dataset


def test_strip_html():
    raw = "<p>We are looking for a <b>Java Developer</b> with Spring Boot experience.</p>"
    clean = strip_html(raw)
    assert clean == "We are looking for a Java Developer with Spring Boot experience."


def test_determine_work_mode():
    assert determine_work_mode("Backend Engineer", "Remote", True, "Fully remote position") == "Remote"
    assert determine_work_mode("Full Stack Dev", "Berlin", False, "Hybrid 2 days in office") == "Hybrid"
    assert determine_work_mode("Software Engineer", "New York, NY", False, "Must work from office") == "Onsite"


def test_extract_experience():
    text1, min_exp1 = extract_experience("Senior Software Engineer", "Requires 5+ years of Python")
    assert min_exp1 >= 5.0

    text2, min_exp2 = extract_experience("Junior Developer", "Fresher welcome, 0-1 years")
    assert min_exp2 == 0.0


def test_extract_skills():
    skills = extract_skills_from_text(
        title="Full Stack Java Developer",
        tags=["java", "spring-boot", "react"],
        description="Must have strong knowledge of PostgreSQL, Docker, and REST API."
    )
    assert "Java" in skills
    assert "PostgreSQL" in skills
    assert "Docker" in skills
    assert "REST API" in skills


def test_generate_stable_job_id():
    id1 = generate_stable_job_id("https://example.com/job/1", "Acme", "Dev")
    id2 = generate_stable_job_id("https://example.com/job/1", "Acme", "Dev")
    id3 = generate_stable_job_id("https://example.com/job/2", "Acme", "Dev")
    assert id1 == id2
    assert id1 != id3
    assert id1.startswith("job_")


def test_validate_dataset_sample():
    sample_jobs = [
        {
            "job_id": "job_01",
            "title": "Software Engineer",
            "company": "Tech Corp",
            "location": "Remote",
            "work_mode": "Remote",
            "experience_required": "1-3 years",
            "min_experience_years": 1.0,
            "skills": ["Python", "FastAPI"],
            "description": "Building AI backend services.",
            "source": "Arbeitnow",
            "source_link": "https://example.com/job/01",
            "posted_date": "2026-10-30",
        }
    ]
    report = validate_dataset(sample_jobs)
    assert report["total_records"] == 1
    assert report["usable_jobs_count"] == 1
    assert report["missing_fields_records"] == 0
    assert report["duplicate_ids"] == 0

