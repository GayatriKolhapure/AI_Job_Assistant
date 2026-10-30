"""Pydantic schemas for structured resume extraction and profile validation."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ExperienceDetail(BaseModel):
    role: str = Field(default="", description="Job title or role")
    company: str = Field(default="", description="Company or organization name")
    duration: str = Field(default="", description="Duration or dates of employment")
    description: str = Field(default="", description="Key responsibilities or summary")


class EducationDetail(BaseModel):
    institution: str = Field(default="", description="University, college, or school name")
    degree: str = Field(default="", description="Degree or diploma earned")
    field_of_study: str = Field(default="", description="Major or area of specialization")
    year: Optional[str] = Field(default="", description="Graduation year or dates attended")


class ProjectDetail(BaseModel):
    title: str = Field(default="", description="Project title")
    description: str = Field(default="", description="Brief project description")
    technologies: List[str] = Field(default_factory=list, description="Technologies or tools used")


class ResumeProfile(BaseModel):
    name: str = Field(default="", description="Candidate full name")
    email: str = Field(default="", description="Email address")
    phone: str = Field(default="", description="Contact phone number")
    designation: str = Field(default="", description="Current or target professional designation")
    skills: List[str] = Field(default_factory=list, description="Technical and soft skills list")
    experience_years: float = Field(default=0.0, ge=0.0, description="Total estimated years of experience")
    experience_details: List[ExperienceDetail] = Field(default_factory=list)
    education: List[EducationDetail] = Field(default_factory=list)
    projects: List[ProjectDetail] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)

    @field_validator("skills", mode="before")
    @classmethod
    def clean_skills(cls, v):
        if isinstance(v, list):
            cleaned = []
            for item in v:
                if isinstance(item, str):
                    s = item.strip()
                    if s and s not in cleaned:
                        cleaned.append(s)
            return cleaned
        return []


class ResumeParseResponse(BaseModel):
    success: bool
    filename: str
    profile: Optional[ResumeProfile] = None
    parse_method: str = Field(default="deterministic", description="Method used: 'llm' or 'deterministic'")
    text_preview: str = Field(default="", description="Truncated preview of extracted text")
    message: str = Field(default="Resume parsed successfully")

