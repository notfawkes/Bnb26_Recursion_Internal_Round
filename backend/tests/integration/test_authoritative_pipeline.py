import pytest
import copy
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.dependencies import mock_builder_manager
from app.services.verification_service import VerificationService
from app.services.real_builder_manager import RealBuilderManager
from app.services.blockchain_service import AnvilBlockchainService
from app.schemas.release import ReleaseResponse
from app.schemas.attestation import BuilderResult, BuildRequest
from app.core.enums import ReleaseStatus


@pytest.fixture
def client():
    return TestClient(app)


def test_scenario_1_verified_unanimous(client):
    """TEST 1: 3 builders produce same hash -> blockchain says VERIFIED"""
    payload = {
        "repository_url": "https://github.com/example/safecalc",
        "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "build_config_id": "python-package-v1",
        "published_hash": "a" * 64,
        "artifact_name": "safecalc.tar.gz",
        "builder_count": 3,
        "quorum_required": 2
    }
    create_res = client.post("/api/v1/releases", json=payload)
    assert create_res.status_code == 201
    rel_id = create_res.json()["release_id"]

    verify_res = client.post(f"/api/v1/releases/{rel_id}/verify?scenario=NORMAL")
    assert verify_res.status_code == 200
    data = verify_res.json()

    assert data["decision"] == "VERIFIED"
    assert data["decision_source"] == "BLOCKCHAIN"
    assert data["blockchain_consistent"] is True
    assert data["blockchain"]["decision"] == "VERIFIED"
    assert data["blockchain"]["quorum_hash"] == "a" * 64


def test_scenario_2_verified_with_disagreement(client):
    """TEST 2: 2 builders produce published hash, 1 builder produces different hash -> blockchain says VERIFIED"""
    payload = {
        "repository_url": "https://github.com/example/safecalc",
        "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "build_config_id": "python-package-v1",
        "published_hash": "a" * 64,
        "artifact_name": "safecalc.tar.gz",
        "builder_count": 3,
        "quorum_required": 2
    }
    create_res = client.post("/api/v1/releases", json=payload)
    rel_id = create_res.json()["release_id"]

    verify_res = client.post(f"/api/v1/releases/{rel_id}/verify?scenario=ONE_DISAGREE")
    assert verify_res.status_code == 200
    data = verify_res.json()

    assert data["decision"] == "VERIFIED"
    assert data["decision_source"] == "BLOCKCHAIN"
    assert data["blockchain_consistent"] is True
    assert data["blockchain"]["quorum_hash"] == "a" * 64
    assert data["builders"][0]["status_detail"] == "AGREE"
    assert data["builders"][1]["status_detail"] == "AGREE"
    assert data["builders"][2]["status_detail"] == "DISAGREE"


def test_scenario_3_rejected_majority_differs(client):
    """TEST 3: 2 builders agree on a hash different from published hash -> blockchain says REJECTED"""
    payload = {
        "repository_url": "https://github.com/example/safecalc",
        "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "build_config_id": "python-package-v1",
        "published_hash": "a" * 64,
        "artifact_name": "safecalc.tar.gz",
        "builder_count": 3,
        "quorum_required": 2
    }
    create_res = client.post("/api/v1/releases", json=payload)
    rel_id = create_res.json()["release_id"]

    verify_res = client.post(f"/api/v1/releases/{rel_id}/verify?scenario=WRONG_QUORUM")
    assert verify_res.status_code == 200
    data = verify_res.json()

    assert data["decision"] == "REJECTED"
    assert data["decision_source"] == "BLOCKCHAIN"
    assert data["blockchain_consistent"] is True
    assert data["blockchain"]["quorum_hash"] == "b" * 64


def test_scenario_4_disputed_all_different(client):
    """TEST 4: 3 builders produce different hashes -> blockchain says DISPUTED"""
    payload = {
        "repository_url": "https://github.com/example/safecalc",
        "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "build_config_id": "python-package-v1",
        "published_hash": "a" * 64,
        "artifact_name": "safecalc.tar.gz",
        "builder_count": 3,
        "quorum_required": 2
    }
    create_res = client.post("/api/v1/releases", json=payload)
    rel_id = create_res.json()["release_id"]

    verify_res = client.post(f"/api/v1/releases/{rel_id}/verify?scenario=ALL_DIFFERENT")
    assert verify_res.status_code == 200
    data = verify_res.json()

    assert data["decision"] == "DISPUTED"
    assert data["decision_source"] == "BLOCKCHAIN"
    assert data["blockchain_consistent"] is True


