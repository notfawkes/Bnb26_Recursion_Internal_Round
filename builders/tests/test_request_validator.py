import json
from pathlib import Path

import pytest

from builders.manager.config import BuildConfiguration, ResourceLimits
from builders.manager.request_validator import (
    RequestValidationError,
    validate_builder_request,
)

EXAMPLE_PATH = (
    Path(__file__).resolve().parents[2]
    / "shared"
    / "specs"
    / "builder-request.example.json"
)


@pytest.fixture
def request_payload() -> dict[str, object]:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_shared_example_is_accepted(request_payload: dict[str, object]) -> None:
    result = validate_builder_request(request_payload)

    assert str(result.release_id) == request_payload["release_id"]
    assert result.builders == ("builder-a", "builder-b", "builder-c")
    assert result.build_config.artifact_glob == "dist/*.whl"
    assert result.build_config.limits.timeout_seconds == 300


@pytest.mark.parametrize(
    "missing_field",
    ["release_id", "repository_url", "commit_sha", "build_config_id", "builders"],
)
def test_missing_field_is_rejected(
    request_payload: dict[str, object], missing_field: str
) -> None:
    del request_payload[missing_field]
    with pytest.raises(RequestValidationError, match="missing fields"):
        validate_builder_request(request_payload)


def test_extra_field_is_rejected(request_payload: dict[str, object]) -> None:
    request_payload["artifact_path"] = "other/"
    with pytest.raises(RequestValidationError, match="unexpected fields"):
        validate_builder_request(request_payload)


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/example/safecalc",
        "https://127.0.0.1/example/safecalc",
        "https://github.com.evil.test/example/safecalc",
        "https://github.com@127.0.0.1/example/safecalc",
        "https://github.com:443/example/safecalc",
        "https://github.com/example/safecalc?next=internal",
        "https://github.com/example/..",
        "git@github.com:example/safecalc.git",
    ],
)
def test_unsafe_repository_url_is_rejected(
    request_payload: dict[str, object], url: str
) -> None:
    request_payload["repository_url"] = url
    with pytest.raises(RequestValidationError, match="repository_url"):
        validate_builder_request(request_payload)


@pytest.mark.parametrize("sha", ["a1b2c3", "A" * 40, "z" * 40])
def test_invalid_commit_is_rejected(
    request_payload: dict[str, object], sha: str
) -> None:
    request_payload["commit_sha"] = sha
    with pytest.raises(RequestValidationError, match="commit_sha"):
        validate_builder_request(request_payload)


def test_invalid_release_id_is_rejected(request_payload: dict[str, object]) -> None:
    request_payload["release_id"] = "release-001"
    with pytest.raises(RequestValidationError, match="release_id"):
        validate_builder_request(request_payload)


def test_unapproved_config_is_rejected(request_payload: dict[str, object]) -> None:
    request_payload["build_config_id"] = "run-anything"
    with pytest.raises(RequestValidationError, match="build_config_id"):
        validate_builder_request(request_payload)


@pytest.mark.parametrize(
    "builders",
    [
        ["builder-a"],
        ["builder-a", "builder-a", "builder-c"],
        ["builder-a", "builder-b", "unknown"],
    ],
)
def test_invalid_builders_are_rejected(
    request_payload: dict[str, object], builders: list[str]
) -> None:
    request_payload["builders"] = builders
    with pytest.raises(RequestValidationError, match="builders"):
        validate_builder_request(request_payload)


def test_config_without_valid_limits_is_rejected(
    request_payload: dict[str, object],
) -> None:
    invalid_configs = {
        "python-package-v1": BuildConfiguration(
            image="quorum-python-package-v1:local",
            command=("python", "-m", "build"),
            artifact_glob="dist/*.whl",
            limits=ResourceLimits(timeout_seconds=0, cpu_count=1, memory_mb=512),
        )
    }
    with pytest.raises(RequestValidationError, match="timeout_seconds"):
        validate_builder_request(request_payload, configs=invalid_configs)


def test_non_object_request_is_rejected() -> None:
    with pytest.raises(RequestValidationError, match="JSON object"):
        validate_builder_request([])  # type: ignore[arg-type]
