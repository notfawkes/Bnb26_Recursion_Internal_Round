"""Validate the five-field request before any repository or build work begins."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from uuid import UUID

from builders.manager.config import (
    APPROVED_BUILD_CONFIGS,
    BuildConfiguration,
    ResourceLimits,
)

REQUIRED_FIELDS = frozenset(
    {"release_id", "repository_url", "commit_sha", "build_config_id", "builders"}
)
BUILDER_IDS = frozenset({"builder-a", "builder-b", "builder-c"})
REPOSITORY_URL = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
COMMIT_SHA = re.compile(r"[0-9a-f]{40}")


class RequestValidationError(ValueError):
    """The builder cannot safely accept this request."""


@dataclass(frozen=True)
class ValidatedBuilderRequest:
    release_id: UUID
    repository_url: str
    commit_sha: str
    build_config_id: str
    builders: tuple[str, ...]
    build_config: BuildConfiguration


def _validated_configuration(config: object) -> BuildConfiguration:
    if not isinstance(config, BuildConfiguration):
        raise RequestValidationError("build configuration is not defined")

    artifact = config.artifact_glob
    if (
        not isinstance(artifact, str)
        or not artifact
        or artifact.startswith("/")
        or "\\" in artifact
        or ":" in artifact
        or ".." in PurePosixPath(artifact).parts
    ):
        raise RequestValidationError("build configuration has no safe artifact path")

    limits = config.limits
    if not isinstance(limits, ResourceLimits):
        raise RequestValidationError("build configuration has no resource limits")
    for name in ("timeout_seconds", "cpu_count", "memory_mb"):
        value = getattr(limits, name)
        if type(value) is not int or value <= 0:
            raise RequestValidationError(f"build configuration has invalid {name}")
    return config


def validate_builder_request(
    payload: Mapping[str, object],
    *,
    configs: Mapping[str, BuildConfiguration] = APPROVED_BUILD_CONFIGS,
) -> ValidatedBuilderRequest:
    """Return a typed request, or raise RequestValidationError.

    URL syntax checks are only the first boundary. The future fetch/build worker
    must also restrict network egress and avoid following unsafe redirects.
    """
    if not isinstance(payload, Mapping):
        raise RequestValidationError("request must be a JSON object")

    keys = set(payload)
    if not all(isinstance(key, str) for key in keys):
        raise RequestValidationError("request keys must be strings")
    missing = REQUIRED_FIELDS - keys
    unexpected = keys - REQUIRED_FIELDS
    if missing:
        raise RequestValidationError(f"missing fields: {', '.join(sorted(missing))}")
    if unexpected:
        raise RequestValidationError(
            f"unexpected fields: {', '.join(sorted(unexpected))}"
        )

    release_id = payload["release_id"]
    if not isinstance(release_id, str):
        raise RequestValidationError("release_id must be a UUID string")
    try:
        parsed_release_id = UUID(release_id)
    except ValueError as exc:
        raise RequestValidationError("release_id must be a UUID string") from exc
    if str(parsed_release_id) != release_id:
        raise RequestValidationError(
            "release_id must use canonical lowercase UUID format"
        )

    repository_url = payload["repository_url"]
    if not isinstance(repository_url, str) or len(repository_url) > 2048:
        raise RequestValidationError("repository_url must be an HTTPS GitHub URL")
    match = REPOSITORY_URL.fullmatch(repository_url)
    if match is None or any(part in {".", ".."} for part in match.groups()):
        raise RequestValidationError("repository_url must be an HTTPS GitHub URL")

    commit_sha = payload["commit_sha"]
    if not isinstance(commit_sha, str) or COMMIT_SHA.fullmatch(commit_sha) is None:
        raise RequestValidationError(
            "commit_sha must be 40 lowercase hexadecimal characters"
        )

    build_config_id = payload["build_config_id"]
    if not isinstance(build_config_id, str) or build_config_id not in configs:
        raise RequestValidationError("build_config_id is not approved")
    build_config = _validated_configuration(configs[build_config_id])

    builders = payload["builders"]
    if (
        not isinstance(builders, list)
        or len(builders) != 3
        or not all(isinstance(builder, str) for builder in builders)
        or set(builders) != BUILDER_IDS
    ):
        raise RequestValidationError(
            "builders must contain builder-a, builder-b and builder-c once each"
        )

    return ValidatedBuilderRequest(
        release_id=parsed_release_id,
        repository_url=repository_url,
        commit_sha=commit_sha,
        build_config_id=build_config_id,
        builders=tuple(builders),
        build_config=build_config,
    )
