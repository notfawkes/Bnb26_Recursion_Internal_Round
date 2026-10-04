from fastapi import APIRouter, HTTPException

from app.schemas.artifact import (
    ArtifactDetectionResponse,
    ArtifactHashRequest,
    ArtifactHashResponse,
    ArtifactInspectionRequest,
)
from app.services.project_inspection_service import (
    ProjectInspectionError,
    ProjectInspectionService,
)


router = APIRouter(prefix="/api/v1/artifacts", tags=["Artifact inspection"])


@router.post("/detect", response_model=ArtifactDetectionResponse)
async def detect_artifact(payload: ArtifactInspectionRequest):
    """Detect project type and one committed release artifact at a pinned commit."""
    try:
        return ProjectInspectionService.detect(payload.repository_url, payload.commit_sha)
    except ProjectInspectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/hash", response_model=ArtifactHashResponse)
async def hash_artifact(payload: ArtifactHashRequest):
    """Re-fetch the pinned commit and stream SHA-256 over the selected artifact bytes."""
    try:
        return ProjectInspectionService.hash_artifact(
            payload.repository_url, payload.commit_sha, payload.artifact_path
        )
    except ProjectInspectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
