import os
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from app.config import settings

DEFAULT_ANVIL_ACCOUNTS = {
    "builder-a": {
        "wallet": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "eth_key": "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
    },
    "builder-b": {
        "wallet": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
        "eth_key": "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
    },
    "builder-c": {
        "wallet": "0x90F79bf6EB2c4f870365E785982E1f101E93b906",
        "eth_key": "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
    },
    "builder-d": {
        "wallet": "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",
        "eth_key": "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",
    },
}


class BuilderRegistryService:
    """
    Registry and identity verification service for authorized builders.
    Stores trusted builder public keys, private keys, and Ethereum wallet addresses from settings/env/PEM files.
    """

    def __init__(self, key_directory: Path = Path("builders/keys")):
        self.key_directory = key_directory
        # Maps builder_id -> dict with details
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._test_private_keys: Dict[str, ed25519.Ed25519PrivateKey] = {}
        self._ethereum_private_keys: Dict[str, str] = {}
        self._initialize_builders()

    def _initialize_builders(self) -> None:
        builder_configs = [
            ("builder-a", settings.BUILDER_A_WALLET, settings.BUILDER_A_ETH_KEY),
            ("builder-b", settings.BUILDER_B_WALLET, settings.BUILDER_B_ETH_KEY),
            ("builder-c", settings.BUILDER_C_WALLET, settings.BUILDER_C_ETH_KEY),
            ("builder-d", settings.BUILDER_D_WALLET, settings.BUILDER_D_ETH_KEY),
        ]

        for b_id, wallet, eth_priv in builder_configs:
            # Fall back to default local Anvil credentials if not configured in env
            default_acc = DEFAULT_ANVIL_ACCOUNTS.get(b_id, {})
            effective_wallet = wallet if wallet else default_acc.get("wallet", "0x" + "0" * 40)
            effective_eth_key = eth_priv if eth_priv else default_acc.get("eth_key", "")

            pub_pem_file = self.key_directory / f"{b_id}-key-v1.pub.pem"
            priv_pem_file = self.key_directory / f"{b_id}-key-v1.pem"

            priv_key: Optional[ed25519.Ed25519PrivateKey] = None
            pub_pem_bytes: Optional[bytes] = None
            pub_hex: str = ""

            if pub_pem_file.exists():
                pub_pem_bytes = pub_pem_file.read_bytes()
                try:
                    loaded_pub = serialization.load_pem_public_key(pub_pem_bytes)
                    if isinstance(loaded_pub, ed25519.Ed25519PublicKey):
                        pub_hex = loaded_pub.public_bytes_raw().hex()
                except Exception:
                    pass

            if priv_pem_file.exists():
                try:
                    loaded_priv = serialization.load_pem_private_key(priv_pem_file.read_bytes(), password=None)
                    if isinstance(loaded_priv, ed25519.Ed25519PrivateKey):
                        priv_key = loaded_priv
                        if not pub_hex:
                            pub_hex = priv_key.public_key().public_bytes_raw().hex()
                        if not pub_pem_bytes:
                            pub_pem_bytes = priv_key.public_key().public_bytes(
                                encoding=serialization.Encoding.PEM,
                                format=serialization.PublicFormat.SubjectPublicKeyInfo
                            )
                except Exception:
                    pass

            # If no key on disk, generate deterministic fallback key for test environments
            if not priv_key or not pub_hex:
                seed = hashlib.sha256(f"seed_secret_{b_id}".encode()).digest()
                priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
                pub_hex = priv_key.public_key().public_bytes_raw().hex()
                pub_pem_bytes = priv_key.public_key().public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )

            self.register_builder(
                builder_id=b_id,
                public_key=pub_hex,
                wallet_address=effective_wallet,
                private_key=priv_key,
                eth_private_key=effective_eth_key,
                public_key_pem=pub_pem_bytes,
                public_key_id=f"{b_id}-key-v1"
            )

    def register_builder(
        self,
        builder_id: str,
        public_key: str,
        wallet_address: str,
        private_key: Optional[ed25519.Ed25519PrivateKey] = None,
        eth_private_key: Optional[str] = None,
        public_key_pem: Optional[bytes] = None,
        public_key_id: Optional[str] = None
    ) -> None:
        """Register or update an authorized builder."""
        b_id = builder_id.lower().strip()
        self._registry[b_id] = {
            "builder_id": b_id,
            "public_key": public_key.lower(),
            "public_key_pem": public_key_pem,
            "public_key_id": public_key_id or f"{b_id}-key-v1",
            "wallet_address": wallet_address
        }
        if private_key:
            self._test_private_keys[b_id] = private_key
        if eth_private_key:
            self._ethereum_private_keys[b_id] = eth_private_key

    def get_authorized_builders(self) -> List[str]:
        return list(self._registry.keys())

    def get_builder(self, builder_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve registered builder info."""
        return self._registry.get(builder_id.lower().strip())

    def get_trusted_public_key_pem(self, builder_id: str) -> Optional[bytes]:
        """Retrieve trusted Ed25519 public key PEM for the given builder ID."""
        info = self.get_builder(builder_id)
        if not info:
            return None
        return info.get("public_key_pem")

    def is_authorized(self, builder_id: str, public_key: Optional[str] = None) -> bool:
        """
        Verify if the builder ID is authorized and (if provided) matches the trusted key.
        Accepts public key hex, public key ID, or PEM string.
        """
        builder_info = self.get_builder(builder_id)
        if not builder_info:
            return False

        if not public_key:
            return True

        pk_clean = public_key.strip()
        expected_pk_id = builder_info.get("public_key_id", "")
        if pk_clean == expected_pk_id:
            return True

        expected_pk_hex = builder_info.get("public_key", "").lower()
        if pk_clean.lower() == expected_pk_hex:
            return True

        pem_bytes = builder_info.get("public_key_pem")
        if pem_bytes and pk_clean.encode() in pem_bytes:
            return True

        return False

    def get_test_keypair(self, builder_id: str) -> Optional[Tuple[ed25519.Ed25519PrivateKey, str]]:
        """Get stored test private key and public key hex for builder signing."""
        b_id = builder_id.lower().strip()
        priv_key = self._test_private_keys.get(b_id)
        if not priv_key:
            return None
        pubkey_hex = priv_key.public_key().public_bytes_raw().hex()
        return priv_key, pubkey_hex

    def get_ethereum_private_key(self, builder_id: str) -> Optional[str]:
        """Get Ethereum private key for sending on-chain transactions as this builder."""
        return self._ethereum_private_keys.get(builder_id.lower().strip())


# Singleton builder registry instance pre-populated with configured builders
builder_registry = BuilderRegistryService()
