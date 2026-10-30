"""Job normalization, skill extraction, deduplication, and schema validation pipeline."""

import hashlib
import html
import re
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

from backend.app.services.resume_parser import TECH_SKILLS_ONTOLOGY, ResumeParserService


def strip_html(raw_html: str) -> str:
    """Strip HTML markup and entities into clean plain text."""
    if not raw_html:
        return ""
    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        text = soup.get_text(separator=" ")
    except Exception:
        text = re.sub(r"<[^>]+>", " ", raw_html)
    text = html.unescape(text)
    # Collapse multiple whitespace
    return re.sub(r"\s+", " ", text).strip()


def determine_work_mode(title: str, location: str, remote_flag: Any, description: str) -> str:
    """Determine whether a role is Remote, Hybrid, or Onsite."""
    combined = f"{title} {location} {description[:300]}".lower()

    if remote_flag is True or str(remote_flag).lower() in ("true", "1", "remote", "yes"):
        return "Remote"

    if "hybrid" in combined:
        return "Hybrid"

    if "remote" in combined or "work from home" in combined or "anywhere" in combined:
        return "Remote"

    if location and "remote" in location.lower():
        return "Remote"

    return "Onsite" if location else "Remote"


def extract_experience(title: str, description: str) -> Tuple[str, float]:
    """Extract human-readable experience level and minimum experience years."""
    combined = f"{title} {description[:1000]}".lower()

    # Entry / Fresher detection
    if "intern" in combined or "internship" in combined:
        return "Internship / Student", 0.0
    if "fresher" in combined or "graduate" in combined or "entry level" in combined or "junior" in title.lower():
        return "Fresher / Entry level (0-1 yr)", 0.0

    # Pattern: "X+ years", "X-Y years", "X years of experience"
    exp_match = re.search(r"(\d+)(?:\s*(?:-|to)\s*(\d+))?\+?\s*(?:year|yr)s?\s*(?:of)?\s*experience", combined)
    if exp_match:
        min_yr = float(exp_match.group(1))
        max_yr = float(exp_match.group(2)) if exp_match.group(2) else min_yr + 2.0
        if min_yr == 0:
            return "Fresher / Entry level (0-1 yr)", 0.0
        elif min_yr <= 2:
            return f"1-3 years experience", min_yr
        elif min_yr <= 5:
            return f"3-5 years experience", min_yr
        else:
            return f"5+ years (Senior / Lead)", min_yr

    # Senior detection from title
    if "senior" in title.lower() or "sr." in title.lower() or "lead" in title.lower() or "architect" in title.lower():
        return "5+ years (Senior / Lead)", 5.0

    if "mid" in title.lower() or "intermediate" in title.lower():
        return "2-4 years experience", 2.0

    return "1-3 years experience", 1.0


def extract_skills_from_text(title: str, tags: List[str], description: str) -> List[str]:
    """Extract and normalize all technical skills mentioned in title, tags, or description."""
    skills_found = set()

    # Check tags first
    for tag in tags:
        t_clean = tag.strip().lower()
        if t_clean in TECH_SKILLS_ONTOLOGY:
            skills_found.add(ResumeParserService._format_skill_name(t_clean))

    # Search in title + description
    combined_text = f"{title} {' '.join(tags)} {description[:2000]}".lower()
    for skill in TECH_SKILLS_ONTOLOGY:
        if "+" in skill or "#" in skill or "." in skill:
            escaped = re.escape(skill)
            if re.search(rf"(?:^|\s|[,;/]){escaped}(?:$|\s|[,;/])", combined_text):
                skills_found.add(ResumeParserService._format_skill_name(skill))
        else:
            if re.search(rf"\b{re.escape(skill)}\b", combined_text):
                skills_found.add(ResumeParserService._format_skill_name(skill))

    return sorted(list(skills_found))


def generate_stable_job_id(source_link: str, company: str, title: str) -> str:
    """Generate deterministic, stable job ID based on SHA-256 hash."""
    seed = (source_link or f"{company}_{title}").strip().lower()
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"job_{h}"


