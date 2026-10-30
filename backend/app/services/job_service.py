"""Job dataset loading, indexing, multi-criteria filtering, and transparent match scoring."""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.config import get_settings
from backend.app.schemas.job import (
    JobListing,
    JobMatchResult,
    JobSearchQuery,
)
from backend.app.schemas.resume import ResumeProfile

logger = logging.getLogger("uvicorn.error")


class JobService:
    """Manages the real job dataset with in-memory indexing, search, and transparent scoring."""

    def __init__(self, dataset_path: Optional[str] = None):
        settings = get_settings()
        self.dataset_path = dataset_path or settings.jobs_data_path
        self._jobs: List[JobListing] = []
        self._job_index: Dict[str, JobListing] = {}
        self.load_dataset()

    def load_dataset(self) -> None:
        """Load and index job listings from JSON file."""
        if not os.path.exists(self.dataset_path):
            logger.warning(f"Jobs dataset file not found at: {self.dataset_path}")
            self._jobs = []
            self._job_index = {}
            return

        with open(self.dataset_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        loaded_jobs = []
        for item in raw_data:
            try:
                job = JobListing(**item)
                loaded_jobs.append(job)
            except Exception as e:
                logger.debug(f"Skipping malformed job item: {e}")

        self._jobs = loaded_jobs
        self._job_index = {j.job_id: j for j in self._jobs}
        logger.info(f"Loaded {len(self._jobs)} valid jobs from {self.dataset_path}")

    @property
    def total_count(self) -> int:
        return len(self._jobs)

    def get_job(self, job_id: str) -> Optional[JobListing]:
        """Fetch a specific job by its unique ID."""
        return self._job_index.get(job_id)

    def search_jobs(self, query: JobSearchQuery) -> Tuple[int, List[JobListing]]:
        """Filter jobs using multi-field query parameters."""
        filtered = self._jobs

        # 1. Keyword search across title, company, description
        if query.keyword:
            kw = query.keyword.strip().lower()
            filtered = [
                j for j in filtered
                if kw in j.title.lower() or kw in j.company.lower() or kw in j.description[:500].lower()
            ]

        # 2. Designation / role filter
        if query.designation:
            desig = query.designation.strip().lower()
            filtered = [j for j in filtered if desig in j.title.lower()]

        # 3. Location filter
        if query.location:
            loc = query.location.strip().lower()
            filtered = [j for j in filtered if loc in j.location.lower() or loc in j.title.lower()]

        # 4. Work mode (Remote, Hybrid, Onsite)
        if query.work_mode:
            wm = query.work_mode.strip().lower()
            filtered = [j for j in filtered if j.work_mode.lower() == wm]

        # 5. Skills filter (job must contain at least one of requested skills)
        if query.skills:
            req_skills = {s.strip().lower() for s in query.skills if s.strip()}
            if req_skills:
                filtered = [
                    j for j in filtered
                    if any(s.lower() in req_skills for s in j.skills)
                ]

        # 6. Experience bounds
        if query.min_experience is not None:
            filtered = [j for j in filtered if j.min_experience_years >= query.min_experience]
        if query.max_experience is not None:
            filtered = [j for j in filtered if j.min_experience_years <= query.max_experience]

        total_matches = len(filtered)
        paginated = filtered[query.offset: query.offset + query.limit]
        return total_matches, paginated

    def calculate_match(self, profile: ResumeProfile, job: JobListing) -> JobMatchResult:
        """
        Calculate transparent match score across 4 auditable dimensions:
        - Skills Overlap (50%)
        - Designation / Title Relevance (25%)
        - Experience Compatibility (15%)
        - Location / Remote Fit (10%)
        """
        settings = get_settings()

        # 1. Skills Scoring (50%)
        candidate_skills = {s.lower() for s in profile.skills}
        job_skills = {s.lower() for s in job.skills}

        matching_skill_names = [s for s in job.skills if s.lower() in candidate_skills]
        missing_skill_names = [s for s in job.skills if s.lower() not in candidate_skills]

        if job_skills:
            overlap_ratio = len(matching_skill_names) / len(job_skills)
            score_skills = min(100.0, overlap_ratio * 100.0)
        else:
            score_skills = 70.0  # Default reasonable score if no explicit skills tagged

        # 2. Designation Relevance (25%)
        cand_desig = (profile.designation or "").lower()
        job_title = job.title.lower()

        if cand_desig and cand_desig in job_title:
            score_desig = 100.0
        elif any(token in job_title for token in cand_desig.split() if len(token) > 2):
            score_desig = 75.0
        else:
            # Check broad tech role overlap
            common_roles = ["developer", "engineer", "analyst", "intern", "qa", "architect"]
            if any(r in cand_desig and r in job_title for r in common_roles):
                score_desig = 60.0
            else:
                score_desig = 30.0

        # 3. Experience Compatibility (15%)
        cand_exp = profile.experience_years
        req_exp = job.min_experience_years

        if cand_exp >= req_exp:
            score_exp = 100.0
            exp_fit = f"Compatible: Candidate has {cand_exp:.1f} yr(s) exp (Job requires: {job.experience_required})"
        else:
            diff = req_exp - cand_exp
            score_exp = max(20.0, 100.0 - (diff * 25.0))
            exp_fit = f"Candidate has {cand_exp:.1f} yr(s) exp, job asks for {job.experience_required}"

        # 4. Location Compatibility (10%)
        if job.work_mode == "Remote":
            score_loc = 100.0
        else:
            score_loc = 50.0  # Partial fit for on-site unless explicitly filtered

        # Weighted Total (0 - 100)
        total_score = (
            (score_skills * settings.weight_skills) +
            (score_desig * settings.weight_designation) +
            (score_exp * settings.weight_experience) +
            (score_loc * settings.weight_location)
        )
        total_score = round(max(5.0, min(99.0, total_score)), 1)

        # Generate transparent, clear explanation
        reasons = []
        if matching_skill_names:
            reasons.append(f"Matches {len(matching_skill_names)} required skills: {', '.join(matching_skill_names[:3])}")
        if score_desig >= 75.0:
            reasons.append(f"Title '{job.title}' closely matches target role '{profile.designation}'")
        if job.work_mode == "Remote":
            reasons.append("Remote flexibility")
        reasons.append(exp_fit)

        match_reason = ". ".join(reasons) + "."

        return JobMatchResult(
            job=job,
            match_score=total_score,
            matching_skills=matching_skill_names,
            missing_skills=missing_skill_names[:5],
            experience_fit=exp_fit,
            match_reason=match_reason,
        )

    def match_jobs_for_profile(
        self,
        profile: ResumeProfile,
        filters: Optional[JobSearchQuery] = None,
        top_k: int = 10,
    ) -> List[JobMatchResult]:
        """Rank and return top job recommendations for candidate profile."""
        candidate_pool = self._jobs

        # Apply any active query filters first
        if filters:
            if filters.work_mode:
                candidate_pool = [j for j in candidate_pool if j.work_mode.lower() == filters.work_mode.lower()]
            if filters.location:
                loc = filters.location.lower()
                candidate_pool = [j for j in candidate_pool if loc in j.location.lower()]
            if filters.keyword:
                kw = filters.keyword.lower()
                candidate_pool = [j for j in candidate_pool if kw in j.title.lower() or kw in j.description.lower()]

        scored_results: List[JobMatchResult] = []
        for job in candidate_pool:
            result = self.calculate_match(profile, job)
            scored_results.append(result)

        # Sort descending by match score
        scored_results.sort(key=lambda r: r.match_score, reverse=True)
        return scored_results[:top_k]


# Singleton instance
_job_service_instance: Optional[JobService] = None


def get_job_service() -> JobService:
    """Return JobService singleton."""
    global _job_service_instance
    if _job_service_instance is None:
        _job_service_instance = JobService()
    return _job_service_instance

