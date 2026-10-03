"""Run one validated builder and return evidence, never a quorum decision."""

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from builders.manager.artifact import ArtifactError, collect_and_hash_artifact
from builders.manager.attestation import make_attestation
from builders.manager.executor import (
    BuildExecutionError,
    ExecutionResult,
    execute_build,
)
from builders.manager.repository import (
    FetchedSource,
    RepositoryFetchError,
    fetch_repository,
)
from builders.manager.request_validator import (
    RequestValidationError,
    ValidatedBuilderRequest,
    validate_builder_request,
)
from builders.manager.signing import sign_attestation

FetchFunction = Callable[[ValidatedBuilderRequest, Path], FetchedSource]
ExecuteFunction = Callable[..., ExecutionResult]


@dataclass(frozen=True)
class BuilderOutcome:
    release_id: str
    builder_id: str
    status: str
    job_directory: str
    artifact_hash: str | None = None
    artifact_path: str | None = None
    signed_attestation: dict[str, object] | None = None
    error_code: str | None = None


def run_single_builder(
    payload: Mapping[str, object],
    builder_id: str,
    output_root: Path,
    private_key_path: Path,
    *,
    fetcher: FetchFunction = fetch_repository,
    executor: ExecuteFunction = execute_build,
) -> BuilderOutcome:
    """Fetch, build, hash and sign one builder's result.

    `fetcher` and `executor` are injectable only to test the pipeline without
    a network or Docker daemon. Production callers use the defaults.
    """
    request = validate_builder_request(payload)
    if builder_id not in request.builders:
        raise RequestValidationError("builder_id is not part of this request")

    job_dir = output_root.resolve() / str(request.release_id) / builder_id / uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=False)
    outcome_fields = {
        "release_id": str(request.release_id),
        "builder_id": builder_id,
        "job_directory": str(job_dir),
    }

    try:
        fetched = fetcher(request, job_dir / "source")
    except RepositoryFetchError as exc:
        (job_dir / "fetch.log").write_text(str(exc), encoding="utf-8")
        return BuilderOutcome(
            status="FETCH_FAILED", error_code="GIT_ERROR", **outcome_fields
        )
    (job_dir / "fetch.log").write_text(fetched.log, encoding="utf-8")

    try:
        execution = executor(
            fetched.directory,
            job_dir / "dist",
            request.build_config,
            source_date_epoch=fetched.source_date_epoch,
        )
    except BuildExecutionError as exc:
        (job_dir / "build.log").write_text(str(exc), encoding="utf-8")
        return BuilderOutcome(
            status="BUILD_FAILED", error_code="DOCKER_ERROR", **outcome_fields
        )
    (job_dir / "build.log").write_text(execution.log, encoding="utf-8")
    if execution.status != "SUCCESS":
        return BuilderOutcome(
            status=execution.status,
            error_code=(
                "BUILD_TIMEOUT"
                if execution.status == "BUILD_TIMEOUT"
                else f"BUILD_EXIT_{execution.exit_code}"
            ),
            **outcome_fields,
        )

    try:
        artifact = collect_and_hash_artifact(
            job_dir, request.build_config.artifact_glob
        )
    except ArtifactError:
        return BuilderOutcome(
            status="ARTIFACT_ERROR",
            error_code="MISSING_OR_AMBIGUOUS_ARTIFACT",
            **outcome_fields,
        )

    attestation = make_attestation(
        request,
        builder_id,
        artifact,
        execution.image_id,
        fetched.source_date_epoch,
    )
    try:
        envelope = sign_attestation(attestation, private_key_path)
    except (OSError, TypeError, ValueError):
        return BuilderOutcome(
            status="SIGNING_FAILED", error_code="KEY_ERROR", **outcome_fields
        )

    (job_dir / "signed-attestation.json").write_text(
        json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return BuilderOutcome(
        status="SUCCESS",
        artifact_hash=artifact.digest,
        artifact_path=str(artifact.path),
        signed_attestation=envelope,
        **outcome_fields,
    )
