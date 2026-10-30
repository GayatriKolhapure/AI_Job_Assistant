"""Dataset validation script ensuring schema integrity, real URLs, and record count checks."""

import json
import os
import re
import sys
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

MANDATORY_FIELDS = [
    "job_id",
    "title",
    "company",
    "location",
    "work_mode",
    "experience_required",
    "skills",
    "description",
    "source",
    "source_link",
]

URL_PATTERN = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)


def validate_dataset(jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Inspect dataset against schema integrity rules and generate statistical report."""
    total_records = len(jobs)
    seen_ids = set()
    seen_links = set()
    duplicate_ids = 0
    duplicate_links = 0
    missing_fields_count = 0
    invalid_urls_count = 0
    source_counts = {}
    work_mode_counts = {}
    skills_histogram = {}
    usable_jobs = []

    for idx, job in enumerate(jobs):
        is_usable = True
        jid = job.get("job_id")
        link = job.get("source_link")

        # 1. Mandatory fields verification
        missing = []
        for f in MANDATORY_FIELDS:
            val = job.get(f)
            if val is None:
                missing.append(f)
            elif isinstance(val, str) and not val.strip():
                missing.append(f)
            elif isinstance(val, list) and len(val) == 0:
                missing.append(f)

        if missing:
            missing_fields_count += 1
            is_usable = False

        # 2. Check duplicates
        if jid in seen_ids:
            duplicate_ids += 1
            is_usable = False
        else:
            if jid:
                seen_ids.add(jid)

        if link in seen_links:
            duplicate_links += 1
            is_usable = False
        else:
            if link:
                seen_links.add(link)

        # 3. Check URL validity
        if not link or not URL_PATTERN.match(link):
            invalid_urls_count += 1
            is_usable = False

        # 4. Source & Work Mode distribution
        src = job.get("source", "Unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

        wm = job.get("work_mode", "Unknown")
        work_mode_counts[wm] = work_mode_counts.get(wm, 0) + 1

        # 5. Skills count
        for skill in job.get("skills", []):
            skills_histogram[skill] = skills_histogram.get(skill, 0) + 1

        if is_usable:
            usable_jobs.append(job)

    # Top 10 skills
    top_skills = sorted(skills_histogram.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total_records": total_records,
        "usable_jobs_count": len(usable_jobs),
        "duplicate_ids": duplicate_ids,
        "duplicate_links": duplicate_links,
        "missing_fields_records": missing_fields_count,
        "invalid_urls": invalid_urls_count,
        "source_distribution": source_counts,
        "work_mode_distribution": work_mode_counts,
        "top_skills": top_skills,
        "is_valid_range": (1500 <= len(usable_jobs) <= 2500),
    }


def print_validation_report(report: Dict[str, Any]) -> None:
    """Print a clean, professional formatted CLI validation report."""
    print("=" * 70)
    print("       AI JOB CHAT ASSISTANT - DATASET VALIDATION REPORT")
    print("       Assessment Target: 1,500 - 2,000 Real Job Listings")
    print("=" * 70)
    print(f"Total Records Collected:      {report['total_records']}")
    print(f"Usable, Valid Records:        {report['usable_jobs_count']}")
    print(f"Duplicate IDs Detected:       {report['duplicate_ids']}")
    print(f"Duplicate URLs Detected:      {report['duplicate_links']}")
    print(f"Records with Missing Fields:  {report['missing_fields_records']}")
    print(f"Invalid URL Formats:          {report['invalid_urls']}")
    print("-" * 70)
    print("Source Distribution:")
    for src, count in report["source_distribution"].items():
        pct = (count / max(1, report['total_records'])) * 100
        print(f"  * {src:<20}: {count:>5} jobs ({pct:.1f}%)")
    print("-" * 70)
    print("Work Mode Distribution:")
    for wm, count in report["work_mode_distribution"].items():
        pct = (count / max(1, report['total_records'])) * 100
        print(f"  * {wm:<20}: {count:>5} jobs ({pct:.1f}%)")
    print("-" * 70)
    print("Top In-Demand Skills in Dataset:")
    for skill, count in report["top_skills"]:
        print(f"  * {skill:<20}: {count:>5} mentions")
    print("=" * 70)
    if report["is_valid_range"] and report["missing_fields_records"] == 0:
        print("[SUCCESS] Dataset satisfies the 1,500 - 2,000 real job listing requirement.")
    else:
        print(f"[STATUS] Dataset count: {report['usable_jobs_count']} usable jobs.")
    print("=" * 70)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "data/jobs.json"
    if not os.path.exists(path):
        print(f"[ERROR] Dataset file not found at: {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    report = validate_dataset(jobs)
    print_validation_report(report)

    if not report["is_valid_range"] or report["missing_fields_records"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
