from pathlib import Path

from builders.manager.artifact import collect_artifact
from builders.manager.hashing import sha256_file


def _builder_artifact(root: Path, contents: bytes):
    dist = root / "dist"
    dist.mkdir(parents=True)
    (dist / "demo-1.0-py3-none-any.whl").write_bytes(contents)
    return sha256_file(collect_artifact(root, "dist/*.whl"))


def test_two_builders_with_identical_bytes_have_identical_sha256(
    tmp_path: Path,
) -> None:
    builder_a = _builder_artifact(tmp_path / "builder-a", b"same package bytes")
    builder_b = _builder_artifact(tmp_path / "builder-b", b"same package bytes")

    assert builder_a.algorithm == "sha256"
    assert builder_a.digest == builder_b.digest


def test_one_changed_byte_produces_a_different_sha256(tmp_path: Path) -> None:
    builder_a = _builder_artifact(tmp_path / "builder-a", b"same package bytes")
    builder_c = _builder_artifact(tmp_path / "builder-c", b"same package byteS")

    assert builder_a.digest != builder_c.digest


def test_manifest_records_selection_and_digest(tmp_path: Path) -> None:
    artifact = _builder_artifact(tmp_path / "builder-a", b"wheel bytes")

    assert artifact.manifest() == {
        "artifact": {
            "path": "dist/demo-1.0-py3-none-any.whl",
            "size_bytes": 11,
        },
        "hash": {
            "algorithm": "sha256",
            "digest": artifact.digest,
        },
    }
