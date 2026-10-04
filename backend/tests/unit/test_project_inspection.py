from hashlib import sha256
from pathlib import Path

import pytest

from app.services.project_inspection_service import (
    ProjectInspectionError,
    ProjectInspectionService,
)


@pytest.mark.parametrize(
    ("marker", "artifact", "project_type", "profile"),
    [
        ("pyproject.toml", "dist/demo-1.0.0-py3-none-any.whl", "Python", "python-package-v1"),
        ("package.json", "dist/demo-1.0.0.tgz", "Node.js", "node-package-v1"),
        ("pom.xml", "target/demo-1.0.0.jar", "Java", "java-maven-v1"),
    ],
)
def test_detects_supported_project_and_artifact(
    tmp_path: Path, marker: str, artifact: str, project_type: str, profile: str
) -> None:
    (tmp_path / marker).write_text("{}", encoding="utf-8")
    artifact_path = tmp_path / artifact
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(b"release bytes")

    result = ProjectInspectionService.inspect_directory(
        tmp_path, "https://github.com/example/demo", "a" * 40
    )

    assert result.project_type == project_type
    assert result.build_config_id == profile
    assert result.artifact.path == artifact
    assert result.artifact.size_bytes == len(b"release bytes")


def test_artifact_selection_prefers_profile_extension_and_output_directory(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "old.whl").write_bytes(b"old")
    target = tmp_path / "dist" / "package.tgz"
    target.parent.mkdir()
    target.write_bytes(b"node package")

    result = ProjectInspectionService.inspect_directory(
        tmp_path, "https://github.com/example/demo", "b" * 40
    )

    assert result.artifact.path == "dist/package.tgz"
    assert result.candidates_found == 2


def test_explicit_disputed_marker_selects_demo_profile(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "quorum-disputed-demo.json").write_text("{}", encoding="utf-8")
    package = tmp_path / "release-assets" / "published" / "demo-1.0.0.tgz"
    package.parent.mkdir(parents=True)
    package.write_bytes(b"node package")

    result = ProjectInspectionService.inspect_directory(
        tmp_path, "https://github.com/example/demo", "e" * 40
    )

    assert result.project_type == "Node.js (Disputed Demo)"
    assert result.build_config_id == "node-disputed-demo-v1"
    assert result.evidence == ["package.json", "quorum-disputed-demo.json"]


def test_rejects_repository_without_supported_marker(tmp_path: Path) -> None:
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "demo.jar").write_bytes(b"jar")
    with pytest.raises(ProjectInspectionError, match="project marker"):
        ProjectInspectionService.inspect_directory(
            tmp_path, "https://github.com/example/demo", "c" * 40
        )


def test_streaming_digest_matches_artifact_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "pyproject.toml").write_text("[build-system]", encoding="utf-8")
    wheel = tmp_path / "dist" / "demo.whl"
    wheel.parent.mkdir()
    wheel.write_bytes(b"known wheel bytes")

    from contextlib import contextmanager

    @contextmanager
    def fake_checkout(repository_url: str, commit_sha: str):
        yield tmp_path

    monkeypatch.setattr(ProjectInspectionService, "_checkout", fake_checkout)
    result = ProjectInspectionService.hash_artifact(
        "https://github.com/example/demo", "d" * 40, "dist/demo.whl"
    )

    assert result.digest == sha256(b"known wheel bytes").hexdigest()
    assert result.bytes_hashed == len(b"known wheel bytes")
