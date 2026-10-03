import pytest
from app.schemas.attestation import BuildRequest, BuilderManagerResponse, BuilderResult
from app.schemas.release import ReleaseResponse
from app.schemas.verification import VerificationResponse, LocalQuorumResult, BlockchainRecord
from app.core.enums import ReleaseStatus, Decision
from app.services.mock_builder_manager import MockBuilderManager
from app.services.blockchain_service import MockBlockchainService, AnvilBlockchainService
from app.config import settings


@pytest.mark.asyncio
async def test_build_request_exact_schema():
    req = BuildRequest(
        release_id="d4f2496e-5c5a-4c82-9fd5-f3c3012a524e",
        repository_url="https://github.com/example/safecalc",
        commit_sha="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        build_config_id="python-package-v1",
        builders=["builder-a", "builder-b", "builder-c"]
    )
    req_dict = req.model_dump()
    assert "published_hash" not in req_dict
    assert "build_command" not in req_dict
    assert "artifact_path" not in req_dict
    assert req_dict["release_id"] == "d4f2496e-5c5a-4c82-9fd5-f3c3012a524e"
    assert req_dict["repository_url"] == "https://github.com/example/safecalc"
    assert req_dict["commit_sha"] == "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
    assert req_dict["build_config_id"] == "python-package-v1"
    assert req_dict["builders"] == ["builder-a", "builder-b", "builder-c"]


@pytest.mark.asyncio
async def test_builder_manager_response_and_mock():
    mock_mgr = MockBuilderManager()
    req = BuildRequest(
        release_id="d4f2496e-5c5a-4c82-9fd5-f3c3012a524e",
        repository_url="https://github.com/example/safecalc",
        commit_sha="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        build_config_id="python-package-v1",
        builders=["builder-a", "builder-b", "builder-c"]
    )
    res = await mock_mgr.run_builders(req)
    assert isinstance(res, BuilderManagerResponse)
    assert res.release_id == req.release_id
    assert len(res.results) == 3
    for b_res in res.results:
        assert isinstance(b_res, BuilderResult)
        assert b_res.status == "SUCCESS"
        assert b_res.artifact_sha256 is not None
        assert b_res.attestation is not None


@pytest.mark.asyncio
async def test_blockchain_configuration():
    assert settings.BLOCKCHAIN_RPC_URL == "http://127.0.0.1:8545"
    assert settings.BLOCKCHAIN_CHAIN_ID == 31337
    assert settings.BLOCKCHAIN_CONTRACT_ADDRESS == "0x5FbDB2315678afecb367f032d93F642f64180aa3"
    assert settings.BLOCKCHAIN_ABI_PATH == "blockchain/deployments/QuorumVerifier.abi.json"


@pytest.mark.asyncio
async def test_blockchain_service_flow():
    bc = MockBlockchainService()
    pub_hash = "a" * 64

    # 1. createRelease sends published_hash
    create_res = await bc.create_release(
        repository_url="https://github.com/example/safecalc",
        commit_sha="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        published_hash=pub_hash,
        builder_count=3,
        quorum_required=2
    )
    rel_id = create_res["release_id"]

    # 2. submitAttestation for each builder with individual artifact hash
    await bc.submit_attestation(rel_id, "builder-a", pub_hash)
    await bc.submit_attestation(rel_id, "builder-b", pub_hash)
    await bc.submit_attestation(rel_id, "builder-c", "b" * 64)

    # 3. finalizeRelease
    fin_res = await bc.finalize_release(rel_id)
    assert fin_res["decision"] == "VERIFIED"

    # 4. getRelease returns authoritative state
    rel_data = await bc.get_release(rel_id)
    assert rel_data["published_hash"] == pub_hash
    assert rel_data["quorum_hash"] == pub_hash
    assert rel_data["decision"] == "VERIFIED"
    assert rel_data["is_finalized"] is True
