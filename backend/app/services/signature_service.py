import json
from typing import Dict, Any, Union
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
from app.schemas.attestation import Attestation


class SignatureService:
    """
    Ed25519 signature verification service.
    Follows deterministic canonical serialization of the attestation payload.
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
    def verify_attestation_signature(
        cls,
        attestation: Union[Attestation, Dict[str, Any]]
    ) -> bool:
        """
        Verifies the Ed25519 signature of an attestation.
        Returns True if valid, False otherwise.
        """
        if isinstance(attestation, Attestation):
            attestation_dict = attestation.model_dump()
        else:
            attestation_dict = dict(attestation)

        signature_hex = attestation_dict.get("signature")
        if not signature_hex or not isinstance(signature_hex, str):
            return False

        builder_info = attestation_dict.get("builder", {})
        pubkey_hex = builder_info.get("public_key")
        if not pubkey_hex or not isinstance(pubkey_hex, str):
            return False

        try:
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
