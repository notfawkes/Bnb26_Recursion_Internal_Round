"""Execute every requested builder and collect evidence without judging it."""

import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

from builders.manager.pipeline import JOB_ID_PATTERN, BuilderOutcome, run_single_builder
from builders.manager.request_validator import (
    BUILDER_ORDER,
    RequestValidationError,
    ValidatedBuilderRequest,
    validate_builder_request,
)

BuilderRunner = Callable[..., BuilderOutcome]


@dataclass(frozen=True)
class BuildSummary:
    total_builders: int
    successful_builds: int
    failed_builds: int


@dataclass(frozen=True)
class MultiBuilderOutcome:
    release_id: str
    job_id: str
    status: str
    request: dict[str, object]
    summary: BuildSummary
    builder_results: tuple[BuilderOutcome, ...]
    result_path: str


def _request_payload(request: ValidatedBuilderRequest) -> dict[str, object]:
    return {
        "release_id": str(request.release_id),
        "repository_url": request.repository_url,
        "commit_sha": request.commit_sha,
        "build_config_id": request.build_config_id,
        "builders": list(request.builders),
    }


def _unexpected_failure(
    request: ValidatedBuilderRequest,
    builder_id: str,
    output_root: Path,
    job_id: str,
) -> BuilderOutcome:
    job_directory = (
        output_root.resolve() / str(request.release_id) / builder_id / job_id
    )
    return BuilderOutcome(
        release_id=str(request.release_id),
        builder_id=builder_id,
        status="INTERNAL_ERROR",
        job_directory=str(job_directory),
        error_code="UNHANDLED_BUILDER_ERROR",
    )


def run_all_builders(
    payload: Mapping[str, object],
    output_root: Path,
    key_directory: Path,
    *,
    runner: BuilderRunner = run_single_builder,
    job_id: str | None = None,
) -> MultiBuilderOutcome:
    """Run all requested builders sequentially and collect their evidence.

    `COMPLETED` means every requested builder reached a terminal outcome. It is
    not a verification, acceptance, rejection or quorum decision.
    """
    request = validate_builder_request(payload)
    request_payload = _request_payload(request)
    effective_job_id = job_id or uuid4().hex
    if JOB_ID_PATTERN.fullmatch(effective_job_id) is None:
        raise RequestValidationError(
            "job_id must be 32 lowercase hexadecimal characters"
        )
    builder_results: list[BuilderOutcome] = []

    for builder_id in BUILDER_ORDER:
        private_key = key_directory / f"{builder_id}-key-v1.pem"
        try:
            result = runner(
                _request_payload(request),
                builder_id,
                output_root,
                private_key,
                job_id=effective_job_id,
            )
        except Exception:  # noqa: BLE001 - one crashed builder must not stop the others
            result = _unexpected_failure(
                request, builder_id, output_root, effective_job_id
            )
        builder_results.append(result)

    successful_builds = sum(result.status == "SUCCESS" for result in builder_results)
    summary = BuildSummary(
        total_builders=len(builder_results),
        successful_builds=successful_builds,
        failed_builds=len(builder_results) - successful_builds,
    )
    result_directory = (
        output_root.resolve()
        / str(request.release_id)
        / "orchestrations"
        / effective_job_id
    )
    result_directory.mkdir(parents=True, exist_ok=False)
    result_path = result_directory / "combined-result.json"
    outcome = MultiBuilderOutcome(
        release_id=str(request.release_id),
        job_id=effective_job_id,
        status="COMPLETED",
        request=request_payload,
        summary=summary,
        builder_results=tuple(builder_results),
        result_path=str(result_path),
    )
    result_path.write_text(
        json.dumps(asdict(outcome), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return outcome
