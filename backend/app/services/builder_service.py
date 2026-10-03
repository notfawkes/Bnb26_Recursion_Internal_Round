import hashlib
from typing import Dict, Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from app.config import settings


class BuilderRegistryService:
    """
    Registry and identity verification service for authorized builders.
    Stores builder public keys, private keys, and Ethereum wallet addresses from settings/env.
    """

    def __init__(self):
        # Maps builder_id -> {"public_key": hex, "wallet_address": 0x...}
        self._registry: Dict[str, Dict[str, str]] = {}
        # Private keys store for test/mock builders generation
        self._test_private_keys: Dict[str, ed25519.Ed25519PrivateKey] = {}
        self._ethereum_private_keys: Dict[str, str] = {}

    def register_builder(
        self,
        builder_id: str,
        public_key: str,
        wallet_address: str,
        private_key: Optional[ed25519.Ed25519PrivateKey] = None,
        eth_private_key: Optional[str] = None
    ) -> None:
        """Register or update an authorized builder."""
        b_id = builder_id.lower().strip()
        self._registry[b_id] = {
            "public_key": public_key.lower(),
            "wallet_address": wallet_address
        }
        if private_key:
            self._test_private_keys[b_id] = private_key
        if eth_private_key:
            self._ethereum_private_keys[b_id] = eth_private_key

    def get_builder(self, builder_id: str) -> Optional[Dict[str, str]]:
        """Retrieve registered builder info."""
        return self._registry.get(builder_id.lower().strip())

    def is_authorized(self, builder_id: str, public_key: str) -> bool:
        """
        Verify if the submitted builder ID exists and its public key matches the authorized registry.
        """
        builder_info = self.get_builder(builder_id)
        if not builder_info:
            return False
        return builder_info["public_key"].lower() == public_key.lower()

    def get_test_keypair(self, builder_id: str) -> Optional[Tuple[ed25519.Ed25519PrivateKey, str]]:
        """Get stored test private key and public key hex for mock builder signing."""
        b_id = builder_id.lower().strip()
        priv_key = self._test_private_keys.get(b_id)
        if not priv_key:
            return None
        pubkey_hex = priv_key.public_key().public_bytes_raw().hex()
        return priv_key, pubkey_hex

    def get_ethereum_private_key(self, builder_id: str) -> Optional[str]:
        """Get Ethereum private key for sending on-chain transactions as this builder."""
        return self._ethereum_private_keys.get(builder_id.lower().strip())


# Singleton builder registry instance pre-populated with configured test builders
builder_registry = BuilderRegistryService()

def _initialize_default_test_builders():
    test_builders = [
        ("builder-a", settings.BUILDER_A_WALLET, settings.BUILDER_A_ETH_KEY),
        ("builder-b", settings.BUILDER_B_WALLET, settings.BUILDER_B_ETH_KEY),
        ("builder-c", settings.BUILDER_C_WALLET, settings.BUILDER_C_ETH_KEY),
        ("builder-d", settings.BUILDER_D_WALLET, settings.BUILDER_D_ETH_KEY),
    ]
    for b_id, wallet, eth_priv in test_builders:
        # Generate deterministic 32-byte seed from builder_id
        seed = hashlib.sha256(f"seed_secret_{b_id}".encode()).digest()
        priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
        pub_bytes = priv_key.public_key().public_bytes_raw()
        pub_hex = pub_bytes.hex()
        builder_registry.register_builder(b_id, pub_hex, wallet, priv_key, eth_priv)

_initialize_default_test_builders()
