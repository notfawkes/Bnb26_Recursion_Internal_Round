"""Select exactly one approved build artifact and hash its bytes."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

MAX_ARTIFACT_BYTES = 100 * 1024 * 1024
HASH_CHUNK_BYTES = 1024 * 1024


class ArtifactError(RuntimeError):
    """The build did not produce exactly one acceptable artifact."""


@dataclass(frozen=True)
class HashedArtifact:
    path: Path
    relative_path: str
    size_bytes: int
    algorithm: str
    digest: str


def hash_artifact(path: Path) -> str:
    """Hash file contents incrementally, not the filename or path."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def collect_and_hash_artifact(
    job_dir: Path, artifact_glob: str, *, max_bytes: int = MAX_ARTIFACT_BYTES
) -> HashedArtifact:
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

    return HashedArtifact(
        path=path,
        relative_path=path.relative_to(job_dir).as_posix(),
        size_bytes=size_bytes,
        algorithm="sha256",
        digest=hash_artifact(path),
    )
