"""Builder-owned configuration referenced by an incoming build request."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class ResourceLimits:
    timeout_seconds: int
    cpu_count: int
    memory_mb: int


@dataclass(frozen=True)
class BuildConfiguration:
    artifact_glob: str
    limits: ResourceLimits


APPROVED_BUILD_CONFIGS: Mapping[str, BuildConfiguration] = MappingProxyType(
    {
        "python-package-v1": BuildConfiguration(
            artifact_glob="dist/*.whl",
            limits=ResourceLimits(
                timeout_seconds=300,
                cpu_count=1,
                memory_mb=512,
            ),
        )
    }
)
