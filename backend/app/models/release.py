from dataclasses import dataclass
from typing import Optional
from app.core.enums import ReleaseStatus


@dataclass
class ReleaseModel:
    release_id: str
    repository: str
    commit: str
    published_hash: str
    artifact_name: str
    builder_count: int
    quorum_required: int
    status: ReleaseStatus
    created_at: str
