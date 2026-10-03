"""Sign exact attestation bytes with development Ed25519 builder keys."""

import base64
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from builders.manager.request_validator import BUILDER_IDS

CANONICALIZATION = "quorum-json-v1"
SIGNATURE_ALGORITHM = "ed25519"


@dataclass(frozen=True)
class DevelopmentKeyPair:
    private_path: Path
    public_path: Path
    public_key_id: str


def _check_v1_value(value: object) -> None:
    if type(value) in (str, int):
        return
    if type(value) is dict:
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("attestation object keys must be strings")
            _check_v1_value(item)
        return
    raise TypeError("v1 attestation values must be strings, integers or objects")


def canonical_attestation_bytes(attestation: dict[str, object]) -> bytes:
    """Use the exact UTF-8 JSON bytes agreed in shared/specs/.

    This is a deliberately restricted project format, not a claim of full
    RFC 8785 compliance. V1 attestations use only strings and integers.
    """
    _check_v1_value(attestation)
    return json.dumps(
        attestation,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def generate_development_keypair(
    builder_id: str, directory: Path
) -> DevelopmentKeyPair:
    """Create unencrypted local-only test keys; never mount them into a build."""
    if builder_id not in BUILDER_IDS:
        raise ValueError("builder_id is not approved")
    directory.mkdir(parents=True, exist_ok=True)
    private_path = directory / f"{builder_id}-key-v1.pem"
    public_path = directory / f"{builder_id}-key-v1.pub.pem"
    if private_path.exists() or public_path.exists():
        raise FileExistsError("development key already exists; refusing to overwrite")

    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_created = False
    try:
        with private_path.open("xb") as private_file:
            private_created = True
            private_file.write(private_bytes)
        os.chmod(private_path, 0o600)
        with public_path.open("xb") as public_file:
            public_file.write(public_bytes)
    except OSError:
        if private_created:
            private_path.unlink(missing_ok=True)
        raise
    return DevelopmentKeyPair(private_path, public_path, f"{builder_id}-key-v1")


def sign_attestation(
    attestation: dict[str, object], private_key_path: Path
) -> dict[str, object]:
    private_key = serialization.load_pem_private_key(
        private_key_path.read_bytes(), password=None
    )
    if not isinstance(private_key, Ed25519PrivateKey):
        raise TypeError("private key must be Ed25519")

    key_id = attestation.get("public_key_id")
    if not isinstance(key_id, str) or not key_id:
        raise ValueError("attestation has no public_key_id")
    signature = private_key.sign(canonical_attestation_bytes(attestation))
    return {
        "attestation": attestation,
        "public_key_id": key_id,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "canonicalization": CANONICALIZATION,
        "signature": base64.b64encode(signature).decode("ascii"),
    }


def verify_attestation_signature(
    envelope: Mapping[str, object], public_key_pem: bytes
) -> bool:
    """Verify cryptography only; trusted key ownership is the backend's job."""
    attestation = envelope.get("attestation")
    key_id = envelope.get("public_key_id")
    signature_text = envelope.get("signature")
    if (
        not isinstance(attestation, dict)
        or not isinstance(key_id, str)
        or attestation.get("public_key_id") != key_id
        or envelope.get("signature_algorithm") != SIGNATURE_ALGORITHM
        or envelope.get("canonicalization") != CANONICALIZATION
        or not isinstance(signature_text, str)
    ):
        return False
    try:
        public_key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(public_key, Ed25519PublicKey):
            return False
        signature = base64.b64decode(signature_text, validate=True)
        public_key.verify(signature, canonical_attestation_bytes(attestation))
    except (InvalidSignature, ValueError, TypeError):
        return False
    return True
