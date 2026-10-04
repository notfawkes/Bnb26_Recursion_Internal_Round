from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.builder import BuilderInfo, BuildInfo, ResultInfo


class SourceInfo(BaseModel):
    repository: str = Field(..., description="Git repository URL")
    commit: str = Field(..., description="Pinned git commit SHA")


class ArtifactInfo(BaseModel):
    name: str = Field(..., description="Artifact filename")
    sha256: str = Field(..., description="Artifact SHA-256 hash (64 hex characters)")


class Attestation(BaseModel):
    builder: BuilderInfo
    source: SourceInfo
    artifact: ArtifactInfo
    build: BuildInfo
    result: ResultInfo
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp")
    signature: str = Field(..., description="Ed25519 signature over canonical JSON payload")


class BuildRequest(BaseModel):
    release_id: str
    repository_url: str
    commit_sha: str
    build_config_id: str = "python-package-v1"
    builders: List[str] = Field(default_factory=lambda: ["builder-a", "builder-b", "builder-c"])


class BuilderLogEntry(BaseModel):
    timestamp: str
    stage: str
    level: str = "INFO"
    message: str


class BuilderResult(BaseModel):
    builder_id: str
    status: str = Field(default="SUCCESS", description="Build result status (SUCCESS or FAILURE)")
    artifact_name: str
    artifact_sha256: str
    attestation: Optional[Attestation] = None
    signed_attestation: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    logs: List[BuilderLogEntry] = Field(default_factory=list)


class BuilderManagerResponse(BaseModel):
    release_id: str
    results: List[BuilderResult]
