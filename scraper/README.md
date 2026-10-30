# Job Scraping & Data Pipeline

**Component**: Real Job Dataset Harvester & Validator  
**Target Goal**: 1,500 – 2,000 Real, Permitted Job Listings  
**Primary Target File**: `data/jobs.json`  

---

## 1. Compliance & Ethical Collection Principles

This project strictly follows ethical web scraping and data harvesting guidelines:
1. **Permitted Public Feeds & Open APIs**:
   - **Arbeitnow API**: Official public API (`https://www.arbeitnow.com/api/job-board-api`) allowing programmatic job discovery for developers.
   - **Jobicy Remote Jobs Feed**: Public API (`https://jobicy.com/api/v2/remote-jobs`) intended for remote job aggregation.
   - **Remotive Open API**: Public developer job feed (`https://remotive.com/api/remote-jobs`).
2. **No Authentication or CAPTCHA Bypassing**: Zero scraping of restricted member portals, behind logins, or protected by CAPTCHAs.
3. **Respectful Rate Limiting**: Built-in 500ms pauses between paginated requests with standardized academic User-Agent headers.
4. **No Synthetic / Fabricated Jobs**: All company names, job titles, direct application URLs, and job descriptions are genuine records from active employers.

---

## 2. Pipeline Execution Commands

### Collect and Rebuild Dataset:
```powershell
.\.venv\Scripts\python.exe -m scraper.main --target 1600 --output data/jobs.json
```

### Validate Dataset Integrity:
```powershell
.\.venv\Scripts\python.exe -m scraper.validator data/jobs.json
```

---

## 3. JSON Record Schema

Each job listing conforms to the assessment contract:
```json
{
  "job_id": "job_a1b2c3d4e5f6",
  "title": "Junior Java Developer",
  "company": "Enterprise Tech Solutions",
  "location": "Remote",
  "work_mode": "Remote",
  "experience_required": "1-3 years experience",
  "min_experience_years": 1.0,
  "skills": ["Java", "Spring Boot", "MySQL", "Docker", "REST API"],
  "description": "Full plain-text job description without HTML tags...",
  "source": "Arbeitnow",
  "source_link": "https://www.arbeitnow.com/jobs/...",
  "posted_date": "2026-10-25"
}
```

