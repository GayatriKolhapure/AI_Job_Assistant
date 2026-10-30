"""API endpoints for resume upload, extraction, and sample profile retrieval."""

import os
import uuid
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from backend.app.core.config import get_settings
from backend.app.schemas.resume import (
    EducationDetail,
    ExperienceDetail,
    ProjectDetail,
    ResumeParseResponse,
    ResumeProfile,
)
from backend.app.services.resume_parser import (
    ResumeParserService,
    ResumeParsingError,
)

router = APIRouter(prefix="/api/resume", tags=["Resume"])
settings = get_settings()


@router.post("/upload", response_model=ResumeParseResponse)
@router.post("/parse", response_model=ResumeParseResponse)
async def upload_and_parse_resume(file: UploadFile = File(...)):
    """
    Accepts candidate resume in PDF or DOCX format.
    Extracts text via PyMuPDF/python-docx and returns structured ResumeProfile.
    """
    filename = file.filename or "unknown_resume.pdf"
    fn_lower = filename.lower()

    if not (fn_lower.endswith(".pdf") or fn_lower.endswith(".docx")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF (.pdf) and Word (.docx) resumes are accepted.",
        )

    # Read file content safely
    contents = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.max_upload_size_mb} MB.",
        )

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    # Optional local cache in uploads dir
    os.makedirs(settings.upload_dir, exist_ok=True)
    temp_filename = f"{uuid.uuid4().hex}_{filename}"
    temp_path = os.path.join(settings.upload_dir, temp_filename)
    try:
        with open(temp_path, "wb") as f:
            f.write(contents)
    except Exception:
        pass  # Non-fatal if ephemeral

    try:
        result = await ResumeParserService.parse_file(contents, filename)
        return result
    except ResumeParsingError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing resume: {str(e)}",
        )


@router.get("/sample", response_model=ResumeProfile)
def get_sample_profile():
    """
    Returns a generic candidate demo profile for instant demonstration
    or quick testing without requiring manual file upload.
    """
    return ResumeProfile(
        name="Demo Candidate",
        email="demo.candidate@example.com",
        phone="+1 555-0199",
        designation="Java Developer",
        skills=[
            "Java", "Spring Boot", "REST API", "Hibernate", "MySQL",
            "Microservices", "Docker", "Git", "Postman", "JUnit"
        ],
        experience_years=1.0,
        experience_details=[
            ExperienceDetail(
                role="Junior Java Developer",
                company="Demo Tech Corp",
                duration="2023 - 2024",
                description="Developed backend RESTful APIs using Spring Boot and Hibernate for transaction processing."
            )
        ],
        education=[
            EducationDetail(
                institution="State University of Technology",
                degree="Bachelor of Engineering (B.E.)",
                field_of_study="Computer Engineering",
                year="2023"
            )
        ],
        projects=[
            ProjectDetail(
                title="E-Commerce Microservices Engine",
                description="Designed distributed microservices architecture for order fulfillment and inventory tracking.",
                technologies=["Java", "Spring Boot", "MySQL", "Docker"]
            )
        ],
        certifications=["Oracle Certified Associate, Java SE 8 Programmer"]
    )

