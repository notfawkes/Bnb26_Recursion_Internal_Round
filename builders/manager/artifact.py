"""Select exactly one approved build artifact from a completed job."""

from dataclasses import dataclass
from pathlib import Path

MAX_ARTIFACT_BYTES = 100 * 1024 * 1024


class ArtifactError(RuntimeError):
    """The build did not produce exactly one acceptable artifact."""


@dataclass(frozen=True)
class CollectedArtifact:
    path: Path
    relative_path: str
    size_bytes: int


def collect_artifact(
    job_dir: Path, artifact_glob: str, *, max_bytes: int = MAX_ARTIFACT_BYTES
) -> CollectedArtifact:
    """Return the one regular file selected by the approved configuration."""
    matches = list(job_dir.glob(artifact_glob))
    if len(matches) != 1:
        raise ArtifactError(f"expected one artifact; found {len(matches)}")

    path = matches[0]
    resolved_job_dir = job_dir.resolve()
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(resolved_job_dir)
    ):
        raise ArtifactError("artifact must be a regular file inside the job directory")

    size_bytes = path.stat().st_size
    if size_bytes <= 0 or size_bytes > max_bytes:
        raise ArtifactError("artifact size is outside the allowed range")

    return CollectedArtifact(
        path=path,
        relative_path=path.relative_to(job_dir).as_posix(),
        size_bytes=size_bytes,
    )
