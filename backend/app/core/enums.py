from enum import Enum


class ReleaseStatus(str, Enum):
    CREATED = "CREATED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    DISPUTED = "DISPUTED"


class Decision(str, Enum):
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    DISPUTED = "DISPUTED"


class BuilderStatus(str, Enum):
    AGREE = "AGREE"
    DISAGREE = "DISAGREE"
    INVALID = "INVALID"
