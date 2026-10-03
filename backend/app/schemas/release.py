from typing import Optional
from pydantic import BaseModel, Field, model_validator
from app.core.enums import ReleaseStatus


class ReleaseCreate(BaseModel):
    repository_url: Optional[str] = Field(default=None, description="Public Git repository URL")
    repository: Optional[str] = Field(default=None, description="Alias for repository_url")

    commit_sha: Optional[str] = Field(default=None, description="Pinned source commit SHA")
    commit: Optional[str] = Field(default=None, description="Alias for commit_sha")

    build_config_id: str = Field(default="python-package-v1", description="Build configuration profile ID")
    published_artifact: Optional[str] = Field(
        default=None,
        description="Optional file path or content to calculate published SHA-256 hash"
    )
    published_hash: Optional[str] = Field(
        default=None,
        description="Published artifact SHA-256 hash (64 hex characters)"
    )
    artifact_name: str = Field(default="project-linux-amd64.tar.gz", description="Artifact binary filename")
    builder_count: int = Field(default=3, ge=1, description="Total independent builders")
    quorum_required: int = Field(default=2, ge=1, description="Quorum threshold required for agreement")

    @model_validator(mode="after")
    def validate_repo_and_commit(self):
        if not self.repository_url and not self.repository:
            raise ValueError("Either 'repository_url' or 'repository' must be provided.")
        if not self.commit_sha and not self.commit:
            raise ValueError("Either 'commit_sha' or 'commit' must be provided.")

        # Normalize aliases
        if not self.repository_url and self.repository:
            self.repository_url = self.repository
        if not self.repository and self.repository_url:
            self.repository = self.repository_url

        if not self.commit_sha and self.commit:
            self.commit_sha = self.commit
        if not self.commit and self.commit_sha:
            self.commit = self.commit_sha

        return self


class ReleaseResponse(BaseModel):
    release_id: str
    repository_url: str
    repository: str
    commit_sha: str
    commit: str
    build_config_id: str = "python-package-v1"
    published_hash: str
    artifact_name: str
    builder_count: int
    quorum_required: int
    status: ReleaseStatus
    created_at: str
