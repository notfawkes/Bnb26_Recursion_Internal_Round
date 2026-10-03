import datetime
from typing import List, Dict, Any, Optional
from app.schemas.attestation import (
    BuildRequest, BuilderManagerResponse, BuilderResult, Attestation,
    BuilderInfo, SourceInfo, ArtifactInfo, BuildInfo, ResultInfo
)
from app.services.builder_service import builder_registry
from app.services.signature_service import SignatureService


class MockBuilderManager:
    """
    Mock implementation of BuilderManager (Person 2).
    Consumes exact BuildRequest (release_id, repository_url, commit_sha, build_config_id, builders)
    and produces BuilderManagerResponse containing BuilderResult items with valid signed Attestations.
    """

    def __init__(self):
        self._scenario: str = "NORMAL"  # NORMAL, ONE_DISAGREE, STRICT_DISAGREE, WRONG_QUORUM, INVALID_SIGNATURE
        self._custom_response: Optional[BuilderManagerResponse] = None
        self._override_published_hash: Optional[str] = None

    def set_scenario(self, scenario: str, published_hash: Optional[str] = None) -> None:
        """Sets the active mock build scenario."""
        self._scenario = scenario.upper()
        self._custom_response = None
        if published_hash:
            self._override_published_hash = published_hash

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

        hashes: List[str] = []

        if self._scenario in ("NORMAL", "VERIFIED"):
            hashes = [default_hash] * count
        elif self._scenario in ("ONE_DISAGREE", "STRICT_DISAGREE"):
            # First N-1 produce default_hash, last produces alternate_hash
            hashes = [default_hash] * max(1, count - 1) + [alternate_hash]
        elif self._scenario == "WRONG_QUORUM":
            # Majority produce alternate_hash, last produces default_hash
            hashes = [alternate_hash] * max(1, count - 1) + [default_hash]
        else:
            hashes = [default_hash] * count

        builder_results: List[BuilderResult] = []
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        artifact_name = "safecalc.tar.gz"

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

            if priv_key and (self._scenario != "INVALID_SIGNATURE" or i != 1):
                canonical_bytes = SignatureService.construct_canonical_payload(att_dict)
                sig_bytes = priv_key.sign(canonical_bytes)
                att_dict["signature"] = sig_bytes.hex()
            else:
                att_dict["signature"] = "f" * 128

            attestation_obj = Attestation(**att_dict)

            builder_results.append(
                BuilderResult(
                    builder_id=b_id,
                    status="SUCCESS",
                    artifact_name=artifact_name,
                    artifact_sha256=att_hash,
                    attestation=attestation_obj
                )
            )

        return BuilderManagerResponse(
            release_id=build_request.release_id,
            results=builder_results
        )
