"""API router for conversational chat interactions."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.chat_orchestrator import ChatOrchestrator, get_chat_orchestrator

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def handle_chat_message(
    req: ChatRequest,
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator),
):
    """
    Process incoming user message through LangGraph orchestrator.
    Executes intent routing, job searching, matching, application tracking,
    and returns conversational response.
    """
    try:
        return await orchestrator.process_chat(req)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}",
        )

