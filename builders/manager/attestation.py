"""Describe what one builder actually produced; do not decide quorum trust."""

from builders.manager.artifact import HashedArtifact
from builders.manager.request_validator import ValidatedBuilderRequest

SCHEMA_VERSION = "1.0"


def make_attestation(
    request: ValidatedBuilderRequest,
    builder_id: str,
    artifact: HashedArtifact,
    image_id: str,
    source_date_epoch: int,
) -> dict[str, object]:
    if builder_id not in request.builders:
        raise ValueError("builder_id is not part of this request")

    return {
        "schema_version": SCHEMA_VERSION,
        "release_id": str(request.release_id),
        "builder_id": builder_id,
        "public_key_id": f"{builder_id}-key-v1",
        "source": {
            "repository_url": request.repository_url,
            "commit_sha": request.commit_sha,
        },
        "build": {
            "config_id": request.build_config_id,
            "image_id": image_id,
            "source_date_epoch": source_date_epoch,
            "status": "SUCCESS",
        },
        "artifact": {
            "path": artifact.relative_path,
            "algorithm": artifact.algorithm,
            "digest": artifact.digest,
            "size_bytes": artifact.size_bytes,
        },
    }
