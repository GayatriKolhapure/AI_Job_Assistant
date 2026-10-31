
import logging
import time
from typing import Any, Dict, List
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "HidaniJobAssistantAssessment/1.0 (Educational Academic Project; contact@hidani.tech)",
    "Accept": "application/json",
}


def fetch_arbeitnow_jobs(max_pages: int = 6) -> List[Dict[str, Any]]:
    """
    Fetch jobs from Arbeitnow's official permitted public API.
    Provides ~300 jobs per page across global and EU tech employers.
    """
    base_url = "https://www.arbeitnow.com/api/job-board-api"
    collected = []

    for page in range(1, max_pages + 1):
        try:
            url = f"{base_url}?page={page}"
            logger.info(f"Fetching Arbeitnow jobs page {page}/{max_pages}...")
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"Arbeitnow returned status {resp.status_code} on page {page}")
                break

            data = resp.json()
            jobs = data.get("data", [])
            if not jobs:
                break

            for j in jobs:
                j["_source_name"] = "Arbeitnow"
                collected.append(j)

            # Respectful rate limiting between page requests
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error fetching page {page} from Arbeitnow: {e}")
            break

    logger.info(f"Collected {len(collected)} raw jobs from Arbeitnow.")
    return collected


def fetch_jobicy_jobs() -> List[Dict[str, Any]]:
    """
    Fetch remote jobs from Jobicy's official open public feed.
    """
    categories = ["engineering", "dev", "data", "devops"]
    collected = []

    for cat in categories:
        try:
            url = f"https://jobicy.com/api/v2/remote-jobs?count=50&tag={cat}"
            logger.info(f"Fetching Jobicy remote jobs for tag '{cat}'...")
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                jobs = data.get("jobs", [])
                for j in jobs:
                    j["_source_name"] = "Jobicy"
                    collected.append(j)
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error fetching from Jobicy ({cat}): {e}")

    logger.info(f"Collected {len(collected)} raw jobs from Jobicy.")
    return collected


def fetch_remotive_jobs() -> List[Dict[str, Any]]:
    """
    Fetch developer listings from Remotive open API.
    """
    url = "https://remotive.com/api/remote-jobs"
    collected = []
    try:
        logger.info("Fetching Remotive remote jobs...")
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            jobs = data.get("jobs", [])
            for j in jobs:
                j["_source_name"] = "Remotive"
                collected.append(j)
    except Exception as e:
        logger.error(f"Error fetching Remotive jobs: {e}")

    logger.info(f"Collected {len(collected)} raw jobs from Remotive.")
    return collected

