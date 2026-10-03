from typing import Protocol
from app.schemas.attestation import BuildRequest, BuilderManagerResponse


class BuilderManager(Protocol):
    """
    Protocol/Interface for Builder Manager (Person 2).
    Person 2 builds the pinned commit independently and returns BuilderManagerResponse.
    """

    async def run_builders(
        self,
        build_request: BuildRequest
    ) -> BuilderManagerResponse:
        ...
