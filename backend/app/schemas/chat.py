"""Pydantic schemas for conversational chat interactions and multi-agent state payload."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from backend.app.schemas.application import ApplicationRecord
from backend.app.schemas.job import JobMatchResult
from backend.app.schemas.resume import ResumeProfile


def get_utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: str = Field(default_factory=get_utc_now_iso)


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100, description="Active user session ID")
    message: str = Field(..., min_length=1, max_length=2000, description="User conversational message")
    resume_profile: Optional[ResumeProfile] = Field(default=None, description="Optional active candidate profile")

    @field_validator("message")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Message cannot be empty or contain only whitespace.")
        return clean


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    action_type: str = Field(default="general_chat", description="Identified action or tool response type")
    jobs: List[JobMatchResult] = Field(default_factory=list, description="Job recommendations if applicable")
    application: Optional[ApplicationRecord] = Field(default=None, description="Created or queried application record")
    applications: List[ApplicationRecord] = Field(default_factory=list, description="Application history list")
    suggested_prompts: List[str] = Field(default_factory=list, description="Contextual quick reply suggestions")
    timestamp: str = Field(default_factory=get_utc_now_iso)
    is_mock: bool = False

