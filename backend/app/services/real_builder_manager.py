import os
from pathlib import Path
from typing import List, Dict, Any
from app.interfaces.builder_manager import BuilderManager
from app.schemas.attestation import BuildRequest, BuilderManagerResponse, BuilderResult
from builders.manager.orchestrator import run_all_builders
from app.services.verification_service import to_uuid_str


class RealBuilderManager:
    """
    Adapter executing Person 2's real Builder Manager:
    - Pins Git commit
    - Runs Docker builds with container isolation
    - Computes SHA-256 artifact hashes
    - Generates and signs Ed25519 attestations
    - Returns MultiBuilderOutcome adapted to BuilderManagerResponse
    """

    def __init__(
        self,
        output_root: Path = Path("builders/output"),
        key_directory: Path = Path("builders/keys")
    ):
        self.output_root = output_root
        self.key_directory = key_directory

    async def run_builders(self, build_request: BuildRequest) -> BuilderManagerResponse:
        canonical_release_id = to_uuid_str(build_request.release_id)

        # 5-field contract strictly following shared/specs/builder-request.md
        payload = {
            "release_id": canonical_release_id,
            "repository_url": build_request.repository_url,
            "commit_sha": build_request.commit_sha,
            "build_config_id": build_request.build_config_id,
            "builders": ["builder-a", "builder-b", "builder-c"]
        }

        # Run Person 2's multi-builder orchestrator
        outcome = run_all_builders(
            payload=payload,
            output_root=self.output_root,
            key_directory=self.key_directory
        )

        results: List[BuilderResult] = []
        for res in outcome.builder_results:
            art_name = Path(res.artifact_path).name if res.artifact_path else "safecalc.whl"
            results.append(
                BuilderResult(
                    builder_id=res.builder_id,
                    status=res.status,
                    artifact_name=art_name,
                    artifact_sha256=res.artifact_hash or "",
                    signed_attestation=res.signed_attestation,
                    error_code=res.error_code,
                    logs=list(res.logs),
                )
            )

        return BuilderManagerResponse(
            release_id=str(build_request.release_id),
            results=results
        )
