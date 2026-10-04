"""Run one validated builder and return evidence, never a quorum decision."""

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from builders.manager.artifact import ArtifactError, collect_artifact
from builders.manager.attestation import make_attestation
from builders.manager.executor import (
    BuildExecutionError,
    ExecutionResult,
    execute_build,
)
from builders.manager.hashing import sha256_file
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
JOB_ID_PATTERN = re.compile(r"[0-9a-f]{32}")


@dataclass(frozen=True)
class BuilderOutcome:
    release_id: str
    builder_id: str
    status: str
    job_directory: str
    artifact_hash: str | None = None
    artifact_path: str | None = None
    artifact_manifest: dict[str, object] | None = None
    public_key_id: str | None = None
    signed_attestation: dict[str, object] | None = None
    error_code: str | None = None
    logs: tuple[dict[str, str], ...] = ()


def _audit_log(stage: str, message: str, level: str = "INFO") -> dict[str, str]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "level": level,
        "message": message,
    }


def run_single_builder(
    payload: Mapping[str, object],
    builder_id: str,
    output_root: Path,
    private_key_path: Path,
    *,
    fetcher: FetchFunction = fetch_repository,
    executor: ExecuteFunction = execute_build,
    job_id: str | None = None,
) -> BuilderOutcome:
    """Fetch, build, hash and sign one builder's result.

    `fetcher` and `executor` are injectable only to test the pipeline without
    a network or Docker daemon. Production callers use the defaults.
    """
    request = validate_builder_request(payload)
    if builder_id not in request.builders:
        raise RequestValidationError("builder_id is not part of this request")

    effective_job_id = job_id or uuid4().hex
    if JOB_ID_PATTERN.fullmatch(effective_job_id) is None:
        raise RequestValidationError(
            "job_id must be 32 lowercase hexadecimal characters"
        )
    job_dir = (
        output_root.resolve() / str(request.release_id) / builder_id / effective_job_id
    )
    job_dir.mkdir(parents=True, exist_ok=False)
    outcome_fields = {
        "release_id": str(request.release_id),
        "builder_id": builder_id,
        "job_directory": str(job_dir),
    }
    logs: list[dict[str, str]] = [
        _audit_log(
            "REQUEST",
            f"Received {request.build_config_id} build request for {request.repository_url}@{request.commit_sha}.",
        )
    ]

    try:
        fetched = fetcher(request, job_dir / "source")
    except RepositoryFetchError as exc:
        (job_dir / "fetch.log").write_text(str(exc), encoding="utf-8")
        logs.append(_audit_log("SOURCE", f"Pinned source fetch failed: {exc}", "ERROR"))
        return BuilderOutcome(
            status="FETCH_FAILED", error_code="GIT_ERROR", logs=tuple(logs), **outcome_fields
        )
    (job_dir / "fetch.log").write_text(fetched.log, encoding="utf-8")
    logs.append(
        _audit_log(
            "SOURCE",
            f"Fetched and checked out exact commit {fetched.commit_sha}; SOURCE_DATE_EPOCH={fetched.source_date_epoch}.",
        )
    )
    if fetched.log.strip():
        logs.append(_audit_log("SOURCE", f"Git transcript:\n{fetched.log[-8000:]}"))

    approved_command = " ".join(request.build_config.command)
    logs.append(
        _audit_log(
            "CONTAINER",
            f"Launching image {request.build_config.image} with network=none, read-only root, dropped capabilities, and command:\n{approved_command}",
        )
    )

    try:
        execution = executor(
            fetched.directory,
            job_dir / "dist",
            request.build_config,
            source_date_epoch=fetched.source_date_epoch,
        )
    except BuildExecutionError as exc:
        (job_dir / "build.log").write_text(str(exc), encoding="utf-8")
        logs.append(_audit_log("CONTAINER", f"Docker execution failed: {exc}", "ERROR"))
        return BuilderOutcome(
            status="BUILD_FAILED", error_code="DOCKER_ERROR", logs=tuple(logs), **outcome_fields
        )
    (job_dir / "build.log").write_text(execution.log, encoding="utf-8")
    container_identity = execution.container_name or execution.container_id[:12] or "ephemeral-container"
    logs.append(
        _audit_log(
            "CONTAINER",
            f"Container {container_identity} exited with status {execution.status} and code {execution.exit_code}; image={execution.image_id}.",
        )
    )
    if execution.log.strip():
        logs.append(_audit_log("BUILD", f"Container output:\n{execution.log[-12000:]}"))
    logs.append(
        _audit_log(
            "CLEANUP",
            f"Container {container_identity} was force-removed after evidence collection.",
        )
    )
    if execution.status != "SUCCESS":
        logs.append(_audit_log("BUILD", "Approved build command did not complete successfully.", "ERROR"))
        return BuilderOutcome(
            status=execution.status,
            error_code=(
                "BUILD_TIMEOUT"
                if execution.status == "BUILD_TIMEOUT"
                else f"BUILD_EXIT_{execution.exit_code}"
            ),
            logs=tuple(logs),
            **outcome_fields,
        )

    try:
        collected_artifact = collect_artifact(
            job_dir, request.build_config.artifact_glob
        )
    except ArtifactError as exc:
        logs.append(_audit_log("ARTIFACT", f"Artifact collection failed: {exc}", "ERROR"))
        return BuilderOutcome(
            status="ARTIFACT_ERROR",
            error_code="MISSING_OR_AMBIGUOUS_ARTIFACT",
            logs=tuple(logs),
            **outcome_fields,
        )
    logs.append(
        _audit_log(
            "ARTIFACT",
            f"Selected {collected_artifact.relative_path} ({collected_artifact.size_bytes} bytes) using {request.build_config.artifact_glob}.",
        )
    )
    artifact = sha256_file(collected_artifact)
    logs.append(_audit_log("HASH", f"SHA-256 digest generated: {artifact.digest}."))
    manifest = artifact.manifest()
    (job_dir / "artifact-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
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
        logs.append(_audit_log("ATTESTATION", "Ed25519 attestation signing failed.", "ERROR"))
        return BuilderOutcome(
            status="SIGNING_FAILED", error_code="KEY_ERROR", logs=tuple(logs), **outcome_fields
        )

    (job_dir / "signed-attestation.json").write_text(
        json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    logs.append(
        _audit_log(
            "ATTESTATION",
            f"Signed evidence with {builder_id}-key-v1; builder result is ready for backend verification.",
        )
    )
    return BuilderOutcome(
        status="SUCCESS",
        artifact_hash=artifact.digest,
        artifact_path=str(artifact.path),
        artifact_manifest=manifest,
        public_key_id=f"{builder_id}-key-v1",
        signed_attestation=envelope,
        logs=tuple(logs),
        **outcome_fields,
    )
