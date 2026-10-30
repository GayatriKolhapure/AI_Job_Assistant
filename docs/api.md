# AI Job Chat Assistant — API Reference

Base URL: `http://127.0.0.1:8000` (or configured `BACKEND_URL`)

---

## 1. System Health

### `GET /health` or `GET /api/health`
Returns runtime diagnostic information and mock mode status.

**Response `200 OK`**:
```json
{
  "status": "healthy",
  "app_name": "Hidani AI Job Assistant",
  "environment": "development",
  "mock_mode": true,
  "version": "1.0.0",
  "timestamp": "2026-10-30T11:35:16.629812Z"
}
```

---

## 2. Resume Extraction

### `POST /api/resume/upload` or `POST /api/resume/parse`
Accepts `multipart/form-data` with a `file` field (`.pdf` or `.docx`). Max 10MB.

**Response `200 OK`**:
```json
{
  "success": true,
  "filename": "sample_resume.pdf",
  "profile": {
    "name": "Demo Candidate",
    "email": "demo.candidate@example.com",
    "phone": "+1 555-0199",
    "designation": "Software Developer",
    "skills": ["Java", "Spring Boot", "MySQL", "Docker", "REST API"],
    "experience_years": 1.0,
    "education": [...],
    "projects": [...],
    "certifications": [...]
  },
  "parse_method": "deterministic",
  "text_preview": "...",
  "message": "Resume parsed successfully."
}
```

### `GET /api/resume/sample`
Returns a verified pre-configured candidate profile for instant demo without manual file upload.

---

## 3. Conversational AI Chat

### `POST /api/chat`
Processes conversational queries through the compiled LangGraph multi-agent orchestrator.

**Request Body**:
```json
{
  "session_id": "sess_user_01",
  "message": "Recommend jobs matching my profile",
  "resume_profile": { ... }
}
```

**Response `200 OK`**:
```json
{
  "session_id": "sess_user_01",
  "reply": "Based on your profile as a Java Developer...",
  "action_type": "jobs_found",
  "jobs": [
    {
      "job": {
        "job_id": "job_01",
        "title": "Junior Java Developer",
        "company": "FinTech Core",
        "location": "Remote",
        "work_mode": "Remote",
        "experience_required": "1-2 years",
        "skills": ["Java", "Spring Boot", "MySQL"],
        "source": "Arbeitnow",
        "source_link": "https://..."
      },
      "match_score": 88.5,
      "matching_skills": ["Java", "Spring Boot"],
      "missing_skills": ["Kafka"],
      "experience_fit": "Compatible: Candidate has 1.0 yr(s) exp",
      "match_reason": "Matches 2 required skills: Java, Spring Boot. Title matches target role. Remote flexibility."
    }
  ],
  "application": null,
  "applications": [],
  "suggested_prompts": ["Show only remote jobs", "Apply to job 1"],
  "timestamp": "2026-10-30T11:35:16Z",
  "is_mock": true
}
```

---

## 4. Jobs Catalog & Search

### `GET /api/jobs`
Query parameters: `limit` (default 10, max 50), `offset` (default 0).

### `GET /api/jobs/{job_id}`
Returns full record details for a specific job ID.

### `POST /api/jobs/search`
Multi-field search filter:
```json
{
  "keyword": "developer",
  "location": "Remote",
  "work_mode": "Remote",
  "skills": ["Python", "FastAPI"],
  "limit": 10,
  "offset": 0
}
```

### `POST /api/jobs/match`
Score and rank the dataset for a given `ResumeProfile`.

---

## 5. Application Tracking

### `POST /api/applications`
Explicitly records an application in SQLite. Enforces `UNIQUE(session_id, job_id)`.

**Request Body**:
```json
{
  "session_id": "sess_user_01",
  "job_id": "job_01",
  "job_title": "Junior Java Developer",
  "company": "FinTech Core",
  "location": "Remote",
  "source_link": "https://..."
}
```

**Response `201 Created`**:
```json
{
  "application_id": "APP-9A8B7C",
  "session_id": "sess_user_01",
  "job_id": "job_01",
  "job_title": "Junior Java Developer",
  "company": "FinTech Core",
  "location": "Remote",
  "source_link": "https://...",
  "status": "Applied",
  "applied_date": "2026-10-30",
  "created_at": "...",
  "updated_at": "..."
}
```

### `GET /api/applications?session_id=sess_user_01`
List all applications recorded for the active session.

### `PATCH /api/applications/{application_id}/status?session_id=sess_user_01`
Update status: `Applied`, `Under Review`, `Interview`, `Rejected`, `Selected`.

