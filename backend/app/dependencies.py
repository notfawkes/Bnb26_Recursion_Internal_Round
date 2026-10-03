from fastapi import Depends
from app.config import settings
from app.services.mock_builder_manager import MockBuilderManager
from app.services.blockchain_service import MockBlockchainService, AnvilBlockchainService
from app.interfaces.builder_manager import BuilderManager
from app.interfaces.blockchain import BlockchainService
from app.services.release_service import ReleaseService

# Global service singletons
mock_builder_manager = MockBuilderManager()
mock_blockchain_service = MockBlockchainService()
anvil_blockchain_service = AnvilBlockchainService()


def get_builder_manager() -> BuilderManager:
    """
    Dependency for BuilderManager.
    Defaults to MockBuilderManager for Person 3 testing/dev.
    Replaceable by Person 2's real Builder Manager implementation.
    """
    return mock_builder_manager


def get_blockchain_service() -> BlockchainService:
    """
    Dependency for BlockchainService.
    Switches between Mock and Anvil based on settings.USE_MOCK_BLOCKCHAIN.
    """
    if settings.USE_MOCK_BLOCKCHAIN:
        return mock_blockchain_service
    return anvil_blockchain_service


def get_release_service(
    builder_mgr: BuilderManager = Depends(get_builder_manager),
    blockchain_svc: BlockchainService = Depends(get_blockchain_service)
) -> ReleaseService:
    """Dependency injection for ReleaseService."""
    return ReleaseService(
        builder_manager=builder_mgr,
        blockchain_service=blockchain_svc
    )
