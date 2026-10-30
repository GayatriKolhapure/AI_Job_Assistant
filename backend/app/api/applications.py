"""API Router for job application management and status updates."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.app.schemas.application import (
    ApplicationCreateRequest,
    ApplicationListResponse,
    ApplicationRecord,
    ApplicationStatusUpdate,
)
from backend.app.services.application_service import (
    ApplicationService,
    DuplicateApplicationError,
)

router = APIRouter(prefix="/api/applications", tags=["Applications"])


@router.post("", response_model=ApplicationRecord, status_code=status.HTTP_201_CREATED)
def record_application(req: ApplicationCreateRequest):
    """
    Record an explicit candidate job application in SQLite.
    Prevents duplicate submissions for the same (session_id, job_id).
    """
    try:
        return ApplicationService.create_application(req)
    except DuplicateApplicationError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record application: {str(e)}",
        )


@router.get("", response_model=ApplicationListResponse)
def list_applications(
    session_id: str = Query(..., description="User session identifier"),
    status: Optional[str] = Query(None, description="Optional status filter"),
):
    """Retrieve all application records for the active session."""
    apps = ApplicationService.list_applications(session_id=session_id, status_filter=status)
    return ApplicationListResponse(total=len(apps), applications=apps)


@router.get("/{application_id}", response_model=ApplicationRecord)
def get_application(
    application_id: str,
    session_id: Optional[str] = Query(None, description="Session ID for isolated access"),
):
    """Retrieve detailed status for a specific application record."""
    record = ApplicationService.get_application(application_id=application_id, session_id=session_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application record '{application_id}' not found.",
        )
    return record


@router.patch("/{application_id}/status", response_model=ApplicationRecord)
def update_application_status(
    application_id: str,
    body: ApplicationStatusUpdate,
    session_id: Optional[str] = Query(None, description="Session ID for ownership verification"),
):
    """Update application progression status (e.g. Under Review, Interview, Rejected, Selected)."""
    updated = ApplicationService.update_status(
        application_id=application_id,
        new_status=body.status,
        session_id=session_id,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application record '{application_id}' not found or cannot be modified.",
        )
    return updated

