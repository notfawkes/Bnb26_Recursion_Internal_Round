import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.dependencies import get_builder_manager, get_blockchain_service
from app.services.real_builder_manager import RealBuilderManager
from app.services.blockchain_service import AnvilBlockchainService


@pytest.mark.asyncio
async def test_real_pipeline_end_to_end_no_mocks(monkeypatch):
    """
    CRITICAL FINAL INTEGRATION TEST:
    Executes the entire Quorum pipeline end-to-end with:
    - Real FastAPI
    - Real Builder Manager
    - Real Docker containers
    - Real Ed25519 signatures
    - Real Anvil node
    - Real QuorumVerifier.sol smart contract
    NO MOCKS ALLOWED.
    """
    monkeypatch.setattr(settings, "USE_MOCK_BUILDERS", False)
    monkeypatch.setattr(settings, "USE_MOCK_BLOCKCHAIN", False)

    real_builder_mgr = RealBuilderManager()
    real_blockchain_svc = AnvilBlockchainService()
    assert real_blockchain_svc.is_connected(), "Anvil blockchain must be running on port 8545 with QuorumVerifier deployed"

    app.dependency_overrides[get_builder_manager] = lambda: real_builder_mgr
    app.dependency_overrides[get_blockchain_service] = lambda: real_blockchain_svc

    try:
        client = TestClient(app)

        # 1. POST /api/v1/releases
        create_payload = {
            "repository_url": "https://github.com/pypa/sampleproject",
            "commit_sha": "621e4974ca25ce531773def586ba3ed8e736b3fc",
            "build_config_id": "python-package-v1",
            "published_hash": "0d9a9a49b40160078387d2ec1c7a59d4135c3095b1b210d8c537ad9f7accafd1",
            "artifact_name": "sampleproject-3.0.0-py3-none-any.whl",
            "builder_count": 3,
            "quorum_required": 2
        }

        create_res = client.post("/api/v1/releases", json=create_payload)
        assert create_res.status_code == 201, f"Failed to create release: {create_res.text}"
        release_data = create_res.json()
        release_id = release_data["release_id"]
        assert int(release_id) >= 1

        # 2. POST /api/v1/releases/{id}/verify (Real Docker builds & Real Blockchain transactions)
        verify_res = client.post(f"/api/v1/releases/{release_id}/verify")
        assert verify_res.status_code == 200, f"Verification failed: {verify_res.text}"
        v_data = verify_res.json()

        assert v_data["release_id"] == release_id
        assert v_data["decision"] == "VERIFIED"
        assert v_data["decision_source"] == "BLOCKCHAIN"
        assert v_data["blockchain_consistent"] is True

        # Check all 3 builders
        builders = v_data["builders"]
        assert len(builders) == 3
        for b in builders:
            assert b["valid"] is True
            assert b["signature_valid"] is True
            assert b["identity_valid"] is True
            assert b["source_match"] is True
            assert b["commit_match"] is True
            assert b["artifact_sha256"] == "0d9a9a49b40160078387d2ec1c7a59d4135c3095b1b210d8c537ad9f7accafd1"

        # Check blockchain record
        bc = v_data["blockchain"]
        assert bc["is_finalized"] is True
        assert bc["decision"] == "VERIFIED"
        assert bc["quorum_hash"] == "0d9a9a49b40160078387d2ec1c7a59d4135c3095b1b210d8c537ad9f7accafd1"
        assert bc["create_release_tx"] is not None
        assert len(bc["attestation_txs"]) == 3
        assert bc["finalize_tx"] is not None

        # 3. GET /api/v1/releases/{id}
        get_rel = client.get(f"/api/v1/releases/{release_id}")
        assert get_rel.status_code == 200
        assert get_rel.json()["status"] == "VERIFIED"

        # 4. GET /api/v1/releases/{id}/result
        get_res = client.get(f"/api/v1/releases/{release_id}/result")
        assert get_res.status_code == 200
        res_data = get_res.json()
        assert res_data["decision"] == "VERIFIED"
        assert res_data["decision_source"] == "BLOCKCHAIN"
        assert res_data["quorum_hash"] == "0d9a9a49b40160078387d2ec1c7a59d4135c3095b1b210d8c537ad9f7accafd1"

        # 5. GET /api/v1/releases/{id}/attestations
        get_att = client.get(f"/api/v1/releases/{release_id}/attestations")
        assert get_att.status_code == 200
        atts_response = get_att.json()
        atts = atts_response["attestations"]
        assert len(atts) == 3
        for att in atts:
            assert att["artifactHash"] == "0d9a9a49b40160078387d2ec1c7a59d4135c3095b1b210d8c537ad9f7accafd1"

    finally:
        app.dependency_overrides.clear()
