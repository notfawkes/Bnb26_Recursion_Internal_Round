import json
from dataclasses import asdict
from pathlib import Path

import pytest

from builders.manager.orchestrator import run_all_builders
from builders.manager.pipeline import BuilderOutcome
from builders.manager.request_validator import RequestValidationError

RELEASE_ID = "d4f2496e-5c5a-4c82-9fd5-f3c3012a524e"
JOB_ID = "0123456789abcdef0123456789abcdef"
BUILDERS = ("builder-a", "builder-b", "builder-c")


def _request() -> dict[str, object]:
    return {
        "release_id": RELEASE_ID,
        "repository_url": "https://github.com/example/safecalc",
        "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "build_config_id": "python-package-v1",
        "builders": list(BUILDERS),
    }


def _success(
    builder_id: str, output_root: Path, job_id: str, digest: str | None = None
) -> BuilderOutcome:
    artifact_hash = digest or (builder_id[-1] * 64)
    key_id = f"{builder_id}-key-v1"
    envelope = {
        "attestation": {
            "builder_id": builder_id,
            "public_key_id": key_id,
            "artifact": {"algorithm": "sha256", "digest": artifact_hash},
        },
        "public_key_id": key_id,
        "signature_algorithm": "ed25519",
        "canonicalization": "quorum-json-v1",
        "signature": f"signature-for-{builder_id}",
    }
    return BuilderOutcome(
        release_id=RELEASE_ID,
        builder_id=builder_id,
        status="SUCCESS",
        job_directory=str(output_root / RELEASE_ID / builder_id / job_id),
        artifact_hash=artifact_hash,
        artifact_path=str(output_root / builder_id / "dist" / "demo.whl"),
        artifact_manifest={
            "artifact": {"path": "dist/demo.whl", "size_bytes": 10},
            "hash": {"algorithm": "sha256", "digest": artifact_hash},
        },
        public_key_id=key_id,
        signed_attestation=envelope,
    )


def _failure(builder_id: str, output_root: Path, job_id: str) -> BuilderOutcome:
    return BuilderOutcome(
        release_id=RELEASE_ID,
        builder_id=builder_id,
        status="BUILD_FAILED",
        job_directory=str(output_root / RELEASE_ID / builder_id / job_id),
        error_code="BUILD_EXIT_2",
    )


def test_all_builders_receive_same_request_and_keep_identity(tmp_path: Path) -> None:
    calls: list[tuple[dict[str, object], str, Path, str]] = []

    def runner(
        payload: dict[str, object],
        builder_id: str,
        output_root: Path,
        private_key: Path,
        *,
        job_id: str,
    ) -> BuilderOutcome:
        calls.append((payload, builder_id, private_key, job_id))
        return _success(builder_id, output_root, job_id, "4" * 64)

    outcome = run_all_builders(
        _request(),
        tmp_path / "output",
        tmp_path / "keys",
        runner=runner,
        job_id=JOB_ID,
    )

    assert [call[1] for call in calls] == list(BUILDERS)
    assert all(call[0] == _request() for call in calls)
    assert all(call[3] == JOB_ID for call in calls)
    assert [call[2].name for call in calls] == [
        "builder-a-key-v1.pem",
        "builder-b-key-v1.pem",
        "builder-c-key-v1.pem",
    ]
    assert outcome.status == "COMPLETED"
    assert outcome.summary.total_builders == 3
    assert outcome.summary.successful_builds == 3
    assert outcome.summary.failed_builds == 0
    assert [result.builder_id for result in outcome.builder_results] == list(BUILDERS)
    assert all(result.signed_attestation for result in outcome.builder_results)

    saved = json.loads(Path(outcome.result_path).read_text(encoding="utf-8"))
    assert saved == json.loads(json.dumps(asdict(outcome)))


