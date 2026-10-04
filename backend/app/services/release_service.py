import datetime
from typing import Dict, Any, List, Optional, ClassVar
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

    _verification_cache: ClassVar[dict[tuple[int, str], VerificationResponse]] = {}

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

        # An explicit UI/API opt-in prevents duplicate on-chain releases while
        # preserving the ability to create a separate verification intentionally.
        if payload.reuse_existing and hasattr(self.blockchain_service, "get_all_releases"):
            existing_releases = await self.blockchain_service.get_all_releases()
            normalized_repository = repo_url.rstrip("/").removesuffix(".git").lower()
            for existing in existing_releases:
                existing_repository = str(existing.get("repository_url", "")).rstrip("/").removesuffix(".git").lower()
                if (
                    existing_repository == normalized_repository
                    and str(existing.get("commit_sha", "")).lower() == pinned_commit
                    and str(existing.get("published_hash", "")).lower() == published_hash
                    and existing.get("build_config_id", "python-package-v1") == payload.build_config_id
                    and existing.get("artifact_name", "") == payload.artifact_name
                    and int(existing.get("builder_count", 0)) == payload.builder_count
                    and int(existing.get("quorum_required", 0)) == payload.quorum_required
                ):
                    decision = str(existing.get("decision", "CREATED"))
                    try:
                        existing_status = ReleaseStatus(decision)
                    except ValueError:
                        existing_status = ReleaseStatus.CREATED
                    return ReleaseResponse(
                        release_id=str(existing["release_id"]),
                        repository_url=repo_url,
                        repository=repo_url,
                        commit_sha=pinned_commit,
                        commit=pinned_commit,
                        build_config_id=payload.build_config_id,
                        published_hash=published_hash,
                        artifact_name=payload.artifact_name,
                        builder_count=payload.builder_count,
                        quorum_required=payload.quorum_required,
                        status=existing_status,
                        created_at=created_at,
                        reused=True,
                    )

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

        cache_key = (id(self.blockchain_service), str(release_id))
        cached = self._verification_cache.get(cache_key)
        if cached is not None:
            return cached.model_copy(update={"cache_hit": True})

        existing_state = await self.blockchain_service.get_release(release_id)
        if existing_state.get("is_finalized"):
            reconstructed = await self._reconstruct_finalized_response(release, existing_state)
            self._verification_cache[cache_key] = reconstructed
            return reconstructed.model_copy(update={"cache_hit": True})

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
        response = VerificationResponse(
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
        self._verification_cache[cache_key] = response
        return response

    async def _reconstruct_finalized_response(
        self, release: ReleaseResponse, bc_state: Dict[str, Any]
    ) -> VerificationResponse:
        """Rebuild an API audit view from immutable on-chain evidence without Docker."""
        attestations = await self.blockchain_service.get_attestations(release.release_id)
        quorum_hash = bc_state.get("quorum_hash") or None
        builders: List[BuilderVerificationResult] = []
        matching = 0
        for index, attestation in enumerate(attestations):
            artifact_hash = str(attestation.get("artifactHash", ""))
            agrees = bool(quorum_hash and artifact_hash.lower() == str(quorum_hash).lower())
            if agrees:
                matching += 1
            builders.append(
                BuilderVerificationResult(
                    builder_id=f"builder-{'abcdefghijklmnopqrstuvwxyz'[index]}",
                    status="SUCCESS",
                    artifact_name=release.artifact_name,
                    artifact_sha256=artifact_hash,
                    signature_valid=True,
                    identity_valid=True,
                    source_match=True,
                    commit_match=True,
                    valid=True,
                    status_detail=("AGREE" if agrees else "DISAGREE"),
                    logs=[],
                )
            )

        decision_text = str(bc_state.get("decision", "DISPUTED"))
        try:
            decision = Decision(decision_text)
        except ValueError:
            decision = Decision.DISPUTED
        local_quorum = LocalQuorumResult(
            achieved=bool(quorum_hash),
            agreement=f"{matching}/{release.builder_count}",
            quorum_hash=quorum_hash,
            expected_decision=decision,
        )
        blockchain = BlockchainRecord(
            release_id=release.release_id,
            published_hash=bc_state.get("published_hash", release.published_hash),
            quorum_hash=quorum_hash,
            decision=decision.value,
            is_finalized=True,
            create_release_tx=bc_state.get("create_release_tx"),
            attestation_txs=bc_state.get("attestation_txs", []),
            finalize_tx=bc_state.get("finalize_tx"),
        )
        return VerificationResponse(
            release_id=release.release_id,
            repository_url=release.repository_url,
            commit_sha=release.commit_sha,
            build_config_id=release.build_config_id,
            published_hash=release.published_hash,
            builders=builders,
            local_quorum=local_quorum,
            blockchain=blockchain,
            decision=decision,
            decision_source="BLOCKCHAIN",
            blockchain_consistent=True,
            cache_hit=True,
        )

    async def get_verification_result(self, release_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves verification audit record directly from blockchain state."""
        bc_state = await self.blockchain_service.get_release(release_id)
        if not bc_state or not bc_state.get("is_finalized"):
            return None
        cache_key = (id(self.blockchain_service), str(release_id))
        cached = self._verification_cache.get(cache_key)
        if cached is not None:
            return cached.model_copy(update={"cache_hit": True}).model_dump(mode="json")
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

