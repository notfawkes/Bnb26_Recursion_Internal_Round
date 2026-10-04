from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.schemas.release import ReleaseCreate, ReleaseResponse
from app.schemas.verification import VerificationResponse
from app.services.release_service import ReleaseService
from app.dependencies import get_release_service, mock_builder_manager
from app.core.exceptions import QuorumException, ReleaseNotFoundError

router = APIRouter(prefix="/api/v1/releases", tags=["Releases"])


@router.post("", response_model=ReleaseResponse, status_code=status.HTTP_201_CREATED)
async def create_release(
    payload: ReleaseCreate,
    service: ReleaseService = Depends(get_release_service)
):
    """
    Create a new release directly on the blockchain.
    Validates repository URL, pinned commit SHA, and published artifact SHA-256.
    """
    try:
        return await service.create_release(payload)
    except QuorumException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("", response_model=List[ReleaseResponse])
async def list_releases(
    service: ReleaseService = Depends(get_release_service)
):
    """Retrieve all releases directly from the blockchain state."""
    try:
        raw_releases = await service.list_releases()
        results = []
        for r in raw_releases:
            dec = r.get("decision", "NONE")
            rel_status = (
                "VERIFIED"
                if dec == "VERIFIED"
                else (
                    "REJECTED"
                    if dec == "REJECTED"
                    else ("DISPUTED" if dec == "DISPUTED" else "CREATED")
                )
            )
            results.append(
                ReleaseResponse(
                    release_id=str(r.get("release_id", "")),
                    repository_url=r.get("repository_url", ""),
                    repository=r.get("repository_url", ""),
                    commit_sha=r.get("commit_sha", ""),
                    commit=r.get("commit_sha", ""),
                    build_config_id=r.get("build_config_id", "python-package-v1"),
                    published_hash=r.get("published_hash", ""),
                    artifact_name=r.get("artifact_name", "sampleproject-3.0.0-py3-none-any.whl"),
                    builder_count=r.get("builder_count", 3),
                    quorum_required=r.get("quorum_required", 2),
                    status=rel_status,
                    created_at=r.get("created_at") or "2026-10-04T00:00:00Z",
                )
            )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{release_id}", response_model=ReleaseResponse)
async def get_release(
    release_id: str,
    service: ReleaseService = Depends(get_release_service)
):
    """Retrieve details of a specific release directly from the blockchain state."""
    try:
        return await service.get_release(release_id)
    except ReleaseNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{release_id}/verify", response_model=VerificationResponse)
async def verify_release(
    release_id: str,
    scenario: str = Query(default="NORMAL", description="Mock builder scenario: NORMAL, ONE_DISAGREE, STRICT_DISAGREE, WRONG_QUORUM, INVALID_SIGNATURE"),
    service: ReleaseService = Depends(get_release_service)
):
    """
    Execute full end-to-end database-free verification flow for a release:
    1. Loads release directly from blockchain
    2. Runs Person 2 Builder Manager (or mock with optional scenario)
    3. Verifies attestations (signatures, identity, repo, commit)
    4. Calculates local expected quorum
    5. Submits builder evidence & final decision to Person 1 Blockchain contract
    6. Returns authoritative decision directly from blockchain with decision_source=BLOCKCHAIN
    """
    try:
        release = await service.get_release(release_id)
        if scenario:
            mock_builder_manager.set_scenario(scenario, published_hash=release.published_hash, artifact_name=release.artifact_name)
        return await service.verify_release(release_id)
    except ReleaseNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except QuorumException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failure: {str(e)}")


@router.get("/{release_id}/result")
async def get_verification_result(
    release_id: str,
    service: ReleaseService = Depends(get_release_service)
):
    """Retrieve stored verification audit record directly from blockchain state."""
    try:
        audit = await service.get_verification_result(release_id)
        if not audit:
            raise HTTPException(status_code=404, detail=f"No finalized verification result found on-chain for release '{release_id}'. Run /verify first.")
        return audit
    except ReleaseNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{release_id}/attestations")
async def get_release_attestations(
    release_id: str,
    service: ReleaseService = Depends(get_release_service)
):
    """Retrieve stored attestations submitted for a release directly from blockchain."""
    try:
        await service.get_release(release_id)
        attestations = await service.get_attestations(release_id)
        return {"release_id": release_id, "count": len(attestations), "attestations": attestations}
    except ReleaseNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
