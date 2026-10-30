"""Pydantic schemas for job listings, search filters, and matching results."""

from typing import List, Optional
from pydantic import BaseModel, Field


class JobListing(BaseModel):
    job_id: str = Field(..., description="Unique stable job identifier")
    title: str = Field(..., description="Official job title")
    company: str = Field(..., description="Hiring company name")
    location: str = Field(default="Remote", description="Job location or Remote")
    work_mode: str = Field(default="Remote", description="Remote, Hybrid, or Onsite")
    experience_required: str = Field(default="Fresher / Entry level", description="Experience description")
    min_experience_years: float = Field(default=0.0, ge=0.0, description="Normalized minimum required experience in years")
    skills: List[str] = Field(default_factory=list, description="Required technical skills")
    description: str = Field(default="", description="Full or summarized job description")
    source: str = Field(default="Permitted Public Feed", description="Source platform name")
    source_link: str = Field(..., description="Official direct application URL")
    posted_date: Optional[str] = Field(default=None, description="Publication date if available")


class JobMatchResult(BaseModel):
    job: JobListing
    match_score: float = Field(..., ge=0.0, le=100.0, description="Calculated match percentage (0-100%)")
    matching_skills: List[str] = Field(default_factory=list, description="Skills present in both resume and job requirements")
    missing_skills: List[str] = Field(default_factory=list, description="Required skills from job not found in resume")
    experience_fit: str = Field(default="Compatible", description="Assessment of candidate experience vs required")
    match_reason: str = Field(..., description="Clear explanation of why this job is recommended")


class JobSearchQuery(BaseModel):
    keyword: Optional[str] = None
    designation: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[str] = None  # Remote, Hybrid, Onsite
    skills: Optional[List[str]] = None
    min_experience: Optional[float] = None
    max_experience: Optional[float] = None
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


class JobSearchResponse(BaseModel):
    total: int
    count: int
    results: List[JobListing]


class JobMatchResponse(BaseModel):
    total: int
    candidate_designation: str
    matches: List[JobMatchResult]

