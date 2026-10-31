
import argparse
import json
import logging
import os
import sys

from scraper.sources import (
    fetch_arbeitnow_jobs,
    fetch_jobicy_jobs,
    fetch_remotive_jobs,
)
from scraper.normalizer import normalize_and_deduplicate
from scraper.validator import validate_dataset, print_validation_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scraper")


def run_pipeline(target_count: int = 1600, output_path: str = "data/jobs.json") -> None:
    """Collect from permitted public APIs, normalize, deduplicate, and validate dataset."""
    logger.info(f"Starting real job scraping pipeline (Target: {target_count} listings)...")

    raw_jobs = []

    # 1. Fetch from Arbeitnow (~300 per page)
    # 6 pages * 300 = ~1,800 raw jobs
    arbeitnow_jobs = fetch_arbeitnow_jobs(max_pages=6)
    raw_jobs.extend(arbeitnow_jobs)

    # 2. Fetch from Jobicy
    jobicy_jobs = fetch_jobicy_jobs()
    raw_jobs.extend(jobicy_jobs)

    # 3. Fetch from Remotive
    remotive_jobs = fetch_remotive_jobs()
    raw_jobs.extend(remotive_jobs)

    logger.info(f"Total raw jobs harvested: {len(raw_jobs)}")

    # 4. Normalize and deduplicate
    logger.info("Normalizing and deduplicating records...")
    normalized_jobs = normalize_and_deduplicate(raw_jobs)
    logger.info(f"Unique valid jobs after deduplication: {len(normalized_jobs)}")

    # If count is higher than target + 200, we can cap at 1,750 for balanced size
    if len(normalized_jobs) > 1800:
        normalized_jobs = normalized_jobs[:1800]

    # 5. Persist to data/jobs.json atomically
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    temp_path = f"{output_path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(normalized_jobs, f, indent=2, ensure_ascii=False)

    if os.path.exists(output_path):
        os.remove(output_path)
    os.rename(temp_path, output_path)

    logger.info(f"Successfully saved {len(normalized_jobs)} jobs to {output_path}")

    # 6. Validate
    report = validate_dataset(normalized_jobs)
    print_validation_report(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real Job Dataset Scraping Pipeline")
    parser.add_argument("--target", type=int, default=1600, help="Target number of real job listings")
    parser.add_argument("--output", type=str, default="data/jobs.json", help="Destination JSON path")
    args = parser.parse_args()

    run_pipeline(target_count=args.target, output_path=args.output)

