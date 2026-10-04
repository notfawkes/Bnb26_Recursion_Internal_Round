from pathlib import Path

import pytest

from builders.manager.artifact import (
    ArtifactError,
    collect_artifact,
)


def test_collect_one_wheel(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = dist / "demo-1.0-py3-none-any.whl"
    wheel.write_bytes(b"wheel bytes")

    artifact = collect_artifact(tmp_path, "dist/*.whl")

    assert artifact.path == wheel
    assert artifact.relative_path == "dist/demo-1.0-py3-none-any.whl"
    assert artifact.size_bytes == len(b"wheel bytes")


def test_missing_or_multiple_wheels_are_rejected(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    with pytest.raises(ArtifactError, match="found 0"):
        collect_artifact(tmp_path, "dist/*.whl")

    (dist / "first.whl").write_bytes(b"first")
    (dist / "second.whl").write_bytes(b"second")
    with pytest.raises(ArtifactError, match="found 2"):
        collect_artifact(tmp_path, "dist/*.whl")


def test_empty_or_oversized_wheel_is_rejected(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = dist / "demo.whl"
    wheel.write_bytes(b"")
    with pytest.raises(ArtifactError, match="size"):
        collect_artifact(tmp_path, "dist/*.whl")

    wheel.write_bytes(b"too large")
    with pytest.raises(ArtifactError, match="size"):
        collect_artifact(tmp_path, "dist/*.whl", max_bytes=2)
