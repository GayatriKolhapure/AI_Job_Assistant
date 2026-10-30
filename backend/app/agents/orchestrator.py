"""LangGraph multi-agent orchestrator for conversational job assistant."""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from langgraph.graph import StateGraph, END

from backend.app.core.config import get_settings
from backend.app.schemas.application import ApplicationCreateRequest
from backend.app.schemas.job import JobMatchResult, JobSearchQuery
from backend.app.schemas.resume import ResumeProfile
from backend.app.services.application_service import (
    ApplicationService,
    DuplicateApplicationError,
)
from backend.app.services.job_service import get_job_service

logger = logging.getLogger("uvicorn.error")


class AgentState(TypedDict):
    session_id: str
    message: str
    messages: List[Dict[str, str]]
    resume_profile: Optional[Dict[str, Any]]
    current_jobs: List[Dict[str, Any]]
    user_filters: Dict[str, Any]
    intent: str
    target_job_index: Optional[int]
    selected_job_id: Optional[str]
    application: Optional[Dict[str, Any]]
    applications_list: List[Dict[str, Any]]
    response_text: str
    action_type: str
    suggested_prompts: List[str]
    is_mock: bool


def classify_intent(message: str, current_jobs: List[Dict[str, Any]]) -> Tuple[str, Optional[int]]:
    """
    Classify user message intent using rule-based pattern matching
    with conversational reference resolution (e.g. 'Apply to job 2').
    """
    msg = message.strip().lower()

    # 1. Apply to a specific job
    apply_pattern = r"\bapply\b.*?\b(?:to\s+)?(?:job\s+)?(?:#\s*)?(\d+)\b"
    apply_match = re.search(apply_pattern, msg)
    if apply_match:
        idx = int(apply_match.group(1)) - 1  # 1-indexed to 0-indexed
        return "apply_job", idx

    if re.search(r"\bapply\b", msg) and ("this job" in msg or "first" in msg):
        return "apply_job", 0

    # 2. View applied jobs / application status
    if any(k in msg for k in ["my application", "applied job", "applied to", "application status", "track application"]):
        return "view_applications", None

    # 3. Filter current results
    if any(k in msg for k in ["only remote", "remote only", "remote jobs", "show remote"]):
        return "filter_remote", None

    if any(k in msg for k in ["require", "skills in", "using", "with "]) and any(s in msg for s in ["spring", "python", "java", "react", "sql", "docker", "aws"]):
        return "filter_skill", None

    # 4. Search jobs / Role specific
    if any(k in msg for k in ["developer", "engineer", "analyst", "intern", "jobs in", "fresher", "search"]):
        return "search_jobs", None

    # 5. Recommend / Match based on profile
    if any(k in msg for k in ["recommend", "suitable", "match", "for me", "profile", "my skills", "find jobs"]):
        return "match_profile", None

    # 6. Profile inquiry
    if any(k in msg for k in ["my resume", "my profile", "extracted details", "what are my skills"]):
        return "query_profile", None

    # 7. Greetings & Help
    if any(k in msg for k in ["hi", "hello", "hey", "help", "who are you", "what can you do"]):
        return "greeting", None

    return "general_chat", None


def intent_classifier_node(state: AgentState) -> Dict[str, Any]:
    """Node: classify user intent and resolve job references."""
    message = state.get("message", "")
    current_jobs = state.get("current_jobs", [])
    intent, target_idx = classify_intent(message, current_jobs)
    return {
        "intent": intent,
        "target_job_index": target_idx,
    }


def match_profile_node(state: AgentState) -> Dict[str, Any]:
    """Node: Recommend jobs matching the candidate's parsed resume profile."""
    job_service = get_job_service()
    raw_profile = state.get("resume_profile")

    if not raw_profile:
        reply = (
            "I would be glad to find the best job matches for you! Please upload your resume in "
            "PDF or DOCX format using the upload button on the left, or tell me your technical "
            "skills, target role, and years of experience."
        )
        return {
            "response_text": reply,
            "action_type": "need_resume",
            "suggested_prompts": ["Upload sample profile", "Show remote Java jobs", "Show Python fresher jobs"],
        }

    profile = ResumeProfile(**raw_profile)
    matches = job_service.match_jobs_for_profile(profile, top_k=6)
    jobs_dicts = [m.model_dump() for m in matches]

    top_title = matches[0].job.title if matches else "Software Engineering"
    reply = (
        f"Based on your profile as a **{profile.designation}** with skills in "
        f"*{', '.join(profile.skills[:4])}*, I found **{len(matches)} highly relevant job openings** "
        f"from our dataset of 1,700+ active listings. Each recommendation includes an auditable "
        f"match score (50% Skills, 25% Title, 15% Experience, 10% Location). "
        f"You can tell me to filter by remote status, or type *'Apply to job 1'* to track an application."
    )

    return {
        "current_jobs": jobs_dicts,
        "response_text": reply,
        "action_type": "jobs_found",
        "suggested_prompts": ["Show only remote jobs", "Apply to job 1", "Show Spring Boot jobs"],
    }


