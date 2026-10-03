from typing import Protocol, Dict, Any, List, Optional


class BlockchainService(Protocol):
    """
    Protocol/Interface for Blockchain Service.
    Person 1 provides the smart contract implementation on Anvil.
    Person 3 provides this interface, a Mock implementation, and an Anvil web3 adapter.
    """

    async def create_release(
        self,
        repository: str,
        commit: str,
        published_hash: str,
        builder_count: int,
        quorum_required: int
    ) -> Dict[str, Any]:
        """Record initial release configuration on-chain."""
        ...

    async def submit_attestation(
        self,
        release_id: str,
        builder_address: str,
        artifact_hash: str
    ) -> Dict[str, Any]:
        """Record individual builder attestation evidence on-chain."""
        ...

    async def finalize_release(
        self,
        release_id: str,
        decision: str,
        quorum_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """Finalize release status and record decision on-chain."""
        ...

    async def get_release(
        self,
        release_id: str
    ) -> Dict[str, Any]:
        """Query release details from blockchain."""
        ...

    async def get_attestations(
        self,
        release_id: str
    ) -> List[Dict[str, Any]]:
        """Query attestations recorded on blockchain for a release."""
        ...