def test_scenario_5_strict_quorum_disputed(client):
    """TEST 5: quorum policy is 3/3, one builder disagrees -> blockchain says DISPUTED"""
    payload = {
        "repository_url": "https://github.com/example/safecalc",
        "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "build_config_id": "python-package-v1",
        "published_hash": "a" * 64,
        "artifact_name": "safecalc.tar.gz",
        "builder_count": 3,
        "quorum_required": 3
    }
    create_res = client.post("/api/v1/releases", json=payload)
    rel_id = create_res.json()["release_id"]

    verify_res = client.post(f"/api/v1/releases/{rel_id}/verify?scenario=STRICT_DISAGREE")
    assert verify_res.status_code == 200
    data = verify_res.json()

    assert data["decision"] == "DISPUTED"
    assert data["decision_source"] == "BLOCKCHAIN"


def test_scenario_6_invalid_signature_rejected(client):
    """TEST 6: one builder has an invalid Ed25519 signature -> invalid evidence is not submitted as valid evidence"""
    payload = {
        "repository_url": "https://github.com/example/safecalc",
        "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "build_config_id": "python-package-v1",
        "published_hash": "a" * 64,
        "artifact_name": "safecalc.tar.gz",
        "builder_count": 3,
        "quorum_required": 2
    }
    create_res = client.post("/api/v1/releases", json=payload)
    rel_id = create_res.json()["release_id"]

    verify_res = client.post(f"/api/v1/releases/{rel_id}/verify?scenario=INVALID_SIGNATURE")
    assert verify_res.status_code == 200
    data = verify_res.json()

    # Builder B (index 1) has invalid signature
    builders = data["builders"]
    assert builders[1]["signature_valid"] is False
    assert builders[1]["valid"] is False
    assert builders[1]["status_detail"] == "INVALID"

    # Only valid builders (A and C) are submitted as attestations on-chain
    assert len(data["blockchain"]["attestation_txs"]) == 2
    assert data["decision"] == "VERIFIED"


def test_scenario_7_unauthorized_builder_identity_rejected():
    """TEST 7: builder identity does not match trusted public key -> attestation rejected"""
    expected_release = ReleaseResponse(
        release_id="00000000-0000-0000-0000-000000000001",
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
        created_at="2026-10-04T00:00:00Z"
    )

    untrusted_result = {
        "builder_id": "malicious-builder",
        "status": "SUCCESS",
        "artifact_name": "safecalc.tar.gz",
        "artifact_sha256": "a" * 64,
        "signed_attestation": {
            "attestation": {
                "schema_version": "v1",
                "release_id": "00000000-0000-0000-0000-000000000001",
                "builder_id": "malicious-builder",
                "public_key_id": "malicious-builder-key-v1",
                "source": {
                    "repository_url": "https://github.com/example/safecalc",
                    "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
                },
                "build": {
                    "config_id": "python-package-v1",
                    "image_id": "img",
                    "source_date_epoch": 1,
                    "status": "SUCCESS"
                },
                "artifact": {
                    "path": "dist/safecalc.tar.gz",
                    "algorithm": "sha256",
                    "digest": "a" * 64,
                    "size_bytes": 100
                }
            },
            "public_key_id": "malicious-builder-key-v1",
            "signature_algorithm": "ed25519",
            "canonicalization": "quorum-json-v1",
            "signature": "c2lnbmF0dXJl"
        }
    }

    ver_res = VerificationService.verify_builder_result(untrusted_result, expected_release)
    assert ver_res.identity_valid is False
    assert ver_res.valid is False
    assert ver_res.status_detail.value == "INVALID"


