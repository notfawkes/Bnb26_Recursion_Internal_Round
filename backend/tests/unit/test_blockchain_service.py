import pytest
from app.services.blockchain_service import MockBlockchainService, AnvilBlockchainService


@pytest.mark.asyncio
async def test_mock_blockchain_service_flow():
    svc = MockBlockchainService()
    res = await svc.create_release(
        repository_url="https://github.com/example/safecalc",
        commit_sha="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        published_hash="a" * 64,
        builder_count=3,
        quorum_required=2
    )
    assert res["recorded"] is True
    release_id = res["release_id"]

    att_res1 = await svc.submit_attestation(
        release_id=release_id,
        builder_id="builder-a",
        artifact_hash="a" * 64
    )
    assert att_res1["recorded"] is True

    att_res2 = await svc.submit_attestation(
        release_id=release_id,
        builder_id="builder-b",
        artifact_hash="a" * 64
    )
    assert att_res2["recorded"] is True

    fin_res = await svc.finalize_release(release_id=release_id)
    assert fin_res["recorded"] is True
    assert fin_res["decision"] == "VERIFIED"

    rel_data = await svc.get_release(release_id)
    assert rel_data["decision"] == "VERIFIED"
    assert rel_data["is_finalized"] is True


@pytest.mark.asyncio
async def test_anvil_blockchain_service_fallback():
    svc = AnvilBlockchainService()
    res = await svc.create_release(
        repository_url="https://github.com/example/safecalc",
        commit_sha="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        published_hash="a" * 64,
        builder_count=3,
        quorum_required=2
    )
    assert res["recorded"] is True
