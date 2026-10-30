"""API endpoints for job listing, multi-parameter search, and profile matching."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.schemas.job import (
    JobListing,
    JobMatchResponse,
    JobSearchQuery,
    JobSearchResponse,
)
from backend.app.schemas.resume import ResumeProfile
from backend.app.services.job_service import JobService, get_job_service

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.get("", response_model=JobSearchResponse)
def list_jobs(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    job_service: JobService = Depends(get_job_service),
):
    """Retrieve paginated job listings from the 1,500+ job dataset."""
    query = JobSearchQuery(limit=limit, offset=offset)
    total, results = job_service.search_jobs(query)
    return JobSearchResponse(total=total, count=len(results), results=results)


@router.get("/{job_id}", response_model=JobListing)
def get_job_by_id(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
):
    """Fetch complete details for a specific job posting."""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job listing '{job_id}' not found.",
        )
    return job


@router.post("/search", response_model=JobSearchResponse)
def search_jobs(
    query: JobSearchQuery,
    job_service: JobService = Depends(get_job_service),
):
    """Search and filter the job dataset by role, location, remote mode, or skills."""
    total, results = job_service.search_jobs(query)
    return JobSearchResponse(total=total, count=len(results), results=results)


@router.post("/match", response_model=JobMatchResponse)
def match_profile_jobs(
    profile: ResumeProfile,
    work_mode: Optional[str] = Query(None, description="Optional work mode filter (Remote/Hybrid/Onsite)"),
    location: Optional[str] = Query(None, description="Optional location filter"),
    limit: int = Query(10, ge=1, le=30),
    job_service: JobService = Depends(get_job_service),
):
    """
    Score and rank the dataset for a candidate profile using transparent 4-factor scoring:
    Skills (50%), Designation (25%), Experience (15%), Location (10%).
    """
    filters = JobSearchQuery(work_mode=work_mode, location=location) if (work_mode or location) else None
    matches = job_service.match_jobs_for_profile(profile, filters=filters, top_k=limit)
    return JobMatchResponse(
        total=len(matches),
        candidate_designation=profile.designation,
        matches=matches,
    )

