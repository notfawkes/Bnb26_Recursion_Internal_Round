import pytest
from app.services.quorum_service import QuorumService
from app.schemas.verification import BuilderVerificationResult
from app.core.enums import Decision, BuilderStatus
from app.core.exceptions import InvalidQuorumPolicyError

PUB_HASH = "a" * 64
OTHER_HASH_1 = "b" * 64
OTHER_HASH_2 = "c" * 64


def make_builder_res(builder_id: str, artifact_hash: str, valid: bool = True) -> BuilderVerificationResult:
    return BuilderVerificationResult(
        builder_id=builder_id,
        status="SUCCESS",
        artifact_name="safecalc.tar.gz",
        artifact_sha256=artifact_hash,
        signature_valid=valid,
        identity_valid=valid,
        source_match=valid,
        commit_match=valid,
        valid=valid,
        status_detail=BuilderStatus.AGREE if valid else BuilderStatus.INVALID
    )


def test_quorum_3_of_3_all_matching():
    builders = [
        make_builder_res("builder-A", PUB_HASH),
        make_builder_res("builder-B", PUB_HASH),
        make_builder_res("builder-C", PUB_HASH),
    ]
    decision, reason, quorum_res, results = QuorumService.calculate_quorum(
        builder_results=builders,
        builder_count=3,
        quorum_required=3,
        published_hash=PUB_HASH
    )
    assert decision == Decision.VERIFIED
    assert quorum_res.achieved is True
    assert quorum_res.quorum_hash == PUB_HASH
    assert quorum_res.agreement == "3/3"
    assert all(r.status_detail == BuilderStatus.AGREE for r in results)


def test_quorum_2_of_3_one_disagreement():
    builders = [
        make_builder_res("builder-A", PUB_HASH),
        make_builder_res("builder-B", PUB_HASH),
        make_builder_res("builder-C", OTHER_HASH_1),
    ]
    decision, reason, quorum_res, results = QuorumService.calculate_quorum(
        builder_results=builders,
        builder_count=3,
        quorum_required=2,
        published_hash=PUB_HASH
    )
    assert decision == Decision.VERIFIED
    assert quorum_res.achieved is True
    assert quorum_res.quorum_hash == PUB_HASH
    assert quorum_res.agreement == "2/3"
    assert results[0].status_detail == BuilderStatus.AGREE
    assert results[1].status_detail == BuilderStatus.AGREE
    assert results[2].status_detail == BuilderStatus.DISAGREE


def test_quorum_3_of_3_strict_policy_one_disagreement():
    builders = [
        make_builder_res("builder-A", PUB_HASH),
        make_builder_res("builder-B", PUB_HASH),
        make_builder_res("builder-C", OTHER_HASH_1),
    ]
    decision, reason, quorum_res, results = QuorumService.calculate_quorum(
        builder_results=builders,
        builder_count=3,
        quorum_required=3,
        published_hash=PUB_HASH
    )
    assert decision == Decision.DISPUTED
    assert quorum_res.achieved is False
    assert "Insufficient builder agreement" in reason


def test_quorum_wrong_quorum_artifact():
    builders = [
        make_builder_res("builder-A", OTHER_HASH_1),
        make_builder_res("builder-B", OTHER_HASH_1),
        make_builder_res("builder-C", PUB_HASH),
    ]
    decision, reason, quorum_res, results = QuorumService.calculate_quorum(
        builder_results=builders,
        builder_count=3,
        quorum_required=2,
        published_hash=PUB_HASH
    )
    assert decision == Decision.REJECTED
    assert quorum_res.achieved is True
    assert quorum_res.quorum_hash == OTHER_HASH_1
    assert "does not match the published artifact hash" in reason


def test_quorum_complete_disagreement():
    builders = [
        make_builder_res("builder-A", PUB_HASH),
        make_builder_res("builder-B", OTHER_HASH_1),
        make_builder_res("builder-C", OTHER_HASH_2),
    ]
    decision, reason, quorum_res, results = QuorumService.calculate_quorum(
        builder_results=builders,
        builder_count=3,
        quorum_required=2,
        published_hash=PUB_HASH
    )
    assert decision == Decision.DISPUTED
    assert quorum_res.achieved is False


def test_quorum_one_invalid_signature():
    builders = [
        make_builder_res("builder-A", PUB_HASH, valid=True),
        make_builder_res("builder-B", PUB_HASH, valid=False),
        make_builder_res("builder-C", PUB_HASH, valid=True),
    ]
    decision, reason, quorum_res, results = QuorumService.calculate_quorum(
        builder_results=builders,
        builder_count=3,
        quorum_required=2,
        published_hash=PUB_HASH
    )
    assert decision == Decision.VERIFIED
    assert quorum_res.achieved is True
    assert results[1].status_detail == BuilderStatus.INVALID


def test_quorum_two_invalid_signatures_causes_disputed():
    builders = [
        make_builder_res("builder-A", PUB_HASH, valid=True),
        make_builder_res("builder-B", PUB_HASH, valid=False),
        make_builder_res("builder-C", PUB_HASH, valid=False),
    ]
    decision, reason, quorum_res, results = QuorumService.calculate_quorum(
        builder_results=builders,
        builder_count=3,
        quorum_required=2,
        published_hash=PUB_HASH
    )
    assert decision == Decision.DISPUTED
    assert quorum_res.achieved is False


def test_quorum_2_of_4_policy():
    builders = [
        make_builder_res("builder-A", PUB_HASH),
        make_builder_res("builder-B", PUB_HASH),
        make_builder_res("builder-C", OTHER_HASH_1),
        make_builder_res("builder-D", OTHER_HASH_2),
    ]
    decision, reason, quorum_res, results = QuorumService.calculate_quorum(
        builder_results=builders,
        builder_count=4,
        quorum_required=2,
        published_hash=PUB_HASH
    )
    assert decision == Decision.VERIFIED
    assert quorum_res.achieved is True
    assert quorum_res.agreement == "2/4"


def test_quorum_duplicate_builder_submissions():
    builders = [
        make_builder_res("builder-A", PUB_HASH),
        make_builder_res("builder-A", OTHER_HASH_1),
        make_builder_res("builder-B", PUB_HASH),
    ]
    decision, reason, quorum_res, results = QuorumService.calculate_quorum(
        builder_results=builders,
        builder_count=3,
        quorum_required=2,
        published_hash=PUB_HASH
    )
    assert decision == Decision.VERIFIED
    assert results[1].status_detail == BuilderStatus.INVALID


def test_quorum_invalid_policy_exceptions():
    builders = [make_builder_res("builder-A", PUB_HASH)]

    with pytest.raises(InvalidQuorumPolicyError):
        QuorumService.calculate_quorum(builders, builder_count=2, quorum_required=3, published_hash=PUB_HASH)

    with pytest.raises(InvalidQuorumPolicyError):
        QuorumService.calculate_quorum(builders, builder_count=2, quorum_required=0, published_hash=PUB_HASH)
