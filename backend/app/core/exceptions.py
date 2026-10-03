class QuorumException(Exception):
    """Base exception for Quorum backend."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ReleaseNotFoundError(QuorumException):
    def __init__(self, release_id: str):
        super().__init__(f"Release with ID '{release_id}' was not found.", status_code=404)


class InvalidQuorumPolicyError(QuorumException):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class InvalidCommitError(QuorumException):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class InvalidRepositoryError(QuorumException):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class InvalidAttestationError(QuorumException):
    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class DuplicateReleaseError(QuorumException):
    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class BlockchainServiceError(QuorumException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class BuilderServiceError(QuorumException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)
