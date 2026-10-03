from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class VerificationRecordModel:
    verification_id: str
    release_id: str
    repository: str
    commit: str
    published_hash: str
    builder_results: Dict[str, Any]
    quorum_policy: Dict[str, Any]
    quorum_hash: Optional[str]
    decision: str
    reason: str
    transaction_hash: Optional[str]
    timestamp: str