def test_one_failure_does_not_stop_remaining_builder(tmp_path: Path) -> None:
    called: list[str] = []

    def runner(
        payload: dict[str, object],
        builder_id: str,
        output_root: Path,
        private_key: Path,
        *,
        job_id: str,
    ) -> BuilderOutcome:
        called.append(builder_id)
        if builder_id == "builder-b":
            return _failure(builder_id, output_root, job_id)
        return _success(builder_id, output_root, job_id)

    outcome = run_all_builders(
        _request(), tmp_path / "output", tmp_path / "keys", runner=runner, job_id=JOB_ID
    )

    assert called == list(BUILDERS)
    assert outcome.summary.successful_builds == 2
    assert outcome.summary.failed_builds == 1
    failed = outcome.builder_results[1]
    assert failed.status == "BUILD_FAILED"
    assert failed.error_code == "BUILD_EXIT_2"
    assert failed.artifact_hash is None
    assert failed.signed_attestation is None


def test_unexpected_builder_exception_is_collected_and_execution_continues(
    tmp_path: Path,
) -> None:
    called: list[str] = []

    def runner(
        payload: dict[str, object],
        builder_id: str,
        output_root: Path,
        private_key: Path,
        *,
        job_id: str,
    ) -> BuilderOutcome:
        called.append(builder_id)
        if builder_id == "builder-b":
            raise RuntimeError("simulated runner crash")
        return _success(builder_id, output_root, job_id)

    outcome = run_all_builders(
        _request(), tmp_path / "output", tmp_path / "keys", runner=runner, job_id=JOB_ID
    )

    assert called == list(BUILDERS)
    assert outcome.builder_results[1].status == "INTERNAL_ERROR"
    assert outcome.builder_results[1].error_code == "UNHANDLED_BUILDER_ERROR"
    assert outcome.summary == type(outcome.summary)(3, 2, 1)


def test_all_failures_are_collected_as_completed_execution(tmp_path: Path) -> None:
    def runner(
        payload: dict[str, object],
        builder_id: str,
        output_root: Path,
        private_key: Path,
        *,
        job_id: str,
    ) -> BuilderOutcome:
        return _failure(builder_id, output_root, job_id)

    outcome = run_all_builders(
        _request(), tmp_path / "output", tmp_path / "keys", runner=runner, job_id=JOB_ID
    )

    assert outcome.status == "COMPLETED"
    assert outcome.summary.successful_builds == 0
    assert outcome.summary.failed_builds == 3
    assert all(result.status == "BUILD_FAILED" for result in outcome.builder_results)
    assert all(result.signed_attestation is None for result in outcome.builder_results)


def test_different_hashes_are_preserved_without_a_verdict(tmp_path: Path) -> None:
    hashes = {
        "builder-a": "a" * 64,
        "builder-b": "a" * 64,
        "builder-c": "c" * 64,
    }

    def runner(
        payload: dict[str, object],
        builder_id: str,
        output_root: Path,
        private_key: Path,
        *,
        job_id: str,
    ) -> BuilderOutcome:
        return _success(builder_id, output_root, job_id, hashes[builder_id])

    outcome = run_all_builders(
        _request(), tmp_path / "output", tmp_path / "keys", runner=runner, job_id=JOB_ID
    )

    assert [result.artifact_hash for result in outcome.builder_results] == [
        "a" * 64,
        "a" * 64,
        "c" * 64,
    ]
    serialized = asdict(outcome)
    assert "decision" not in serialized
    assert "verified" not in serialized
    assert "quorum" not in serialized


def test_invalid_request_or_job_id_is_rejected_before_execution(tmp_path: Path) -> None:
    called = False

    def runner(*args: object, **kwargs: object) -> BuilderOutcome:
        nonlocal called
        called = True
        raise AssertionError("runner should not be called")

    invalid_request = _request()
    del invalid_request["commit_sha"]
    with pytest.raises(RequestValidationError, match="missing fields"):
        run_all_builders(
            invalid_request, tmp_path / "output", tmp_path / "keys", runner=runner
        )
    with pytest.raises(RequestValidationError, match="job_id"):
        run_all_builders(
            _request(),
            tmp_path / "output",
            tmp_path / "keys",
            runner=runner,
            job_id="../unsafe",
        )
    assert called is False
