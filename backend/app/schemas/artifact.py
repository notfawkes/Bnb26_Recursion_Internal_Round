from pydantic import BaseModel, Field


class ArtifactInspectionRequest(BaseModel):
    repository_url: str = Field(description="Public HTTPS GitHub repository URL")
    commit_sha: str = Field(description="Pinned 40-character Git commit SHA")


class ArtifactHashRequest(ArtifactInspectionRequest):
    artifact_path: str = Field(description="Repository-relative artifact path returned by detection")


class DetectedArtifact(BaseModel):
    path: str
    name: str
    extension: str
    size_bytes: int


class ArtifactDetectionResponse(BaseModel):
    repository_url: str
    commit_sha: str
    project_type: str
    build_config_id: str
    evidence: list[str]
    artifact: DetectedArtifact
    candidates_found: int


class ArtifactHashResponse(BaseModel):
    repository_url: str
    commit_sha: str
    artifact: DetectedArtifact
    algorithm: str = "sha256"
    digest: str
    bytes_hashed: int
