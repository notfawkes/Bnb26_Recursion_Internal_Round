from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"

    # Blockchain RPC & Contract Settings (loaded from .env)
    BLOCKCHAIN_RPC_URL: str = "http://127.0.0.1:8545"
    BLOCKCHAIN_CHAIN_ID: int = 31337
    BLOCKCHAIN_CONTRACT_ADDRESS: str = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
    BLOCKCHAIN_ABI_PATH: str = "blockchain/deployments/QuorumVerifier.abi.json"
    BLOCKCHAIN_DEPLOYMENT_PATH: str = "blockchain/deployments/quorum-verifier.json"
    BLOCKCHAIN_PRIVATE_KEY: str = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

    # Builder Wallet & Private Key Credentials (loaded from .env)
    BUILDER_A_WALLET: str = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    BUILDER_A_ETH_KEY: str = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"

    BUILDER_B_WALLET: str = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
    BUILDER_B_ETH_KEY: str = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"

    BUILDER_C_WALLET: str = "0x90F79bf6EB2c4f870365E785982E1f101E93b906"
    BUILDER_C_ETH_KEY: str = "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6"

    BUILDER_D_WALLET: str = "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65"
    BUILDER_D_ETH_KEY: str = "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a"

    # Feature flags
    USE_MOCK_BUILDERS: bool = True
    USE_MOCK_BLOCKCHAIN: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
