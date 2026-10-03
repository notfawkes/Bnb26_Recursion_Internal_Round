import json
from hashlib import sha256
from pathlib import Path

from builders.manager.executor import ExecutionResult
from builders.manager.pipeline import run_single_builder
from builders.manager.repository import FetchedSource
from builders.manager.signing import (
    generate_development_keypair,
    verify_attestation_signature,
)


def _request() -> dict[str, object]:
    return {
        "release_id": "d4f2496e-5c5a-4c82-9fd5-f3c3012a524e",
        "repository_url": "https://github.com/example/safecalc",
        "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "build_config_id": "python-package-v1",
        "builders": ["builder-a", "builder-b", "builder-c"],
    }


def _fake_fetch(request: object, destination: Path) -> FetchedSource:
    destination.mkdir()
    (destination / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
    return FetchedSource(destination, _request()["commit_sha"], 1700000000, "fetched")


def _fake_build(
    source: Path, output: Path, config: object, *, source_date_epoch: int
) -> ExecutionResult:
    assert source_date_epoch == 1700000000
    output.mkdir()
    (output / "demo-1.0-py3-none-any.whl").write_bytes(b"deterministic wheel")
    return ExecutionResult("SUCCESS", 0, "built", "sha256:demo-image")


def test_single_builder_produces_verifiable_signed_evidence(tmp_path: Path) -> None:
    keys = generate_development_keypair("builder-a", tmp_path / "keys")
    outcome = run_single_builder(
        _request(),
        "builder-a",
        tmp_path / "output",
        keys.private_path,
        fetcher=_fake_fetch,
        executor=_fake_build,
    )

    assert outcome.status == "SUCCESS"
    assert outcome.artifact_hash == sha256(b"deterministic wheel").hexdigest()
    assert outcome.signed_attestation is not None
    assert verify_attestation_signature(
        outcome.signed_attestation, keys.public_path.read_bytes()
    )
    assert outcome.signed_attestation["attestation"]["build"]["status"] == "SUCCESS"
    assert (
        outcome.signed_attestation["attestation"]["build"]["image_id"]
        == "sha256:demo-image"
    )
    job_dir = Path(outcome.job_directory)
    assert (job_dir / "fetch.log").read_text(encoding="utf-8") == "fetched"
    assert (job_dir / "build.log").read_text(encoding="utf-8") == "built"
    saved = json.loads(
        (job_dir / "signed-attestation.json").read_text(encoding="utf-8")
    )
    assert saved == outcome.signed_attestation


def test_failed_build_has_no_success_attestation(tmp_path: Path) -> None:
    keys = generate_development_keypair("builder-a", tmp_path / "keys")

    def fail_build(
        source: Path, output: Path, config: object, *, source_date_epoch: int
    ) -> ExecutionResult:
        output.mkdir()
        return ExecutionResult("BUILD_FAILED", 2, "build backend failed", "sha256:demo")

    outcome = run_single_builder(
        _request(),
        "builder-a",
        tmp_path / "output",
        keys.private_path,
        fetcher=_fake_fetch,
        executor=fail_build,
    )

    assert outcome.status == "BUILD_FAILED"
    assert outcome.error_code == "BUILD_EXIT_2"
    assert outcome.signed_attestation is None
    assert not (Path(outcome.job_directory) / "signed-attestation.json").exists()


def test_missing_key_returns_signing_failure(tmp_path: Path) -> None:
    outcome = run_single_builder(
        _request(),
        "builder-a",
        tmp_path / "output",
        tmp_path / "missing.pem",
        fetcher=_fake_fetch,
        executor=_fake_build,
    )

    assert outcome.status == "SIGNING_FAILED"
    assert outcome.signed_attestation is None
