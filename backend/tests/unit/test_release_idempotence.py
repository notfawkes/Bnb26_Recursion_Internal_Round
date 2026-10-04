import asyncio

from app.schemas.release import ReleaseCreate
from app.services.blockchain_service import MockBlockchainService
from app.services.mock_builder_manager import MockBuilderManager
from app.services.release_service import ReleaseService


PAYLOAD = ReleaseCreate(
    repository_url="https://github.com/example/idempotent-demo",
    commit_sha="a" * 40,
    build_config_id="python-package-v1",
    published_hash="a" * 64,
    artifact_name="demo.whl",
    builder_count=3,
    quorum_required=2,
    reuse_existing=True,
)


def test_duplicate_release_and_verification_reuse_existing_result() -> None:
    async def exercise() -> None:
        manager = MockBuilderManager()
        blockchain = MockBlockchainService()
        service = ReleaseService(manager, blockchain)
        calls = 0
        original_run = manager.run_builders

        async def counted_run(request):
            nonlocal calls
            calls += 1
            return await original_run(request)

        manager.run_builders = counted_run

        first_release = await service.create_release(PAYLOAD)
        first_result = await service.verify_release(first_release.release_id)
        second_release = await service.create_release(PAYLOAD)
        second_result = await service.verify_release(second_release.release_id)

        assert first_release.reused is False
        assert second_release.reused is True
        assert second_release.release_id == first_release.release_id
        assert first_result.cache_hit is False
        assert second_result.cache_hit is True
        assert calls == 1

    asyncio.run(exercise())