def search_jobs_node(state: AgentState) -> Dict[str, Any]:
    """Node: Structured search across the 1,500+ job dataset."""
    job_service = get_job_service()
    msg = state.get("message", "").lower()

    # Extract query intent
    work_mode = "Remote" if ("remote" in msg) else None

    # Detect skills mentioned in query
    skills = []
    for s in ["java", "python", "react", "spring boot", "sql", "docker", "fastapi", "aws", "node.js"]:
        if s in msg:
            skills.append(s)

    # Detect location
    location = None
    for loc in ["pune", "bangalore", "mumbai", "delhi", "berlin", "london", "usa", "remote"]:
        if loc in msg:
            location = loc
            break

    # Determine keyword
    keyword = None
    for kw in ["developer", "engineer", "analyst", "intern", "fresher", "backend", "frontend", "full stack"]:
        if kw in msg:
            keyword = kw
            break

    query = JobSearchQuery(
        keyword=keyword,
        location=location,
        work_mode=work_mode,
        skills=skills if skills else None,
        limit=6,
    )
    total, results = job_service.search_jobs(query)

    # Wrap in match format with transparent explanation
    matches = []
    raw_profile = state.get("resume_profile")
    profile = ResumeProfile(**raw_profile) if raw_profile else None

    for job in results:
        if profile:
            matches.append(job_service.calculate_match(profile, job))
        else:
            matches.append(JobMatchResult(
                job=job,
                match_score=85.0 if job.work_mode == "Remote" else 75.0,
                matching_skills=job.skills[:3],
                missing_skills=[],
                experience_fit=job.experience_required,
                match_reason=f"Matches your search criteria. Location: {job.location} ({job.work_mode}).",
            ))

    jobs_dicts = [m.model_dump() for m in matches]

    reply = (
        f"I searched our live dataset of 1,700+ real positions and found **{total} matching jobs**. "
        f"Here are the top {len(results)} opportunities. You can refine your search or type "
        f"*'Apply to job 1'* to track an application."
    )

    return {
        "current_jobs": jobs_dicts,
        "response_text": reply,
        "action_type": "jobs_found",
        "suggested_prompts": ["Show only remote jobs", "Apply to job 1", "Show my applied jobs"],
    }


def filter_node(state: AgentState) -> Dict[str, Any]:
    """Node: Apply conversational filter (e.g. remote only, specific skill) to previous results."""
    current_jobs_raw = state.get("current_jobs", [])
    msg = state.get("message", "").lower()
    intent = state.get("intent", "")

    job_service = get_job_service()
    raw_profile = state.get("resume_profile")
    profile = ResumeProfile(**raw_profile) if raw_profile else None

    if "remote" in msg or intent == "filter_remote":
        query = JobSearchQuery(work_mode="Remote", limit=6)
        total, results = job_service.search_jobs(query)
    elif "spring" in msg:
        query = JobSearchQuery(skills=["Spring Boot", "Java"], limit=6)
        total, results = job_service.search_jobs(query)
    elif "python" in msg:
        query = JobSearchQuery(skills=["Python"], limit=6)
        total, results = job_service.search_jobs(query)
    else:
        query = JobSearchQuery(keyword=msg, limit=6)
        total, results = job_service.search_jobs(query)

    matches = []
    for job in results:
        if profile:
            matches.append(job_service.calculate_match(profile, job))
        else:
            matches.append(JobMatchResult(
                job=job,
                match_score=88.0 if job.work_mode == "Remote" else 78.0,
                matching_skills=job.skills[:3],
                missing_skills=[],
                experience_fit=job.experience_required,
                match_reason=f"Filtered result matching '{msg}'. Location: {job.location}.",
            ))

    jobs_dicts = [m.model_dump() for m in matches]

    reply = (
        f"I updated your results to reflect your preference (*{msg}*). "
        f"Found **{len(jobs_dicts)} refined positions** from our real dataset."
    )

    return {
        "current_jobs": jobs_dicts,
        "response_text": reply,
        "action_type": "jobs_found",
        "suggested_prompts": ["Apply to job 1", "Show jobs with Docker", "Show my applied jobs"],
    }


