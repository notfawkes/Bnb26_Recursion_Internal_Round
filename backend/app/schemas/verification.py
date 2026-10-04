from typing import List, Optional, Any
from pydantic import BaseModel, Field, model_validator
from app.core.enums import Decision, BuilderStatus
from app.schemas.attestation import BuilderLogEntry


class BuilderVerificationResult(BaseModel):
    builder_id: str
    status: str = Field(default="SUCCESS", description="Build execution status (SUCCESS / FAILURE)")
    artifact_name: str = Field(default="safecalc.tar.gz", description="Artifact filename")
    artifact_sha256: str = Field(default="", description="Artifact SHA-256 hash")
    signature_valid: bool
    identity_valid: bool
    source_match: bool
    commit_match: bool
    valid: bool
    status_detail: BuilderStatus = Field(default=BuilderStatus.AGREE, description="AGREE, DISAGREE, or INVALID")
    logs: List[BuilderLogEntry] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def populate_compat_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "artifact_hash" in data and not data.get("artifact_sha256"):
                data["artifact_sha256"] = data["artifact_hash"]
            if "status" in data and isinstance(data["status"], BuilderStatus):
                data["status_detail"] = data["status"]
                data["status"] = "SUCCESS"
            if "status_detail" not in data and "status" not in data:
                data["status_detail"] = BuilderStatus.AGREE
        return data

    @property
    def artifact_hash(self) -> str:
        return self.artifact_sha256


class LocalQuorumResult(BaseModel):
    achieved: bool
    agreement: str = Field(description="e.g. '2/3'")
    quorum_hash: Optional[str] = Field(default=None, description="Winning quorum artifact hash")
    expected_decision: Decision = Field(default=Decision.VERIFIED, description="Expected local decision")


# Alias for backward compatibility
QuorumResult = LocalQuorumResult


class BlockchainRecord(BaseModel):
    release_id: Optional[Any] = None
    published_hash: Optional[str] = None
    quorum_hash: Optional[str] = None
    decision: Optional[str] = None
    is_finalized: bool = False
    create_release_tx: Optional[str] = None
    attestation_txs: List[str] = Field(default_factory=list)
    finalize_tx: Optional[str] = None


class VerificationResponse(BaseModel):
    release_id: str
    repository_url: str
    commit_sha: str
    build_config_id: str = "python-package-v1"
    published_hash: str
    builders: List[BuilderVerificationResult]
    local_quorum: LocalQuorumResult
    blockchain: BlockchainRecord
    decision: Decision
    decision_source: str = Field(default="BLOCKCHAIN", description="Source of final decision: BLOCKCHAIN or LOCAL")
    blockchain_consistent: bool = Field(default=True, description="True if local expected decision matches blockchain decision")
    cache_hit: bool = Field(
        default=False,
        description="True when a finalized audit result was returned without rerunning builders",
    )
