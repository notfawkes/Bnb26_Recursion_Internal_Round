from app.services.verification_service import VerificationService
from app.services.builder_service import builder_registry
from app.services.signature_service import SignatureService
from app.schemas.release import ReleaseResponse
from app.schemas.attestation import BuilderResult, Attestation
from app.core.enums import ReleaseStatus


def test_valid_builder_result_verification_pass():
    keypair = builder_registry.get_test_keypair("builder-a")
    priv_key, pubkey_hex = keypair

    release = ReleaseResponse(
        release_id="REL-001",
        repository_url="https://github.com/example/safecalc",
        repository="https://github.com/example/safecalc",
        commit_sha="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        commit="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        build_config_id="python-package-v1",
        published_hash="a" * 64,
        artifact_name="safecalc.tar.gz",
        builder_count=3,
        quorum_required=2,
        status=ReleaseStatus.CREATED,
        created_at="2026-10-03T22:00:00Z"
    )

    att_dict = {
        "builder": {
            "id": "builder-a",
            "public_key": pubkey_hex,
            "wallet_address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
        },
        "source": {
            "repository": release.repository_url,
            "commit": release.commit_sha
        },
        "artifact": {
            "name": release.artifact_name,
            "sha256": release.published_hash
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

    canonical_bytes = SignatureService.construct_canonical_payload(att_dict)
    att_dict["signature"] = priv_key.sign(canonical_bytes).hex()

    b_res = BuilderResult(
        builder_id="builder-a",
        status="SUCCESS",
        artifact_name=release.artifact_name,
        artifact_sha256=release.published_hash,
        attestation=Attestation(**att_dict)
    )

    res = VerificationService.verify_builder_result(b_res, release)
    assert res.valid is True
    assert res.signature_valid is True
    assert res.identity_valid is True
    assert res.source_match is True
    assert res.commit_match is True


def test_attestation_repository_mismatch_fails():
    keypair = builder_registry.get_test_keypair("builder-a")
    priv_key, pubkey_hex = keypair

    release = ReleaseResponse(
        release_id="REL-001",
        repository_url="https://github.com/example/safecalc",
        repository="https://github.com/example/safecalc",
        commit_sha="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        commit="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        build_config_id="python-package-v1",
        published_hash="a" * 64,
        artifact_name="safecalc.tar.gz",
        builder_count=3,
        quorum_required=2,
        status=ReleaseStatus.CREATED,
        created_at="2026-10-03T22:00:00Z"
    )

    att_dict = {
        "builder": {"id": "builder-a", "public_key": pubkey_hex, "wallet_address": "0x1111"},
        "source": {"repository": "https://github.com/WRONG/safecalc", "commit": release.commit_sha},
        "artifact": {"name": release.artifact_name, "sha256": release.published_hash},
        "build": {"environment": "ubuntu:24.04", "command": "make"},
        "result": {"tests_passed": True},
        "timestamp": "2026-10-03T22:00:00Z",
        "signature": ""
    }
    canonical_bytes = SignatureService.construct_canonical_payload(att_dict)
    att_dict["signature"] = priv_key.sign(canonical_bytes).hex()

    res = VerificationService.verify_attestation(att_dict, release)
    assert res.valid is False
    assert res.source_match is False
