import hashlib
import os
import re
from typing import Optional
from app.core.exceptions import QuorumException

HEX_64_REGEX = re.compile(r"^[0-9a-fA-F]{64}$")


class PublishedArtifactService:
    """
    Service for calculating and handling published artifact SHA-256 hashes.
    Keeps artifact SHA-256 strictly separate from Git commit SHA.
    """

    @staticmethod
    def calculate_sha256(file_path: str) -> str:
        """Calculate SHA-256 hash of a file on disk."""
        if not os.path.exists(file_path):
            raise QuorumException(f"Artifact file not found at path: {file_path}", status_code=400)

        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest().lower()

    @staticmethod
    def calculate_bytes_sha256(content: bytes | str) -> str:
        """Calculate SHA-256 hash from in-memory string or bytes."""
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content
        return hashlib.sha256(content_bytes).hexdigest().lower()

    @classmethod
    def resolve_published_hash(
        cls,
        published_hash: Optional[str] = None,
        published_artifact: Optional[str] = None
    ) -> str:
        """
        Resolves the final 64-character SHA-256 published artifact hash.
        Either accepts a hex string directly or computes it from a file path / string content.
        """
        if published_hash and published_hash.strip():
            clean_hash = published_hash.strip().lower()
            if not HEX_64_REGEX.match(clean_hash):
                raise QuorumException(
                    f"Published hash '{published_hash}' is invalid. Must be a 64-character SHA-256 hex string.",
                    status_code=400
                )
            return clean_hash

        if published_artifact and published_artifact.strip():
            art_str = published_artifact.strip()
            # If artifact path exists as a local file, calculate hash of file
            if os.path.isfile(art_str):
                return cls.calculate_sha256(art_str)
            # If artifact string itself is a 64-char hex string
            if HEX_64_REGEX.match(art_str.lower()):
                return art_str.lower()
            # Otherwise compute SHA-256 of the artifact content/string
            return cls.calculate_bytes_sha256(art_str)

        raise QuorumException(
            "Either 'published_hash' (64-hex SHA-256) or 'published_artifact' must be provided.",
            status_code=400
        )
