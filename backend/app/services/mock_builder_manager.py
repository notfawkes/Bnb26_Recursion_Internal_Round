import base64
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.schemas.attestation import (
    BuildRequest, BuilderManagerResponse, BuilderResult, Attestation,
    BuilderInfo, SourceInfo, ArtifactInfo, BuildInfo, ResultInfo
)
from app.services.builder_service import builder_registry
from app.services.signature_service import SignatureService
from app.services.verification_service import to_uuid_str
from builders.manager.signing import sign_attestation, canonical_attestation_bytes


class MockBuilderManager:
    """
    Mock implementation of BuilderManager (Person 2).
    Consumes exact BuildRequest (release_id, repository_url, commit_sha, build_config_id, builders)
    and produces BuilderManagerResponse containing BuilderResult items with valid signed Attestations.
    """

    def __init__(self, key_directory: Path = Path("builders/keys")):
        self.key_directory = key_directory
        self._scenario: str = "NORMAL"  # NORMAL, ONE_DISAGREE, STRICT_DISAGREE, WRONG_QUORUM, INVALID_SIGNATURE, ALL_DIFFERENT
        self._custom_response: Optional[BuilderManagerResponse] = None
        self._override_published_hash: Optional[str] = None
        self._override_artifact_name: Optional[str] = None

    def set_scenario(self, scenario: str, published_hash: Optional[str] = None, artifact_name: Optional[str] = None) -> None:
        """Sets the active mock build scenario."""
        self._scenario = scenario.upper()
        self._custom_response = None
        if published_hash:
            self._override_published_hash = published_hash
        if artifact_name:
            self._override_artifact_name = artifact_name

    def set_custom_response(self, response: BuilderManagerResponse) -> None:
        """Injects a custom response directly."""
        self._custom_response = response

    async def run_builders(self, build_request: BuildRequest) -> BuilderManagerResponse:
        """Runs mock builders and returns generated BuilderManagerResponse."""
        if self._custom_response is not None:
            return self._custom_response

        builder_ids = [b.lower().strip() for b in build_request.builders]
        count = len(builder_ids)

        default_hash = self._override_published_hash or "a" * 64
        alternate_hash = "b" * 64
        third_hash = "c" * 64

        hashes: List[str] = []

        if self._scenario in ("NORMAL", "VERIFIED"):
            hashes = [default_hash] * count
        elif self._scenario in ("ONE_DISAGREE", "STRICT_DISAGREE"):
            # First N-1 produce default_hash, last produces alternate_hash
            hashes = [default_hash] * max(1, count - 1) + [alternate_hash]
        elif self._scenario == "WRONG_QUORUM":
            # Majority produce alternate_hash, last produces default_hash
            hashes = [alternate_hash] * max(1, count - 1) + [default_hash]
        elif self._scenario == "ALL_DIFFERENT":
            # Each builder produces a different hash
            distinct = [default_hash, alternate_hash, third_hash]
            hashes = distinct[:count] if count <= len(distinct) else distinct + ["d" * 64] * (count - len(distinct))
        else:
            hashes = [default_hash] * count

        builder_results: List[BuilderResult] = []
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        artifact_name = self._override_artifact_name or "safecalc.tar.gz"
        canonical_release_id = to_uuid_str(build_request.release_id)

        for i, b_id in enumerate(builder_ids):
            keypair = builder_registry.get_test_keypair(b_id)
            if not keypair:
                pubkey_hex = "0" * 64
                wallet = "0x" + "0" * 40
                priv_key = None
            else:
                priv_key, pubkey_hex = keypair
                builder_info = builder_registry.get_builder(b_id)
                wallet = builder_info["wallet_address"] if builder_info else "0x" + "0" * 40

            att_hash = hashes[i] if i < len(hashes) else default_hash

            att_dict = {
                "builder": {
                    "id": b_id,
                    "public_key": pubkey_hex,
                    "wallet_address": wallet
                },
                "source": {
                    "repository": build_request.repository_url,
                    "commit": build_request.commit_sha
                },
                "artifact": {
                    "name": artifact_name,
                    "sha256": att_hash
                },
                "build": {
                    "environment": "ubuntu:24.04",
                    "command": "make"
                },
                "result": {
                    "tests_passed": True
                },
                "timestamp": timestamp,
                "signature": ""
            }

            # Also create Person 2 signed_attestation envelope
            p2_attestation = {
                "schema_version": "v1",
                "release_id": canonical_release_id,
                "builder_id": b_id,
                "public_key_id": f"{b_id}-key-v1",
                "source": {
                    "repository_url": build_request.repository_url,
                    "commit_sha": build_request.commit_sha
                },
                "build": {
                    "config_id": build_request.build_config_id,
                    "image_id": "quorum-python-package-v1:local",
                    "source_date_epoch": 1700000000,
                    "status": "SUCCESS"
                },
                "artifact": {
                    "path": f"dist/{artifact_name}",
                    "algorithm": "sha256",
                    "digest": att_hash,
                    "size_bytes": 1000
                }
            }

            key_file = self.key_directory / f"{b_id}-key-v1.pem"
            signed_env = None

            if priv_key and (self._scenario != "INVALID_SIGNATURE" or i != 1):
                canonical_bytes = SignatureService.construct_canonical_payload(att_dict)
                sig_bytes = priv_key.sign(canonical_bytes)
                att_dict["signature"] = sig_bytes.hex()

                if key_file.exists():
                    signed_env = sign_attestation(p2_attestation, key_file)
                else:
                    raw_sig = priv_key.sign(canonical_attestation_bytes(p2_attestation))
                    signed_env = {
                        "attestation": p2_attestation,
                        "public_key_id": f"{b_id}-key-v1",
                        "signature_algorithm": "ed25519",
                        "canonicalization": "quorum-json-v1",
                        "signature": base64.b64encode(raw_sig).decode("ascii")
                    }
            else:
                att_dict["signature"] = "f" * 128
                signed_env = {
                    "attestation": p2_attestation,
                    "public_key_id": f"{b_id}-key-v1",
                    "signature_algorithm": "ed25519",
                    "canonicalization": "quorum-json-v1",
                    "signature": base64.b64encode(b"invalid_signature_bytes_here_1234567890abcdef1234567890abcdef").decode("ascii")
                }

            attestation_obj = Attestation(**att_dict)

            builder_results.append(
                BuilderResult(
                    builder_id=b_id,
                    status="SUCCESS",
                    artifact_name=artifact_name,
                    artifact_sha256=att_hash,
                    attestation=attestation_obj,
                    signed_attestation=signed_env
                )
            )

        return BuilderManagerResponse(
            release_id=build_request.release_id,
            results=builder_results
        )
