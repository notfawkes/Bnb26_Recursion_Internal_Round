import uuid
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
from app.storage.database import Database


class ReleaseService:
    """
    Release Management and Verification Orchestration Service.
    Integrates RepositoryService, PublishedArtifactService, BuilderManager (Person 2),
    VerificationService, QuorumService, and BlockchainService (Person 1).
    """

    def __init__(
        self,
        db: Database,
        builder_manager: BuilderManager,
        blockchain_service: BlockchainService
    ):
        self.db = db
        self.builder_manager = builder_manager
        self.blockchain_service = blockchain_service

    async def create_release(self, payload: ReleaseCreate) -> ReleaseResponse:
        """Creates a new Release record after validating inputs."""
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

        release_id = f"REL-{uuid.uuid4().hex[:8].upper()}"
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        release_res = ReleaseResponse(
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

        # Save to DB
        self.db.save_release(release_res)
        return release_res

    def get_release(self, release_id: str) -> ReleaseResponse:
        """Retrieves a release by ID."""
        release = self.db.get_release(release_id)
        if not release:
            raise ReleaseNotFoundError(release_id)
        return release

    async def verify_release(self, release_id: str) -> VerificationResponse:
        """
        Runs complete updated end-to-end verification flow:
        STEP 1: Load release
        STEP 2-3: Validate repository & pinned commit
        STEP 4-5: Published artifact SHA-256 resolved
        STEP 6-7: Create release on blockchain -> get blockchain releaseId
        STEP 8-9: Send BuildRequest (without published_hash!) to Person 2 Builder Manager
        STEP 10-12: Receive BuilderManagerResponse & validate attestations (signatures, identity, repo, commit)
        STEP 13: Calculate local quorum expectation
        STEP 14: Submit valid builder evidence to blockchain using builder wallet (msg.sender)
        STEP 15-16: Finalize release & read authoritative state from contract getRelease()
        STEP 17-18: Compare local expected result against blockchain decision
        STEP 19-20: Save audit record & return structured API response
        """
        release = self.get_release(release_id)
        self.db.update_release_status(release_id, ReleaseStatus.PENDING_VERIFICATION)

        # STEP 6-7: Create Release on Blockchain
        bc_create_res = await self.blockchain_service.create_release(
            repository_url=release.repository_url,
            commit_sha=release.commit_sha,
            published_hash=release.published_hash,
            builder_count=release.builder_count,
            quorum_required=release.quorum_required
        )
        bc_release_id = bc_create_res.get("release_id", 1)
        create_tx = bc_create_res.get("transaction_hash")

        # STEP 8-9: Construct BuildRequest for Person 2 (NO published_hash!)
        builder_names = [f"builder-{'abcdefghijklmnopqrstuvwxyz'[i]}" for i in range(release.builder_count)]
        build_req = BuildRequest(
            release_id=release_id,
            repository_url=release.repository_url,
            commit_sha=release.commit_sha,
            build_config_id=release.build_config_id,
            builders=builder_names
        )

        builder_mgr_res = await self.builder_manager.run_builders(build_req)

        # STEP 10-12: Validate Builder Results and Attestations
        builder_results: List[BuilderVerificationResult] = []
        attestation_dicts: List[Dict[str, Any]] = []

        for b_res in builder_mgr_res.results:
            att_dict = b_res.attestation.model_dump()
            attestation_dicts.append(att_dict)

            ver_res = VerificationService.verify_builder_result(b_res, release)
            builder_results.append(ver_res)

        # Save raw attestations in DB
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.db.save_attestations(release_id, attestation_dicts, timestamp)

        # STEP 13: Calculate Local Quorum Expectation
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

        # STEP 14: Submit Valid Builder Evidence to Blockchain
        attestation_txs: List[str] = []
        for b_res in final_builder_results:
            if b_res.valid:
                att_tx_res = await self.blockchain_service.submit_attestation(
                    release_id=bc_release_id,
                    builder_id=b_res.builder_id,
                    artifact_hash=b_res.artifact_sha256
                )
                if att_tx_res.get("transaction_hash"):
                    attestation_txs.append(att_tx_res["transaction_hash"])

        # STEP 15: Finalize Release on Blockchain
        fin_bc_res = await self.blockchain_service.finalize_release(bc_release_id)
        finalize_tx = fin_bc_res.get("transaction_hash")

        # STEP 16-17: Read Authoritative Blockchain State
        bc_state = await self.blockchain_service.get_release(bc_release_id)
        bc_published_hash = bc_state.get("published_hash") or release.published_hash
        bc_quorum_hash = bc_state.get("quorum_hash")
        bc_decision_str = bc_state.get("decision", local_decision.value)
        bc_is_finalized = bc_state.get("is_finalized", True)

        try:
            bc_decision_enum = Decision(bc_decision_str)
        except ValueError:
            bc_decision_enum = local_decision

        # STEP 18: Check Local vs Blockchain Consistency
        blockchain_consistent = (
            (local_decision.value == bc_decision_str)
            and (local_quorum_obj.quorum_hash == bc_quorum_hash if local_quorum_obj.quorum_hash and bc_quorum_hash else True)
        )

        blockchain_rec = BlockchainRecord(
            release_id=bc_release_id,
            published_hash=bc_published_hash,
            quorum_hash=bc_quorum_hash,
            decision=bc_decision_str,
            is_finalized=bc_is_finalized,
            create_release_tx=create_tx,
            attestation_txs=attestation_txs,
            finalize_tx=finalize_tx
        )

        # Update release status in DB
        final_status = ReleaseStatus(bc_decision_str) if bc_decision_str in ReleaseStatus.__members__ else ReleaseStatus(local_decision.value)
        self.db.update_release_status(release_id, final_status)

        # STEP 19: Save Audit Record
        audit_record = {
            "verification_id": f"VER-{uuid.uuid4().hex[:8].upper()}",
            "release_id": release_id,
            "repository_url": release.repository_url,
            "commit_sha": release.commit_sha,
            "published_hash": release.published_hash,
            "builders": [b.model_dump() for b in final_builder_results],
            "local_quorum": local_quorum_obj.model_dump(),
            "blockchain": blockchain_rec.model_dump(),
            "decision": bc_decision_str,
            "decision_source": "BLOCKCHAIN" if bc_is_finalized else "LOCAL",
            "blockchain_consistent": blockchain_consistent,
            "timestamp": timestamp
        }
        self.db.save_verification_audit(audit_record)

        # STEP 20: Return Structured Verification Response
        return VerificationResponse(
            release_id=release_id,
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

    def get_verification_result(self, release_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves stored verification audit result."""
        release = self.get_release(release_id)
        audit = self.db.get_verification_audit(release_id)
        if not audit:
            return None
        return audit