def apply_job_node(state: AgentState) -> Dict[str, Any]:
    """Node: Record job application in SQLite and provide official employer apply link."""
    session_id = state.get("session_id", "default_session")
    target_idx = state.get("target_job_index", 0)
    current_jobs = state.get("current_jobs", [])

    if not current_jobs:
        return {
            "response_text": "You haven't searched or viewed any jobs yet. Please ask me to recommend jobs or search for roles first!",
            "action_type": "error",
            "suggested_prompts": ["Recommend jobs for me", "Show remote Java jobs"],
        }

    if target_idx is None or target_idx < 0 or target_idx >= len(current_jobs):
        return {
            "response_text": f"I couldn't identify job #{target_idx + 1 if target_idx is not None else '?'}. Please select a job between 1 and {len(current_jobs)}.",
            "action_type": "error",
            "suggested_prompts": [f"Apply to job 1", f"Apply to job {min(2, len(current_jobs))}"],
        }

    job_entry = current_jobs[target_idx]
    job_data = job_entry.get("job", job_entry)

    job_id = job_data.get("job_id")
    title = job_data.get("title")
    company = job_data.get("company")
    location = job_data.get("location", "Remote")
    source_link = job_data.get("source_link")

    req = ApplicationCreateRequest(
        session_id=session_id,
        job_id=job_id,
        job_title=title,
        company=company,
        location=location,
        source_link=source_link,
    )

    try:
        record = ApplicationService.create_application(req)
        reply = (
            f"**Application Recorded Successfully!**\n\n"
            f"• **Application ID**: `{record.application_id}`\n"
            f"• **Position**: **{title}**\n"
            f"• **Company**: **{company}**\n"
            f"• **Status**: `{record.status.value}`\n\n"
            f"*(Notice: This application has been saved to your personal tracking history. "
            f"To complete your external submission with the employer, please visit their official job link: "
            f"[{company} Career Portal]({source_link}))*"
        )
        return {
            "application": record.model_dump(),
            "response_text": reply,
            "action_type": "applied",
            "suggested_prompts": ["Show my applied jobs", "Recommend more jobs", "Show only remote jobs"],
        }
    except DuplicateApplicationError as e:
        reply = f"[Notice: Already Applied] {str(e)}\n\nYou can view your application status anytime by typing *'Show my applied jobs'*."
        return {
            "response_text": reply,
            "action_type": "duplicate_application",
            "suggested_prompts": ["Show my applied jobs", "Recommend more jobs"],
        }


def view_applications_node(state: AgentState) -> Dict[str, Any]:
    """Node: Retrieve and display application tracking history for the session."""
    session_id = state.get("session_id", "default_session")
    apps = ApplicationService.list_applications(session_id=session_id)
    apps_dicts = [a.model_dump() for a in apps]

    if not apps:
        reply = (
            "You haven't tracked any job applications yet in this session. "
            "When you find an interesting position, just type *'Apply to job 1'* to record it!"
        )
        return {
            "applications_list": [],
            "response_text": reply,
            "action_type": "application_list",
            "suggested_prompts": ["Recommend jobs for me", "Show Java developer jobs"],
        }

    lines = [f"Here is your active application history (**{len(apps)} applications**):\n"]
    for i, a in enumerate(apps, 1):
        lines.append(f"{i}. **{a.job_title}** at **{a.company}** — Status: `{a.status.value}` (Applied: {a.applied_date})")

    lines.append("\nYou can continue searching or refine your criteria anytime.")
    return {
        "applications_list": apps_dicts,
        "response_text": "\n".join(lines),
        "action_type": "application_list",
        "suggested_prompts": ["Recommend more jobs", "Show only remote jobs"],
    }


