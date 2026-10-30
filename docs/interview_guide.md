# AI Job Chat Assistant — Developer Learning & Technical Interview Guide

**Assessment Target**: Hidani Tech — SDE Intern (AI Agents & Automation)  
**Topic**: Technical Defense, Architecture Deep Dive, and Core Engineering Concepts  

---

## 1. Core Module Breakdown

| Module | Location | Primary Responsibility |
|---|---|---|
| **LangGraph Orchestrator** | `backend/app/agents/orchestrator.py` | State graph definition, intent classification, conditional edge routing, tool coordination. |
| **Resume Parser** | `backend/app/services/resume_parser.py` | PyMuPDF PDF extraction, python-docx parsing, skill ontology matching, experience estimation, LLM structuring fallback. |
| **Job Search & Matching Service** | `backend/app/services/job_service.py` | In-memory indexing of 1,790 real jobs, multi-attribute filtering, transparent 4-factor scoring algorithm. |
| **Application Tracker** | `backend/app/services/application_service.py` | SQLite persistence, session isolation, duplicate prevention constraint (`UNIQUE(session_id, job_id)`). |
| **Scraper Pipeline** | `scraper/` | Harvests real listings from permitted APIs (Arbeitnow, Jobicy, Remotive), deduplicates, validates schema. |
| **FastAPI REST API** | `backend/app/api/` | Typed Pydantic request/response validation, CORS middleware, sanitized error handling. |
| **React + TypeScript Frontend** | `frontend/` | Conversational UI, resume upload dropzone, interactive job cards, application history drawer. |

---

## 2. Key Architecture & Design Questions

### Q1: Why did you choose LangGraph instead of a simple linear LangChain chain or single prompt?
**Answer**:
A conversational assistant is inherently non-linear and stateful. A simple linear chain assumes every user message follows the same steps. With **LangGraph**:
1. We define an explicit state machine (`StateGraph`) with typed state (`AgentState`).
2. An **Intent Classifier node** evaluates the user's intent (*match*, *search*, *filter*, *apply*, *history*, or *general chat*).
3. **Conditional edge routing** invokes *only* the specific tool node needed for that action, minimizing latency and compute costs.
4. Graph state carries the active candidate profile, previous job search results, and session ID across conversation turns.

### Q2: How does the Job Matching algorithm work and why not just ask the LLM to give a score?
**Answer**:
Letting an LLM invent match percentages directly leads to hallucinations, non-reproducible scores, and false claims of hiring probability. Instead, we use an **auditable, deterministic 4-factor scoring engine**:
- **Skills Overlap (50%)**: Measures the ratio of required job skills present in the candidate's verified skills list.
- **Designation Relevance (25%)**: Substring and token matching between the candidate's target role and the official job title.
- **Experience Compatibility (15%)**: Evaluates candidate experience years against the role's minimum requirements.
- **Location Fit (10%)**: Grants 100% for Remote positions or matching cities; partial credit for on-site.

The LLM is used purely for natural-language synthesis and explanation, not for arbitrary number generation.

### Q3: How do you prevent duplicate job applications?
**Answer**:
Duplicate prevention is enforced at the database level in SQLite using a compound unique constraint:
```sql
UNIQUE(session_id, job_id)
```
Before executing the `INSERT`, `ApplicationService.is_already_applied()` performs an index check. If a duplicate insert is attempted, SQLite raises `sqlite3.IntegrityError`, which our service catches and translates into a friendly `DuplicateApplicationError`. The user is informed with a clear notice without server crashes.

### Q4: How is candidate privacy and security protected?
**Answer**:
1. **PII Sanitization**: Contact details (phone, email) are kept in memory and session scope; they are never printed in routine application logs.
2. **Safe File Handling**: Uploaded resume files are validated for size (< 10MB) and MIME type (.pdf, .docx). They are stored with randomized UUID filenames to prevent path traversal attacks.
3. **CORS Allowlist**: Configured strictly for authorized frontend origins; unrestricted wildcard `*` is disabled.
4. **Environment Secret Management**: API keys are loaded via Pydantic BaseSettings from `.env`, which is strictly excluded from Git via `.gitignore`.

### Q5: What happens when the OpenAI API key is unavailable or runs out of credits?
**Answer**:
The system implements a **graceful deterministic offline mock fallback**:
1. When `OPENAI_API_KEY=mock` or network timeout occurs, `Settings.is_mock_mode` evaluates to `True`.
2. The LangGraph state machine uses deterministic regex and token parsing to classify intents.
3. Resume parsing uses the PyMuPDF/docx extractor and our comprehensive 100+ skill ontology.
4. Job matching queries the real 1,790 job dataset directly.
5. All 26 automated unit and integration tests pass without requiring external API credits.

---

## 3. Walkthrough Checklist for Interview Demo

1. **Start Services**:
   - Backend: `uvicorn backend.app.main:app --reload`
   - Frontend: `npm run dev` in `frontend/`
2. **Demonstrate Resume Parsing**:
   - Click "Load Demo Profile" or upload a PDF resume.
   - Point out extracted candidate name, designation ("Software Developer"), experience (1.0 yr), and skills list.
3. **Conversational Job Recommendation**:
   - Type *"Recommend jobs for my profile"*.
   - Point out the 6 job cards returned from the 1,790 dataset, the green match score badge (e.g. 88.5%), and the transparent breakdown of matched skills vs desired skills.
4. **Conversational Refinement**:
   - Type *"Show only remote jobs"*.
   - Show how the state graph filters previous results dynamically.
5. **Application Tracking**:
   - Type *"Apply to job 1"*.
   - Point out the generated Application ID (`APP-XXXXXXXX`), the official employer direct application link, and the SQLite persistence.
   - Switch to the "Applications" tab to see the recorded application.
   - Change status to "Interview" using the dropdown.
   - Return to chat and type *"Apply to job 1"* again to demonstrate duplicate application prevention!
6. **Dataset Validation**:
   - Open terminal and run `python -m scraper.validator data/jobs.json` to prove the dataset contains 1,790 verified, usable real job records.

