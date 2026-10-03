"""Calculate a streaming SHA-256 digest of a collected artifact's bytes."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from builders.manager.artifact import CollectedArtifact

HASH_ALGORITHM = "sha256"
HASH_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class HashedArtifact:
    collected: CollectedArtifact
    algorithm: str
    digest: str

    @property
    def path(self) -> Path:
        return self.collected.path

    @property
    def relative_path(self) -> str:
        return self.collected.relative_path

    @property
    def size_bytes(self) -> int:
        return self.collected.size_bytes

    def manifest(self) -> dict[str, object]:
        """Return the Step 5/6 output passed into the signed attestation."""
        return {
            "artifact": {
                "path": self.relative_path,
                "size_bytes": self.size_bytes,
            },
            "hash": {
                "algorithm": self.algorithm,
                "digest": self.digest,
            },
        }


def sha256_file(artifact: CollectedArtifact) -> HashedArtifact:
    """Hash file contents incrementally, never its name or path text."""
    digest = hashlib.sha256()
    with artifact.path.open("rb") as stream:
        while chunk := stream.read(HASH_CHUNK_BYTES):
            digest.update(chunk)
    return HashedArtifact(artifact, HASH_ALGORITHM, digest.hexdigest())
