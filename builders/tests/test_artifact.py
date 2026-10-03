from pathlib import Path

import pytest

from builders.manager.artifact import (
    ArtifactError,
    collect_and_hash_artifact,
    hash_artifact,
)


def test_identical_bytes_have_identical_sha256(tmp_path: Path) -> None:
    first = tmp_path / "first.whl"
    second = tmp_path / "second.whl"
    first.write_bytes(b"same package bytes")
    second.write_bytes(b"same package bytes")

    assert hash_artifact(first) == hash_artifact(second)
    second.write_bytes(b"same package byteS")
    assert hash_artifact(first) != hash_artifact(second)


def test_collect_one_wheel_and_hash_its_bytes(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = dist / "demo-1.0-py3-none-any.whl"
    wheel.write_bytes(b"wheel bytes")

    artifact = collect_and_hash_artifact(tmp_path, "dist/*.whl")

    assert artifact.path == wheel
    assert artifact.relative_path == "dist/demo-1.0-py3-none-any.whl"
    assert artifact.size_bytes == len(b"wheel bytes")
    assert artifact.algorithm == "sha256"
    assert artifact.digest == hash_artifact(wheel)


def test_missing_or_multiple_wheels_are_rejected(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    with pytest.raises(ArtifactError, match="found 0"):
        collect_and_hash_artifact(tmp_path, "dist/*.whl")

    (dist / "first.whl").write_bytes(b"first")
    (dist / "second.whl").write_bytes(b"second")
    with pytest.raises(ArtifactError, match="found 2"):
        collect_and_hash_artifact(tmp_path, "dist/*.whl")


def test_empty_or_oversized_wheel_is_rejected(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = dist / "demo.whl"
    wheel.write_bytes(b"")
    with pytest.raises(ArtifactError, match="size"):
        collect_and_hash_artifact(tmp_path, "dist/*.whl")

    wheel.write_bytes(b"too large")
    with pytest.raises(ArtifactError, match="size"):
        collect_and_hash_artifact(tmp_path, "dist/*.whl", max_bytes=2)
