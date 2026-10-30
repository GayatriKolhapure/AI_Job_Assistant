"""Chat orchestration service executing LangGraph workflow with session memory management."""

from collections import defaultdict
import logging
from typing import Any, Dict, List, Optional

from backend.app.agents.orchestrator import AgentState, build_orchestrator_graph
from backend.app.core.config import get_settings
from backend.app.schemas.application import ApplicationRecord
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.schemas.job import JobMatchResult

logger = logging.getLogger("uvicorn.error")


class SessionState:
    """Tracks active conversational context for a session ID."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.resume_profile: Optional[Dict[str, Any]] = None
        self.current_jobs: List[Dict[str, Any]] = []
        self.user_filters: Dict[str, Any] = {}
        self.messages: List[Dict[str, str]] = []

    def update_resume(self, profile: Dict[str, Any]) -> None:
        self.resume_profile = profile

    def add_turn(self, user_msg: str, assistant_reply: str) -> None:
        self.messages.append({"role": "user", "content": user_msg})
        self.messages.append({"role": "assistant", "content": assistant_reply})
        # Maintain max 20 messages (10 turns)
        if len(self.messages) > 20:
            self.messages = self.messages[-20:]


class ChatOrchestrator:
    """Singleton chat manager executing the LangGraph pipeline."""

    def __init__(self):
        self.graph = build_orchestrator_graph()
        self.sessions: Dict[str, SessionState] = defaultdict(lambda: None)
        self.settings = get_settings()

    def get_or_create_session(self, session_id: str) -> SessionState:
        if self.sessions[session_id] is None:
            self.sessions[session_id] = SessionState(session_id)
        return self.sessions[session_id]

    async def process_chat(self, req: ChatRequest) -> ChatResponse:
        """Run user message through LangGraph state machine and persist conversational memory."""
        session = self.get_or_create_session(req.session_id)

        # Update profile if provided in payload
        if req.resume_profile:
            session.update_resume(req.resume_profile.model_dump())

        # Construct initial state
        initial_state: AgentState = {
            "session_id": req.session_id,
            "message": req.message,
            "messages": session.messages,
            "resume_profile": session.resume_profile,
            "current_jobs": session.current_jobs,
            "user_filters": session.user_filters,
            "intent": "",
            "target_job_index": None,
            "selected_job_id": None,
            "application": None,
            "applications_list": [],
            "response_text": "",
            "action_type": "general_chat",
            "suggested_prompts": [],
            "is_mock": self.settings.is_mock_mode,
        }

        # Execute LangGraph state machine
        try:
            final_state = self.graph.invoke(initial_state)
        except Exception as e:
            logger.error(f"LangGraph execution error: {e}", exc_info=True)
            return ChatResponse(
                session_id=req.session_id,
                reply="I encountered an internal error while processing your request. Please try again or rephrase.",
                action_type="error",
                is_mock=self.settings.is_mock_mode,
            )

        # Update session state with graph mutations
        if final_state.get("current_jobs"):
            session.current_jobs = final_state["current_jobs"]
        if final_state.get("resume_profile"):
            session.resume_profile = final_state["resume_profile"]

        reply = final_state.get("response_text", "How else can I assist you with your job search?")
        session.add_turn(req.message, reply)

        # Parse jobs if present
        jobs_models = []
        for j in final_state.get("current_jobs", []):
            try:
                jobs_models.append(JobMatchResult(**j))
            except Exception:
                pass

        # Parse application if present
        app_model = None
        if final_state.get("application"):
            try:
                app_model = ApplicationRecord(**final_state["application"])
            except Exception:
                pass

        # Parse applications list if present
        apps_list_models = []
        for a in final_state.get("applications_list", []):
            try:
                apps_list_models.append(ApplicationRecord(**a))
            except Exception:
                pass

        return ChatResponse(
            session_id=req.session_id,
            reply=reply,
            action_type=final_state.get("action_type", "general_chat"),
            jobs=jobs_models,
            application=app_model,
            applications=apps_list_models,
            suggested_prompts=final_state.get("suggested_prompts", []),
            is_mock=self.settings.is_mock_mode,
        )


_orchestrator: Optional[ChatOrchestrator] = None


def get_chat_orchestrator() -> ChatOrchestrator:
    """Return ChatOrchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ChatOrchestrator()
    return _orchestrator