def query_profile_node(state: AgentState) -> Dict[str, Any]:
    """Node: Display candidate's extracted profile details."""
    raw_profile = state.get("resume_profile")
    if not raw_profile:
        reply = "You haven't uploaded a resume yet. You can upload a PDF or DOCX file using the sidebar, or load our sample candidate profile!"
        return {
            "response_text": reply,
            "action_type": "need_resume",
            "suggested_prompts": ["Upload sample profile", "Show remote jobs"],
        }

    p = ResumeProfile(**raw_profile)
    reply = (
        f"### Candidate Profile Overview\n\n"
        f"• **Name**: {p.name}\n"
        f"• **Email**: {p.email or 'Not specified'}\n"
        f"• **Target Role**: {p.designation}\n"
        f"• **Experience**: {p.experience_years:.1f} years\n"
        f"• **Recognized Skills ({len(p.skills)})**: {', '.join(p.skills)}\n"
        f"• **Education**: {p.education[0].degree if p.education else 'Engineering'}\n\n"
        f"Would you like me to find the best job matches for these skills?"
    )
    return {
        "response_text": reply,
        "action_type": "profile_view",
        "suggested_prompts": ["Recommend jobs for me", "Show only remote jobs"],
    }


def general_chat_node(state: AgentState) -> Dict[str, Any]:
    """Node: Friendly conversational guidance and suggestions."""
    reply = (
        "Hello! I'm your AI Job Assistant.\n\n"
        "I can help you find the right job opportunities and manage your job search.\n\n"
        "**1. Resume Analysis**\n"
        "Upload your PDF or DOCX resume to extract your skills, education, experience, and projects.\n\n"
        "**2. Smart Job Recommendations**\n"
        "Discover relevant opportunities from 1,700+ job listings based on your profile.\n\n"
        "**3. Advanced Job Search**\n"
        "Find jobs by role, skills, location, experience level, and remote preferences.\n\n"
        "**4. Job Match Insights**\n"
        "Understand why a particular job matches your skills and experience.\n\n"
        "**5. Application Tracking**\n"
        "Keep track of your selected job applications and check their status.\n\n"
        "Let's get started! Upload your resume or ask me to find suitable jobs."
    )
    return {
        "response_text": reply,
        "action_type": "greeting",
        "suggested_prompts": [
            "Recommend jobs for me",
            "Show remote Python jobs",
            "Show Java fresher jobs",
            "What can you do?",
        ],
    }


def route_intent(state: AgentState) -> str:
    """Routing function for conditional edges in LangGraph."""
    intent = state.get("intent")
    if intent == "apply_job":
        return "apply_job_node"
    elif intent == "view_applications":
        return "view_applications_node"
    elif intent in ("filter_remote", "filter_skill"):
        return "filter_node"
    elif intent == "search_jobs":
        return "search_jobs_node"
    elif intent == "match_profile":
        return "match_profile_node"
    elif intent == "query_profile":
        return "query_profile_node"
    else:
        return "general_chat_node"


def build_orchestrator_graph():
    """Construct and compile the LangGraph StateGraph workflow."""
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("intent_classifier_node", intent_classifier_node)
    workflow.add_node("match_profile_node", match_profile_node)
    workflow.add_node("search_jobs_node", search_jobs_node)
    workflow.add_node("filter_node", filter_node)
    workflow.add_node("apply_job_node", apply_job_node)
    workflow.add_node("view_applications_node", view_applications_node)
    workflow.add_node("query_profile_node", query_profile_node)
    workflow.add_node("general_chat_node", general_chat_node)

    # Set Entry Point
    workflow.set_entry_point("intent_classifier_node")

    # Add Conditional Edges from classifier
    workflow.add_conditional_edges(
        "intent_classifier_node",
        route_intent,
        {
            "match_profile_node": "match_profile_node",
            "search_jobs_node": "search_jobs_node",
            "filter_node": "filter_node",
            "apply_job_node": "apply_job_node",
            "view_applications_node": "view_applications_node",
            "query_profile_node": "query_profile_node",
            "general_chat_node": "general_chat_node",
        }
    )

    # All action nodes terminate at END
    workflow.add_edge("match_profile_node", END)
    workflow.add_edge("search_jobs_node", END)
    workflow.add_edge("filter_node", END)
    workflow.add_edge("apply_job_node", END)
    workflow.add_edge("view_applications_node", END)
    workflow.add_edge("query_profile_node", END)
    workflow.add_edge("general_chat_node", END)

    return workflow.compile()
