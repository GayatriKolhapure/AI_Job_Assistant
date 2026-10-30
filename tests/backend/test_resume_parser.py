"""Unit tests for resume parsing service and API endpoints."""

import io
import pytest
from fastapi.testclient import TestClient
import pymupdf
import docx

from backend.app.main import app
from backend.app.services.resume_parser import (
    ResumeParserService,
    extract_text_from_pdf,
    extract_text_from_docx,
)

client = TestClient(app)


def create_sample_pdf_bytes() -> bytes:
    """Generate in-memory valid PDF bytes for testing."""
    doc = pymupdf.open()
    page = doc.new_page()
    content = (
        "Rahul Sharma\n"
        "rahul.sharma@example.com | +91 9123456789 | Pune, India\n"
        "Full Stack Developer\n\n"
        "Summary:\n"
        "Passionate software engineer with 2 years of experience in Java, Spring Boot, React, and MySQL.\n\n"
        "Technical Skills:\n"
        "Languages: Java, Python, JavaScript, TypeScript, SQL\n"
        "Frameworks: Spring Boot, React, Express, FastAPI, Docker\n"
        "Databases: MySQL, PostgreSQL, MongoDB\n\n"
        "Experience:\n"
        "Software Engineer at GlobalTech Systems (2022 - 2024)\n"
        "Built microservices and scalable REST APIs using Spring Boot and Docker.\n\n"
        "Education:\n"
        "B.Tech in Computer Science from Pune University (2022)\n"
    )
    page.insert_text((50, 72), content)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_sample_docx_bytes() -> bytes:
    """Generate in-memory valid DOCX bytes for testing."""
    doc = docx.Document()
    doc.add_heading("Priya Patel", level=1)
    doc.add_paragraph("priya.patel@example.com | +91 9876543210")
    doc.add_paragraph("Python Developer - Fresher")
    doc.add_paragraph("Skills: Python, Django, FastAPI, PostgreSQL, Git, Docker")
    doc.add_paragraph("Education: B.Tech Computer Engineering (2024)")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_extract_pdf_and_parse():
    pdf_bytes = create_sample_pdf_bytes()
    text = extract_text_from_pdf(pdf_bytes)
    assert "Rahul Sharma" in text
    assert "rahul.sharma@example.com" in text

    profile = ResumeParserService.parse_deterministic(text)
    assert profile.name == "Rahul Sharma"
    assert profile.email == "rahul.sharma@example.com"
    assert "Java" in profile.skills
    assert "Spring Boot" in profile.skills
    assert "React" in profile.skills
    assert profile.experience_years >= 1.0


def test_extract_docx_and_parse():
    docx_bytes = create_sample_docx_bytes()
    text = extract_text_from_docx(docx_bytes)
    assert "Priya Patel" in text
    assert "priya.patel@example.com" in text

    profile = ResumeParserService.parse_deterministic(text)
    assert "Python" in profile.skills
    assert "FastAPI" in profile.skills


def test_api_resume_upload_pdf():
    pdf_bytes = create_sample_pdf_bytes()
    response = client.post(
        "/api/resume/upload",
        files={"file": ("test_resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["profile"]["name"] == "Rahul Sharma"
    assert "Java" in data["profile"]["skills"]


def test_api_resume_upload_invalid_type():
    response = client.post(
        "/api/resume/upload",
        files={"file": ("test.png", b"not an image", "image/png")},
    )
    assert response.status_code == 400


def test_api_resume_upload_empty_file():
    response = client.post(
        "/api/resume/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400


def test_api_sample_resume():
    response = client.get("/api/resume/sample")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Demo Candidate"
    assert "Spring Boot" in data["skills"]

