import re
from typing import Dict, Any, Union
from app.schemas.attestation import Attestation, BuilderResult
from app.schemas.verification import BuilderVerificationResult
from app.schemas.release import ReleaseResponse
from app.services.signature_service import SignatureService
from app.services.builder_service import builder_registry
from app.core.enums import BuilderStatus

HEX_64_REGEX = re.compile(r"^[0-9a-fA-F]{64}$")


class VerificationService:
    """
    Attestation & Builder Result Verification Service.
    Verifies signatures, builder identity, source matching, and evidence formatting.
    """

    @classmethod
    def verify_builder_result(
        cls,
        builder_result: Union[BuilderResult, Dict[str, Any]],
        expected_release: ReleaseResponse
    ) -> BuilderVerificationResult:
        """
        Validates a BuilderResult against a given release context.
        Returns detailed BuilderVerificationResult.
        """
        if isinstance(builder_result, BuilderResult):
            b_id = builder_result.builder_id.lower().strip()
            status_str = builder_result.status
            art_name = builder_result.artifact_name
            art_hash = builder_result.artifact_sha256.lower().strip()
            att_dict = builder_result.attestation.model_dump()
        else:
            b_res_dict = dict(builder_result)
            b_id = str(b_res_dict.get("builder_id", "")).lower().strip()
            status_str = str(b_res_dict.get("status", "SUCCESS"))
            art_name = str(b_res_dict.get("artifact_name", ""))
            art_hash = str(b_res_dict.get("artifact_sha256", "")).lower().strip()
            att_dict = b_res_dict.get("attestation", {})

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
        signature_valid = SignatureService.verify_attestation_signature(att_dict)

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
