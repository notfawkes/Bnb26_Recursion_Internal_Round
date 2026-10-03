import re
import uuid
from typing import Dict, Any, Union, Optional
from app.schemas.attestation import Attestation, BuilderResult
from app.schemas.verification import BuilderVerificationResult
from app.schemas.release import ReleaseResponse
from app.services.signature_service import SignatureService
from app.services.builder_service import builder_registry
from app.core.enums import BuilderStatus

HEX_64_REGEX = re.compile(r"^[0-9a-fA-F]{64}$")


def to_uuid_str(val: Any) -> str:
    """Normalize any release ID representation (int, str, uuid) to canonical UUID string."""
    s = str(val).strip()
    try:
        return str(uuid.UUID(s))
    except (ValueError, AttributeError):
        try:
            return str(uuid.UUID(int=int(s)))
        except (ValueError, AttributeError):
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, s))


class VerificationService:
    """
    Attestation & Builder Result Verification Service.
    Verifies Ed25519 signatures against trusted backend keys,
    verifies builder identity, source matching, commit matching, and evidence integrity.
    """

    @classmethod
    def verify_builder_result(
        cls,
        builder_result: Union[BuilderResult, Dict[str, Any]],
        expected_release: ReleaseResponse
    ) -> BuilderVerificationResult:
        """
        Validates a BuilderResult against a given release context.
        Handles both Person 2 signed envelopes and Person 3 mock attestations.
        """
        if isinstance(builder_result, BuilderResult):
            b_id = builder_result.builder_id.lower().strip()
            status_str = builder_result.status
            art_name = builder_result.artifact_name
            art_hash = builder_result.artifact_sha256.lower().strip()
            signed_env = builder_result.signed_attestation
            att_dict = builder_result.attestation.model_dump() if builder_result.attestation else None
        else:
            b_res_dict = dict(builder_result)
            b_id = str(b_res_dict.get("builder_id", "")).lower().strip()
            status_str = str(b_res_dict.get("status", "SUCCESS"))
            art_name = str(b_res_dict.get("artifact_name", ""))
            art_hash = str(b_res_dict.get("artifact_sha256", "")).lower().strip()
            signed_env = b_res_dict.get("signed_attestation")
            att_dict = b_res_dict.get("attestation")
            if isinstance(att_dict, Attestation):
                att_dict = att_dict.model_dump()

        # ==========================================================
        # Case A: Person 2 Signed Attestation Envelope
        # ==========================================================
        if signed_env and isinstance(signed_env, dict) and "attestation" in signed_env:
            envelope = signed_env
            inner_att = envelope.get("attestation", {})
            env_key_id = envelope.get("public_key_id", "")

            inner_b_id = str(inner_att.get("builder_id", b_id)).lower().strip()
            inner_key_id = inner_att.get("public_key_id", "")
            inner_rel_id = inner_att.get("release_id", "")
            source_info = inner_att.get("source", {})
            build_info = inner_att.get("build", {})
            artifact_info = inner_att.get("artifact", {})

            # 1. Identity & Key ID check (Must come from backend configuration)
            identity_valid = (
                inner_b_id == b_id
                and b_id in builder_registry.get_authorized_builders()
                and env_key_id == inner_key_id == f"{b_id}-key-v1"
                and builder_registry.is_authorized(b_id, env_key_id)
            )

            # 2. Cryptographic signature check against trusted public key
            trusted_pem = builder_registry.get_trusted_public_key_pem(b_id)
            signature_valid = False
            if trusted_pem and identity_valid:
                signature_valid = SignatureService.verify_envelope(envelope, trusted_pem)

            # 3. Source repository check
            att_repo = str(source_info.get("repository_url", "")).strip()
            exp_repo = expected_release.repository_url.strip()
            source_match = bool(
                att_repo == exp_repo
                or att_repo.rstrip(".git") == exp_repo.rstrip(".git")
            )

            # 4. Source commit check
            att_commit = str(source_info.get("commit_sha", "")).strip().lower()
            exp_commit = expected_release.commit_sha.strip().lower()
            commit_match = bool(att_commit == exp_commit)

            # 5. Release ID check
            rel_id_match = to_uuid_str(inner_rel_id) == to_uuid_str(expected_release.release_id)

            # 6. Build config & build status check
            cfg_match = build_info.get("config_id") == expected_release.build_config_id
            build_status_ok = (status_str == "SUCCESS" and build_info.get("status") == "SUCCESS")

            # 7. Artifact algorithm & digest check
            digest = str(artifact_info.get("digest", "")).lower().strip()
            effective_hash = art_hash if art_hash else digest
            algorithm_ok = artifact_info.get("algorithm") == "sha256"
            hash_valid = bool(
                algorithm_ok
                and HEX_64_REGEX.match(effective_hash)
                and effective_hash == digest
            )

            # Overall validity check
            valid = (
                identity_valid
                and signature_valid
                and source_match
                and commit_match
                and rel_id_match
                and cfg_match
                and build_status_ok
                and hash_valid
            )

            art_path = str(artifact_info.get("path", art_name))

            return BuilderVerificationResult(
                builder_id=b_id,
                status=status_str,
                artifact_name=art_path or expected_release.artifact_name,
                artifact_sha256=effective_hash if hash_valid else "INVALID_HASH",
                signature_valid=signature_valid,
                identity_valid=identity_valid,
                source_match=source_match,
                commit_match=commit_match,
                valid=valid,
                status_detail=BuilderStatus.AGREE if valid else BuilderStatus.INVALID
            )

        # ==========================================================
        # Case B: Person 3 Mock Attestation
        # ==========================================================
        if att_dict is None:
            att_dict = {}

        builder_info = att_dict.get("builder", {})
        public_key = str(builder_info.get("public_key", ""))

        source_info = att_dict.get("source", {})
        att_repo = str(source_info.get("repository", "")).strip()
        att_commit = str(source_info.get("commit", "")).strip().lower()

        artifact_info = att_dict.get("artifact", {})
        att_art_name = str(artifact_info.get("name", "")).strip()
        att_art_hash = str(artifact_info.get("sha256", "")).strip().lower()

        timestamp = att_dict.get("timestamp")
        build_info = att_dict.get("build")

        # 1. Identity Verification
        identity_valid = builder_registry.is_authorized(b_id, public_key)

        # 2. Signature Verification
        trusted_pem = builder_registry.get_trusted_public_key_pem(b_id)
        signature_valid = SignatureService.verify_attestation_signature(att_dict, trusted_pem)

        # 3. Source Repository Verification
        exp_repo = expected_release.repository_url.strip()
        source_match = att_repo == exp_repo or att_repo.rstrip(".git") == exp_repo.rstrip(".git")

        # 4. Source Commit Verification
        exp_commit = expected_release.commit_sha.strip().lower()
        commit_match = att_commit == exp_commit

        # 5. Artifact Name Matching
        exp_artifact_name = expected_release.artifact_name.strip()
        artifact_name_match = (art_name == exp_artifact_name or att_art_name == exp_artifact_name)

        # 6. Artifact Hash Format Validation & Integrity
        hash_valid = bool(HEX_64_REGEX.match(art_hash)) and art_hash == att_art_hash

        # 7. Metadata completeness
        metadata_valid = bool(timestamp) and bool(build_info) and status_str == "SUCCESS"

        # Overall validity check
        valid = (
            identity_valid
            and signature_valid
            and source_match
            and commit_match
            and artifact_name_match
            and hash_valid
            and metadata_valid
        )

        return BuilderVerificationResult(
            builder_id=b_id,
            status=status_str,
            artifact_name=art_name or expected_release.artifact_name,
            artifact_sha256=art_hash if hash_valid else "INVALID_HASH",
            signature_valid=signature_valid,
            identity_valid=identity_valid,
            source_match=source_match,
            commit_match=commit_match,
            valid=valid,
            status_detail=BuilderStatus.AGREE if valid else BuilderStatus.INVALID
        )

    @classmethod
    def verify_attestation(
        cls,
        attestation: Union[Attestation, Dict[str, Any]],
        expected_release: ReleaseResponse
    ) -> BuilderVerificationResult:
        """Convenience wrapper for raw attestation objects."""
        if isinstance(attestation, Attestation):
            att_dict = attestation.model_dump()
        else:
            att_dict = dict(attestation)

        b_id = att_dict.get("builder", {}).get("id", "unknown-builder")
        art_info = att_dict.get("artifact", {})
        art_name = art_info.get("name", expected_release.artifact_name)
        art_hash = art_info.get("sha256", "")

        b_result = BuilderResult(
            builder_id=b_id,
            status="SUCCESS",
            artifact_name=art_name,
            artifact_sha256=art_hash,
            attestation=Attestation(**att_dict)
        )
        return cls.verify_builder_result(b_result, expected_release)
