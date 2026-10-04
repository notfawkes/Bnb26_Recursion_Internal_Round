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
    image: str
    command: tuple[str, ...]
    artifact_glob: str
    limits: ResourceLimits


APPROVED_BUILD_CONFIGS: Mapping[str, BuildConfiguration] = MappingProxyType(
    {
        "python-package-v1": BuildConfiguration(
            image="quorum-python-package-v1:local",
            command=(
                "sh",
                "-c",
                "mkdir -p /tmp/work && cp -a /src/. /tmp/work/ && python -m build --wheel --no-isolation --outdir /out /tmp/work",
            ),
            artifact_glob="dist/*.whl",
            limits=ResourceLimits(
                timeout_seconds=300,
                cpu_count=1,
                memory_mb=512,
            ),
        ),
        "node-package-v1": BuildConfiguration(
            image="quorum-node-package-v1:local",
            command=(
                "sh",
                "-c",
                "mkdir -p /tmp/work /out && cp -a /src/. /tmp/work/ && cd /tmp/work && npm pack --ignore-scripts --pack-destination /out",
            ),
            artifact_glob="dist/*.tgz",
            limits=ResourceLimits(
                timeout_seconds=300,
                cpu_count=1,
                memory_mb=512,
            ),
        ),
        "java-maven-v1": BuildConfiguration(
            image="quorum-java-maven-v1:local",
            command=(
                "sh",
                "-c",
                "mkdir -p /tmp/work /tmp/m2 /out && cp -a /src/. /tmp/work/ && cp -a /opt/maven-cache/. /tmp/m2/ && cd /tmp/work && mvn -B -ntp -o -Dmaven.repo.local=/tmp/m2 -DskipTests package && find target -maxdepth 1 -type f -name '*.jar' ! -name '*-sources.jar' ! -name '*-javadoc.jar' ! -name 'original-*.jar' -exec cp {} /out/ \\;",
            ),
            artifact_glob="dist/*.jar",
            limits=ResourceLimits(
                timeout_seconds=420,
                cpu_count=1,
                memory_mb=768,
            ),
        ),
    }
)