def normalize_raw_job(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize raw job payload into the assessment's target JSON schema."""
    source_name = raw.get("_source_name", "Public Job Board")

    # Handle source-specific fields
    if source_name == "Arbeitnow":
        title = (raw.get("title") or "").strip()
        company = (raw.get("company_name") or "").strip()
        location = (raw.get("location") or "Remote").strip()
        remote_flag = raw.get("remote", False)
        desc_html = raw.get("description") or ""
        source_link = (raw.get("url") or "").strip()
        posted_date = raw.get("created_at")
        tags = raw.get("tags") or []
    elif source_name == "Jobicy":
        title = (raw.get("jobTitle") or "").strip()
        company = (raw.get("companyName") or "").strip()
        location = (raw.get("jobGeo") or "Remote").strip()
        remote_flag = True
        desc_html = raw.get("jobDescription") or ""
        source_link = (raw.get("url") or "").strip()
        posted_date = raw.get("pubDate")
        tags = raw.get("jobTags") or []
    elif source_name == "Remotive":
        title = (raw.get("title") or "").strip()
        company = (raw.get("company_name") or "").strip()
        location = (raw.get("candidate_required_location") or "Remote").strip()
        remote_flag = True
        desc_html = raw.get("description") or ""
        source_link = (raw.get("url") or "").strip()
        posted_date = raw.get("publication_date")
        tags = raw.get("tags") or []
    else:
        title = (raw.get("title") or "").strip()
        company = (raw.get("company") or "").strip()
        location = (raw.get("location") or "Remote").strip()
        remote_flag = raw.get("remote", False)
        desc_html = raw.get("description") or ""
        source_link = (raw.get("source_link") or raw.get("url") or "").strip()
        posted_date = raw.get("posted_date")
        tags = raw.get("skills") or []

    # Mandatory field validation
    if not title or not company or not source_link:
        return None

    clean_desc = strip_html(desc_html)
    work_mode = determine_work_mode(title, location, remote_flag, clean_desc)
    exp_text, min_exp_years = extract_experience(title, clean_desc)
    skills = extract_skills_from_text(title, tags, clean_desc)
    if not skills:
        t_low = title.lower()
        if "developer" in t_low or "engineer" in t_low:
            skills = ["Software Engineering", "Git"]
        elif "data" in t_low or "analyst" in t_low:
            skills = ["Data Analysis", "SQL"]
        elif "qa" in t_low or "test" in t_low:
            skills = ["Quality Assurance", "Testing"]
        elif "design" in t_low or "ui" in t_low or "ux" in t_low:
            skills = ["UI/UX Design", "Figma"]
        else:
            skills = ["Software Development"]

    job_id = generate_stable_job_id(source_link, company, title)

    # Clean date
    posted_date_str = str(posted_date)[:10] if posted_date else None

    return {
        "job_id": job_id,
        "title": title,
        "company": company,
        "location": location if location else "Remote",
        "work_mode": work_mode,
        "experience_required": exp_text,
        "min_experience_years": min_exp_years,
        "skills": skills,
        "description": clean_desc[:2500],  # Concise readable description
        "source": source_name,
        "source_link": source_link,
        "posted_date": posted_date_str,
    }


def normalize_and_deduplicate(raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transform list of raw jobs, remove duplicates, and return validated records."""
    seen_ids = set()
    seen_links = set()
    seen_company_titles = set()
    normalized = []

    for r in raw_jobs:
        job = normalize_raw_job(r)
        if not job:
            continue

        jid = job["job_id"]
        link = job["source_link"].lower()
        comp_title = (job["company"].lower(), job["title"].lower())

        if jid in seen_ids or link in seen_links or comp_title in seen_company_titles:
            continue

        seen_ids.add(jid)
        seen_links.add(link)
        seen_company_titles.add(comp_title)
        normalized.append(job)

    return normalized
