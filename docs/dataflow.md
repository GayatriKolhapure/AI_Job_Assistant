# AI Job Chat Assistant — End-to-End Dataflow

This document traces the complete lifecycle of data across candidate interactions, multi-agent graph nodes, dataset indexing, and database persistence.

---

## 1. Resume Upload & Profile Extraction Flow

```mermaid
sequenceDiagram
    autonumber
    actor Candidate
    participant React as React Frontend
    participant API as FastAPI /api/resume/upload
    participant Parser as ResumeParserService (PyMuPDF / docx)
    participant LLM as OpenAI / Deterministic Engine

    Candidate->>React: Uploads Resume (PDF/DOCX)
    React->>API: POST /api/resume/upload (multipart)
    API->>API: Validate file extension & size (< 10MB)
    API->>Parser: extract_text_from_pdf() / docx()
    Parser->>Parser: Extract raw plain text & headings
    Parser->>LLM: Structured profile extraction (JSON Mode)
    Note over Parser,LLM: Falls back to regex & ontology parser if offline/mock
    LLM-->>Parser: Validated ResumeProfile JSON
    Parser-->>API: ResumeParseResponse
    API-->>React: Display candidate name, role & skills tags
    React->>React: Persist profile in active conversation state
```

---

## 2. Conversational Job Matching & Filtering Flow

```mermaid
sequenceDiagram
    autonumber
    actor Candidate
    participant React as React UI
    participant ChatAPI as FastAPI /api/chat
    participant Graph as LangGraph Orchestrator
    participant JobSvc as JobService (1,790 Real Jobs)

    Candidate->>React: "Show only remote Java developer jobs"
    React->>ChatAPI: POST /api/chat {sessionId, message, resumeProfile}
    ChatAPI->>Graph: invoke(AgentState)
    Graph->>Graph: intent_classifier_node -> filter_remote
    Graph->>JobSvc: search_jobs(query: work_mode='Remote', skills=['Java'])
    JobSvc->>JobSvc: Filter 1,790 real jobs in data/jobs.json
    JobSvc->>JobSvc: Calculate 4-factor match score (50/25/15/10)
    JobSvc-->>Graph: Ranked JobMatchResult list
    Graph->>Graph: Formulate conversational reply & prompt pills
    Graph-->>ChatAPI: Final AgentState
    ChatAPI-->>React: ChatResponse with reply & interactive JobCards
    React-->>Candidate: Renders message bubble & match score badges
```

---

## 3. Application Tracking Flow with Duplicate Prevention

```mermaid
sequenceDiagram
    autonumber
    actor Candidate
    participant React as React UI
    participant ChatAPI as FastAPI /api/chat
    participant AppSvc as ApplicationService
    participant SQLite as SQLite (data/applications.db)

    Candidate->>React: Clicks "Track Application" or types "Apply to job 1"
    React->>ChatAPI: POST /api/chat {message: "Apply to job 1"}
    ChatAPI->>AppSvc: create_application(session_id, job_id, ...)
    AppSvc->>SQLite: Check UNIQUE(session_id, job_id)
    alt Already Applied in this session
        SQLite-->>AppSvc: Integrity Violation / Record Exists
        AppSvc-->>ChatAPI: DuplicateApplicationError
        ChatAPI-->>React: Warning: "You have already applied to this position."
    else First Time Application
        SQLite->>SQLite: INSERT INTO applications VALUES (APP-XXXXXXXX, ...)
        SQLite-->>AppSvc: ApplicationRecord (Status: 'Applied')
        AppSvc-->>ChatAPI: Confirmation with official employer source_link
        ChatAPI-->>React: Success badge + Link to employer portal
    end
```

