from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class AttestationModel:
    id: Optional[str]
    release_id: str
    builder_id: str
    attestation_data: Dict[str, Any]
    created_at: str