def test_scenario_8_commit_mismatch_rejected():
    """TEST 8: commit mismatch -> attestation rejected"""
    expected_release = ReleaseResponse(
        release_id="00000000-0000-0000-0000-000000000001",
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
        created_at="2026-10-04T00:00:00Z"
    )

    mismatch_commit_result = {
        "builder_id": "builder-a",
        "status": "SUCCESS",
        "artifact_name": "safecalc.tar.gz",
        "artifact_sha256": "a" * 64,
        "signed_attestation": {
            "attestation": {
                "schema_version": "v1",
                "release_id": "00000000-0000-0000-0000-000000000001",
                "builder_id": "builder-a",
                "public_key_id": "builder-a-key-v1",
                "source": {
                    "repository_url": "https://github.com/example/safecalc",
                    "commit_sha": "ffffffffffffffffffffffffffffffffffffffff"  # WRONG COMMIT
                },
                "build": {
                    "config_id": "python-package-v1",
                    "image_id": "img",
                    "source_date_epoch": 1,
                    "status": "SUCCESS"
                },
                "artifact": {
                    "path": "dist/safecalc.tar.gz",
                    "algorithm": "sha256",
                    "digest": "a" * 64,
                    "size_bytes": 100
                }
            },
            "public_key_id": "builder-a-key-v1",
            "signature_algorithm": "ed25519",
            "canonicalization": "quorum-json-v1",
            "signature": "c2lnbmF0dXJl"
        }
    }

    ver_res = VerificationService.verify_builder_result(mismatch_commit_result, expected_release)
    assert ver_res.commit_match is False
    assert ver_res.valid is False


def test_scenario_9_release_id_mismatch_rejected():
    """TEST 9: release ID mismatch -> attestation rejected"""
    expected_release = ReleaseResponse(
        release_id="00000000-0000-0000-0000-000000000001",
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
        created_at="2026-10-04T00:00:00Z"
    )

    mismatch_rel_result = {
        "builder_id": "builder-a",
        "status": "SUCCESS",
        "artifact_name": "safecalc.tar.gz",
        "artifact_sha256": "a" * 64,
        "signed_attestation": {
            "attestation": {
                "schema_version": "v1",
                "release_id": "99999999-9999-9999-9999-999999999999",  # WRONG RELEASE ID
                "builder_id": "builder-a",
                "public_key_id": "builder-a-key-v1",
                "source": {
                    "repository_url": "https://github.com/example/safecalc",
                    "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
                },
                "build": {
                    "config_id": "python-package-v1",
                    "image_id": "img",
                    "source_date_epoch": 1,
                    "status": "SUCCESS"
                },
                "artifact": {
                    "path": "dist/safecalc.tar.gz",
                    "algorithm": "sha256",
                    "digest": "a" * 64,
                    "size_bytes": 100
                }
            },
            "public_key_id": "builder-a-key-v1",
            "signature_algorithm": "ed25519",
            "canonicalization": "quorum-json-v1",
            "signature": "c2lnbmF0dXJl"
        }
    }

    ver_res = VerificationService.verify_builder_result(mismatch_rel_result, expected_release)
    assert ver_res.valid is False


def test_scenario_10_blockchain_unavailable_clean_error(monkeypatch):
    """TEST 10: blockchain unavailable -> clean API error; no fake verification result"""
    # Force real blockchain mode with an unreachable RPC port
    monkeypatch.setattr(settings, "USE_MOCK_BLOCKCHAIN", False)
    monkeypatch.setattr(settings, "BLOCKCHAIN_RPC_URL", "http://127.0.0.1:9999")

    # Create fresh AnvilBlockchainService pointing to offline RPC
    offline_bc = AnvilBlockchainService()
    monkeypatch.setattr("app.dependencies.anvil_blockchain_service", offline_bc)

    offline_client = TestClient(app)
    payload = {
        "repository_url": "https://github.com/example/safecalc",
        "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "build_config_id": "python-package-v1",
        "published_hash": "a" * 64,
        "artifact_name": "safecalc.tar.gz",
        "builder_count": 3,
        "quorum_required": 2
    }

    res = offline_client.post("/api/v1/releases", json=payload)
    # Must fail with clean HTTP error (503 Service Unavailable or 500 error), NEVER 201 with fake mock data
    assert res.status_code in (500, 503)
    assert "unavailable" in res.text.lower() or "blockchain" in res.text.lower()
