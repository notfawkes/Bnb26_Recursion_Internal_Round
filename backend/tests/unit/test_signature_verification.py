from cryptography.hazmat.primitives.asymmetric import ed25519
from app.services.signature_service import SignatureService


def test_valid_ed25519_signature_verification():
    # 1. Generate a real Ed25519 keypair
    priv_key = ed25519.Ed25519PrivateKey.generate()
    pub_key_bytes = priv_key.public_key().public_bytes_raw()
    pub_key_hex = pub_key_bytes.hex()

    # 2. Build sample attestation payload
    attestation_dict = {
        "builder": {
            "id": "builder-A",
            "public_key": pub_key_hex,
            "wallet_address": "0x1111111111111111111111111111111111111111"
        },
        "source": {
            "repository": "https://github.com/example/project",
            "commit": "abc1234567890abcdef1234567890abcdef12345"
        },
        "artifact": {
            "name": "project-linux-amd64.tar.gz",
            "sha256": "a" * 64
        },
        "build": {
            "environment": "ubuntu:24.04",
            "command": "make"
        },
        "result": {
            "tests_passed": True
        },
        "timestamp": "2026-10-03T22:00:00Z",
        "signature": ""
    }

    # 3. Construct canonical payload and sign
    canonical_bytes = SignatureService.construct_canonical_payload(attestation_dict)
    sig_bytes = priv_key.sign(canonical_bytes)
    attestation_dict["signature"] = sig_bytes.hex()

    # 4. Verify signature
    assert SignatureService.verify_attestation_signature(attestation_dict) is True


def test_tampered_payload_fails_signature_verification():
    priv_key = ed25519.Ed25519PrivateKey.generate()
    pub_key_hex = priv_key.public_key().public_bytes_raw().hex()

    attestation_dict = {
        "builder": {"id": "builder-A", "public_key": pub_key_hex, "wallet_address": "0x1111"},
        "source": {"repository": "https://github.com/example/project", "commit": "abc1234567890abcdef1234567890abcdef12345"},
        "artifact": {"name": "binary.tar.gz", "sha256": "a" * 64},
        "build": {"environment": "ubuntu:24.04", "command": "make"},
        "result": {"tests_passed": True},
        "timestamp": "2026-10-03T22:00:00Z",
        "signature": ""
    }

    canonical_bytes = SignatureService.construct_canonical_payload(attestation_dict)
    sig_bytes = priv_key.sign(canonical_bytes)
    attestation_dict["signature"] = sig_bytes.hex()

    # Tamper with the artifact SHA-256 after signing
    attestation_dict["artifact"]["sha256"] = "b" * 64

    assert SignatureService.verify_attestation_signature(attestation_dict) is False


def test_invalid_signature_hex_fails_verification():
    priv_key = ed25519.Ed25519PrivateKey.generate()
    pub_key_hex = priv_key.public_key().public_bytes_raw().hex()

    attestation_dict = {
        "builder": {"id": "builder-A", "public_key": pub_key_hex, "wallet_address": "0x1111"},
        "source": {"repository": "https://github.com/example/project", "commit": "abc1234567890abcdef1234567890abcdef12345"},
        "artifact": {"name": "binary.tar.gz", "sha256": "a" * 64},
        "build": {"environment": "ubuntu:24.04", "command": "make"},
        "result": {"tests_passed": True},
        "timestamp": "2026-10-03T22:00:00Z",
        "signature": "f" * 128  # invalid signature
    }

    assert SignatureService.verify_attestation_signature(attestation_dict) is False
