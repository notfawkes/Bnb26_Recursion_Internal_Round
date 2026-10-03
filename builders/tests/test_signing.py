import copy
from pathlib import Path

import pytest

from builders.manager.signing import (
    canonical_attestation_bytes,
    generate_development_keypair,
    sign_attestation,
    verify_attestation_signature,
)


def test_canonical_bytes_do_not_depend_on_input_key_order() -> None:
    first = {"z": 1, "a": {"y": "yes", "b": "no"}}
    second = {"a": {"b": "no", "y": "yes"}, "z": 1}
    expected = b'{"a":{"b":"no","y":"yes"},"z":1}'

    assert canonical_attestation_bytes(first) == expected
    assert canonical_attestation_bytes(second) == expected


def test_canonical_format_rejects_unsupported_numbers() -> None:
    with pytest.raises(TypeError, match="v1 attestation values"):
        canonical_attestation_bytes({"float": 1.5})


def test_sign_verify_and_detect_tampering(tmp_path: Path) -> None:
    keys = generate_development_keypair("builder-a", tmp_path / "keys")
    attestation = {
        "builder_id": "builder-a",
        "public_key_id": keys.public_key_id,
        "artifact": {"digest": "a" * 64},
    }
    envelope = sign_attestation(attestation, keys.private_path)

    assert verify_attestation_signature(envelope, keys.public_path.read_bytes())

    tampered = copy.deepcopy(envelope)
    tampered["attestation"]["artifact"]["digest"] = "b" * 64
    assert not verify_attestation_signature(tampered, keys.public_path.read_bytes())


def test_wrong_public_key_is_rejected(tmp_path: Path) -> None:
    first = generate_development_keypair("builder-a", tmp_path / "first")
    other = generate_development_keypair("builder-b", tmp_path / "other")
    envelope = sign_attestation(
        {"builder_id": "builder-a", "public_key_id": first.public_key_id},
        first.private_path,
    )

    assert not verify_attestation_signature(envelope, other.public_path.read_bytes())


def test_key_generation_refuses_to_overwrite(tmp_path: Path) -> None:
    generate_development_keypair("builder-a", tmp_path)
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        generate_development_keypair("builder-a", tmp_path)
