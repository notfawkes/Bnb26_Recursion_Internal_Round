import datetime
from typing import Dict, Any, List, Optional
from app.schemas.release import ReleaseCreate, ReleaseResponse
from app.schemas.verification import (
    VerificationResponse, LocalQuorumResult, BlockchainRecord, BuilderVerificationResult
)
from app.schemas.attestation import BuildRequest
from app.core.enums import ReleaseStatus, Decision
from app.core.exceptions import ReleaseNotFoundError, InvalidQuorumPolicyError
from app.services.repository_service import RepositoryService
from app.services.published_artifact_service import PublishedArtifactService
from app.services.verification_service import VerificationService
from app.services.quorum_service import QuorumService
from app.interfaces.builder_manager import BuilderManager
from app.interfaces.blockchain import BlockchainService


class ReleaseService:
    """
    Release Management and Verification Orchestration Service.
    Completely database-free: The blockchain is the single persistent source of truth.
    """

    def __init__(
        self,
        builder_manager: BuilderManager,
        blockchain_service: BlockchainService
    ):
        self.builder_manager = builder_manager
        self.blockchain_service = blockchain_service

    async def create_release(self, payload: ReleaseCreate) -> ReleaseResponse:
        """Creates a new Release record directly on the blockchain."""
        repo_url = payload.repository_url or payload.repository or ""
        commit_input = payload.commit_sha or payload.commit or ""

        # 1. Validate repository URL
        RepositoryService.validate_repository(repo_url)

        # 2. Validate & pin commit SHA
        pinned_commit = RepositoryService.validate_commit(repo_url, commit_input)

        # 3. Resolve published artifact SHA-256 hash
        published_hash = PublishedArtifactService.resolve_published_hash(
            published_hash=payload.published_hash,
            published_artifact=payload.published_artifact
        )

        # 4. Validate Quorum Policy
        if payload.quorum_required > payload.builder_count:
            raise InvalidQuorumPolicyError(
                f"quorum_required ({payload.quorum_required}) cannot exceed builder_count ({payload.builder_count})."
            )
        if payload.quorum_required <= 0 or payload.builder_count <= 0:
            raise InvalidQuorumPolicyError("builder_count and quorum_required must be at least 1.")

        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # 5. Call Blockchain Service to create release on-chain
        bc_create_res = await self.blockchain_service.create_release(
            repository_url=repo_url,
            commit_sha=pinned_commit,
            published_hash=published_hash,
            builder_count=payload.builder_count,
            quorum_required=payload.quorum_required,
            build_config_id=payload.build_config_id,
            artifact_name=payload.artifact_name
        )

        release_id = str(bc_create_res.get("release_id", "1"))

        return ReleaseResponse(
            release_id=release_id,
            repository_url=repo_url,
            repository=repo_url,
            commit_sha=pinned_commit,
            commit=pinned_commit,
            build_config_id=payload.build_config_id,
            published_hash=published_hash,
            artifact_name=payload.artifact_name,
            builder_count=payload.builder_count,
            quorum_required=payload.quorum_required,
            status=ReleaseStatus.CREATED,
            created_at=created_at
        )

    async def get_release(self, release_id: str) -> ReleaseResponse:
        """Retrieves release details directly from the blockchain state."""
        bc_rel = await self.blockchain_service.get_release(release_id)
        if not bc_rel or not bc_rel.get("repository_url"):
            raise ReleaseNotFoundError(release_id)

        dec_str = bc_rel.get("decision", "CREATED")
        try:
            rel_status = ReleaseStatus(dec_str)
        except ValueError:
            rel_status = ReleaseStatus.CREATED

        return ReleaseResponse(
            release_id=str(release_id),
            repository_url=bc_rel.get("repository_url", ""),
            repository=bc_rel.get("repository_url", ""),
            commit_sha=bc_rel.get("commit_sha", ""),
            commit=bc_rel.get("commit_sha", ""),
            build_config_id=bc_rel.get("build_config_id", "python-package-v1"),
            published_hash=bc_rel.get("published_hash", ""),
            artifact_name=bc_rel.get("artifact_name", "safecalc.tar.gz"),
            builder_count=bc_rel.get("builder_count", 3),
            quorum_required=bc_rel.get("quorum_required", 2),
            status=rel_status,
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )

    async def verify_release(self, release_id: str) -> VerificationResponse:
        """
        Runs complete updated database-free verification flow:
        1. Fetch release directly from blockchain
        2. Construct BuildRequest for Person 2 (NO published_hash!)
        3. Send BuildRequest to Person 2 Builder Manager
        4. Validate each builder attestation
        5. Calculate local expected quorum
        6. Submit valid builder attestations to blockchain using builder wallet (msg.sender)
        7. Finalize release on blockchain
        8. Read authoritative final decision directly from blockchain getRelease()
        9. Compare local expected vs blockchain decision
        10. Return structured API response with decision_source=BLOCKCHAIN
        """
        release = await self.get_release(release_id)

        # 1. Construct BuildRequest for Person 2 (NO published_hash!)
        builder_names = [f"builder-{'abcdefghijklmnopqrstuvwxyz'[i]}" for i in range(release.builder_count)]
        build_req = BuildRequest(
            release_id=str(release_id),
            repository_url=release.repository_url,
            commit_sha=release.commit_sha,
            build_config_id=release.build_config_id,
            builders=builder_names
        )

        # 2. Run Builder Manager
        builder_mgr_res = await self.builder_manager.run_builders(build_req)

        # 3. Validate Builder Results
        builder_results: List[BuilderVerificationResult] = []

        for b_res in builder_mgr_res.results:
            ver_res = VerificationService.verify_builder_result(b_res, release)
            builder_results.append(ver_res)

        # 4. Calculate Local Quorum Expectation
        local_decision, local_reason, quorum_res, final_builder_results = QuorumService.calculate_quorum(
            builder_results=builder_results,
            builder_count=release.builder_count,
            quorum_required=release.quorum_required,
            published_hash=release.published_hash
        )

        local_quorum_obj = LocalQuorumResult(
            achieved=quorum_res.achieved,
            agreement=quorum_res.agreement,
            quorum_hash=quorum_res.quorum_hash,
            expected_decision=local_decision
        )

        # 5. Submit Valid Builder Evidence to Blockchain
        attestation_txs: List[str] = []
        for b_res in final_builder_results:
            if b_res.valid:
                att_tx_res = await self.blockchain_service.submit_attestation(
                    release_id=release_id,
                    builder_id=b_res.builder_id,
                    artifact_hash=b_res.artifact_sha256
                )
                if att_tx_res.get("transaction_hash"):
                    attestation_txs.append(att_tx_res["transaction_hash"])

        # 6. Finalize Release on Blockchain
        fin_bc_res = await self.blockchain_service.finalize_release(release_id)
        finalize_tx = fin_bc_res.get("transaction_hash")

        # 7. Read Authoritative State from Blockchain
        bc_state = await self.blockchain_service.get_release(release_id)
        bc_published_hash = bc_state.get("published_hash") or release.published_hash
        bc_quorum_hash = bc_state.get("quorum_hash")
        bc_decision_str = bc_state.get("decision", local_decision.value)
        bc_is_finalized = bc_state.get("is_finalized", True)
        create_tx = bc_state.get("create_release_tx")

        try:
            bc_decision_enum = Decision(bc_decision_str)
        except ValueError:
            bc_decision_enum = local_decision

        # 8. Check Local vs Blockchain Consistency
        blockchain_consistent = (
            (local_decision.value == bc_decision_str)
            and (local_quorum_obj.quorum_hash == bc_quorum_hash if local_quorum_obj.quorum_hash and bc_quorum_hash else True)
        )

        blockchain_rec = BlockchainRecord(
            release_id=release_id,
            published_hash=bc_published_hash,
            quorum_hash=bc_quorum_hash,
            decision=bc_decision_str,
            is_finalized=bc_is_finalized,
            create_release_tx=create_tx,
            attestation_txs=attestation_txs,
            finalize_tx=finalize_tx
        )

        # 9. Return Response
        return VerificationResponse(
            release_id=str(release_id),
            repository_url=release.repository_url,
            commit_sha=release.commit_sha,
            build_config_id=release.build_config_id,
            published_hash=release.published_hash,
            builders=final_builder_results,
            local_quorum=local_quorum_obj,
            blockchain=blockchain_rec,
            decision=bc_decision_enum,
            decision_source="BLOCKCHAIN" if bc_is_finalized else "LOCAL",
            blockchain_consistent=blockchain_consistent
        )

    async def get_verification_result(self, release_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves verification audit record directly from blockchain state."""
        bc_state = await self.blockchain_service.get_release(release_id)
        if not bc_state or not bc_state.get("is_finalized"):
            return None
        return {
            "release_id": str(release_id),
            "repository_url": bc_state.get("repository_url", ""),
            "commit_sha": bc_state.get("commit_sha", ""),
            "published_hash": bc_state.get("published_hash", ""),
            "quorum_hash": bc_state.get("quorum_hash", ""),
            "decision": bc_state.get("decision", "NONE"),
            "is_finalized": bc_state.get("is_finalized", False),
            "decision_source": "BLOCKCHAIN"
        }

    async def get_attestations(self, release_id: str) -> List[Dict[str, Any]]:
        """Retrieves stored attestations directly from blockchain state."""
        return await self.blockchain_service.get_attestations(release_id)

    async def list_releases(self) -> List[Dict[str, Any]]:
        """Lists all releases directly from the blockchain state."""
        if hasattr(self.blockchain_service, "get_all_releases"):
            raw_releases = await self.blockchain_service.get_all_releases()
        else:
            raw_releases = []
        return raw_releases
