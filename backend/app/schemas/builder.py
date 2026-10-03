from pydantic import BaseModel, Field


class BuilderInfo(BaseModel):
    id: str = Field(..., description="Builder identifier, e.g. builder-A")
    public_key: str = Field(..., description="Builder Ed25519 public key in hex")
    wallet_address: str = Field(..., description="Builder Ethereum wallet address (0x...)")


class BuildInfo(BaseModel):
    environment: str = Field(default="ubuntu:24.04", description="Build environment image/OS")
    command: str = Field(default="make", description="Command used to build the artifact")


class ResultInfo(BaseModel):
    tests_passed: bool = Field(default=True, description="Whether internal verification tests passed")
