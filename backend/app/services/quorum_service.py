from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from app.core.enums import Decision, BuilderStatus
from app.core.exceptions import InvalidQuorumPolicyError
from app.schemas.verification import BuilderVerificationResult, LocalQuorumResult, QuorumResult


class QuorumService:
    """
    Quorum calculation engine for verifying release builds.
    Supports dynamic N-of-K policy (e.g. 2-of-3, 3-of-3, 2-of-4).
    """

    @classmethod
    def calculate_quorum(
        cls,
        builder_results: List[BuilderVerificationResult],
        builder_count: int,
        quorum_required: int,
        published_hash: str
    ) -> Tuple[Decision, str, LocalQuorumResult, List[BuilderVerificationResult]]:
        """
        Executes quorum calculation over builder verification results.

        Returns:
            Tuple of (Decision, Reason, LocalQuorumResult, Updated BuilderVerificationResults)
        """
        # 1. Validate Policy Rules
        if quorum_required > builder_count:
            raise InvalidQuorumPolicyError(
                f"Invalid quorum policy: quorum_required ({quorum_required}) cannot be greater than builder_count ({builder_count})."
            )
        if quorum_required <= 0:
            raise InvalidQuorumPolicyError(
                f"Invalid quorum policy: quorum_required must be at least 1, got {quorum_required}."
            )
        if builder_count <= 0:
            raise InvalidQuorumPolicyError(
                f"Invalid quorum policy: builder_count must be at least 1, got {builder_count}."
            )

        published_hash_clean = published_hash.strip().lower()

        # 2. Filter & Deduplicate Valid Submissions
        seen_builder_ids = set()
        processed_results: List[BuilderVerificationResult] = []
        valid_builder_results: List[BuilderVerificationResult] = []

        for r in builder_results:
            b_id = r.builder_id.lower().strip()
            # Check duplicate submissions
            if b_id in seen_builder_ids:
                updated_r = r.model_copy(update={"valid": False, "status_detail": BuilderStatus.INVALID})
                processed_results.append(updated_r)
                continue

            if r.valid:
                seen_builder_ids.add(b_id)
                valid_builder_results.append(r)
                processed_results.append(r)
            else:
                updated_r = r.model_copy(update={"status_detail": BuilderStatus.INVALID})
                processed_results.append(updated_r)

        # 3. Group Valid Builders by Artifact Hash
        hash_groups: Dict[str, List[BuilderVerificationResult]] = defaultdict(list)
        for r in valid_builder_results:
            clean_hash = r.artifact_sha256.strip().lower()
            hash_groups[clean_hash].append(r)

        # 4. Find Largest Matching Hash Group
        max_count = 0
        quorum_hash: Optional[str] = None

        for h, group in hash_groups.items():
            count = len(group)
            if count > max_count:
                max_count = count
                quorum_hash = h
            elif count == max_count and max_count > 0:
                if h == published_hash_clean:
                    quorum_hash = h

        # 5. Check if Quorum Achieved
        achieved = max_count >= quorum_required

        # 6. Determine Final Decision & Reason
        if achieved and quorum_hash is not None:
            if quorum_hash == published_hash_clean:
                decision = Decision.VERIFIED
                reason = "Quorum artifact hash matches the published artifact hash."
            else:
                decision = Decision.REJECTED
                reason = "Quorum artifact hash does not match the published artifact hash."
        else:
            decision = Decision.DISPUTED
            reason = "Insufficient builder agreement to reach quorum."

        # 7. Update Status Detail on Each Builder Result
        final_builder_results: List[BuilderVerificationResult] = []
        for r in processed_results:
            if not r.valid:
                final_builder_results.append(r)
            else:
                r_hash = r.artifact_sha256.strip().lower()
                if achieved and quorum_hash is not None and r_hash == quorum_hash:
                    final_r = r.model_copy(update={"status_detail": BuilderStatus.AGREE})
                else:
                    final_r = r.model_copy(update={"status_detail": BuilderStatus.DISAGREE})
                final_builder_results.append(final_r)

        quorum_res = LocalQuorumResult(
            achieved=achieved,
            agreement=f"{max_count}/{builder_count}",
            quorum_hash=quorum_hash if achieved else None,
            expected_decision=decision
        )

        return decision, reason, quorum_res, final_builder_results
