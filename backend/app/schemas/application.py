"""Pydantic schemas for job application tracking records and requests."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


def get_utc_now_iso() -> str:
    """Return standard UTC ISO 8601 timestamp with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ApplicationStatus(str, Enum):
    APPLIED = "Applied"
    UNDER_REVIEW = "Under Review"
    INTERVIEW = "Interview"
    REJECTED = "Rejected"
    SELECTED = "Selected"


class ApplicationCreateRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100, description="User session identifier")
    job_id: str = Field(..., min_length=1, max_length=100, description="Target job identifier")
    job_title: str = Field(..., min_length=1, description="Job title")
    company: str = Field(..., min_length=1, description="Employer company name")
    location: str = Field(default="Remote", description="Job location")
    source_link: str = Field(..., description="Official job application URL")


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus = Field(..., description="New application status")


class ApplicationRecord(BaseModel):
    application_id: str
    session_id: str
    job_id: str
    job_title: str
    company: str
    location: str
    source_link: str
    status: ApplicationStatus
    applied_date: str
    created_at: str
    updated_at: str


class ApplicationListResponse(BaseModel):
    total: int
    applications: List[ApplicationRecord]

