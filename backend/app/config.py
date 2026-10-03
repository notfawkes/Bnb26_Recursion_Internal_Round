from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./quorum.db"

    # Blockchain RPC & Contract Settings (loaded from .env)
    BLOCKCHAIN_RPC_URL: str = "http://127.0.0.1:8545"
    BLOCKCHAIN_CHAIN_ID: int = 31337
    BLOCKCHAIN_CONTRACT_ADDRESS: str = ""
    BLOCKCHAIN_ABI_PATH: str = "blockchain/deployments/QuorumVerifier.abi.json"
    BLOCKCHAIN_DEPLOYMENT_PATH: str = "blockchain/deployments/quorum-verifier.json"
    BLOCKCHAIN_PRIVATE_KEY: str = ""

    # Builder Wallet & Private Key Credentials (loaded from .env)
    BUILDER_A_WALLET: str = ""
    BUILDER_A_ETH_KEY: str = ""

    BUILDER_B_WALLET: str = ""
    BUILDER_B_ETH_KEY: str = ""

    BUILDER_C_WALLET: str = ""
    BUILDER_C_ETH_KEY: str = ""

    BUILDER_D_WALLET: str = ""
    BUILDER_D_ETH_KEY: str = ""

    # Feature flags
    USE_MOCK_BUILDERS: bool = True
    USE_MOCK_BLOCKCHAIN: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
