import json
import base64
from typing import Dict, Any, Union, Optional
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from app.schemas.attestation import Attestation
from builders.manager.signing import (
    canonical_attestation_bytes,
    verify_attestation_signature as builders_verify_signature
)


class SignatureService:
    """
    Ed25519 signature verification service.
    Supports both Person 2's canonical signed attestation envelopes
    and Person 3's internal canonical attestation payloads.
    """

    @staticmethod
    def construct_canonical_payload(attestation_dict: Dict[str, Any]) -> bytes:
        """
        Reconstruct canonical payload for signing/verification:
        1. Deep copy payload
        2. Remove the 'signature' key
        3. Serialize JSON with sorted keys and no unnecessary whitespace
        4. Encode to UTF-8
        """
        payload = dict(attestation_dict)
        payload.pop("signature", None)

        canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return canonical_json.encode('utf-8')

    @classmethod
    def verify_envelope(
        cls,
        envelope: Dict[str, Any],
        trusted_public_key_pem: bytes
    ) -> bool:
        """
        Verifies Person 2's signed_attestation envelope against trusted public key PEM.
        """
        try:
            return builders_verify_signature(envelope, trusted_public_key_pem)
        except Exception:
            return False

    @classmethod
    def verify_attestation_signature(
        cls,
        attestation: Union[Attestation, Dict[str, Any]],
        trusted_pubkey_bytes: Optional[bytes] = None
    ) -> bool:
        """
        Verifies the Ed25519 signature of an attestation.
        If trusted_pubkey_bytes (PEM or 32 raw bytes) is provided, uses it.
        Otherwise falls back to public_key in payload (only for legacy mock tests).
        """
        if isinstance(attestation, Attestation):
            attestation_dict = attestation.model_dump()
        else:
            attestation_dict = dict(attestation)

        # Check if this is a Person 2 envelope containing "attestation" and "signature"
        if "attestation" in attestation_dict and isinstance(attestation_dict["attestation"], dict):
            if trusted_pubkey_bytes:
                return cls.verify_envelope(attestation_dict, trusted_pubkey_bytes)
            return False

        signature_hex = attestation_dict.get("signature")
        if not signature_hex or not isinstance(signature_hex, str):
            return False

        try:
            public_key: Optional[Ed25519PublicKey] = None
            if trusted_pubkey_bytes:
                if b"BEGIN PUBLIC KEY" in trusted_pubkey_bytes:
                    loaded = serialization.load_pem_public_key(trusted_pubkey_bytes)
                    if isinstance(loaded, Ed25519PublicKey):
                        public_key = loaded
                elif len(trusted_pubkey_bytes) == 32:
                    public_key = Ed25519PublicKey.from_public_bytes(trusted_pubkey_bytes)

            if not public_key:
                builder_info = attestation_dict.get("builder", {})
                pubkey_hex = builder_info.get("public_key")
                if not pubkey_hex or not isinstance(pubkey_hex, str):
                    return False
                pubkey_bytes = bytes.fromhex(pubkey_hex)
                if len(pubkey_bytes) != 32:
                    return False
                public_key = Ed25519PublicKey.from_public_bytes(pubkey_bytes)

            signature_bytes = bytes.fromhex(signature_hex)
            if len(signature_bytes) != 64:
                return False

            canonical_payload = cls.construct_canonical_payload(attestation_dict)
            public_key.verify(signature_bytes, canonical_payload)
            return True
        except (ValueError, InvalidSignature, TypeError, Exception):
            return False
