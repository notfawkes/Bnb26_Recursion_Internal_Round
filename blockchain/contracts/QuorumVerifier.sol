// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import { Ownable } from "@openzeppelin/contracts/access/Ownable.sol";
import { IQuorumVerifier } from "../interfaces/IQuorumVerifier.sol";

/**
 * @title QuorumVerifier
 * @notice Independent on-chain quorum verification for reproducible builds.
 * @dev Stores verification evidence and independently determines VERIFIED, REJECTED, or DISPUTED decisions.
 */
contract QuorumVerifier is Ownable, IQuorumVerifier {
    uint256 private _releaseCounter;

    mapping(address => bool) public override isBuilder;
    mapping(uint256 => Release) private _releases;
    mapping(uint256 => Attestation[]) private _attestations;
    mapping(uint256 => mapping(address => bool)) public hasSubmittedAttestation;

    constructor() Ownable(msg.sender) {}

    /**
     * @notice Register a single builder address. Only callable by contract owner.
     * @param builder The address of the builder to register.
     */
    function registerBuilder(address builder) external override onlyOwner {
        if (builder == address(0)) revert InvalidBuilderAddress();
        if (isBuilder[builder]) revert BuilderAlreadyRegistered(builder);

        isBuilder[builder] = true;
        emit BuilderRegistered(builder);
    }

    /**
     * @notice Register multiple builder addresses in batch. Only callable by contract owner.
     * @param builders Array of builder addresses to register.
     */
    function registerBuilders(address[] calldata builders) external override onlyOwner {
        for (uint256 i = 0; i < builders.length; i++) {
            address builder = builders[i];
            if (builder == address(0)) revert InvalidBuilderAddress();
            if (!isBuilder[builder]) {
                isBuilder[builder] = true;
                emit BuilderRegistered(builder);
            }
        }
    }

    /**
     * @notice Unregister a builder address. Only callable by contract owner.
     * @param builder The address of the builder to unregister.
     */
    function unregisterBuilder(address builder) external override onlyOwner {
        if (!isBuilder[builder]) revert BuilderNotRegistered(builder);

        isBuilder[builder] = false;
        emit BuilderUnregistered(builder);
    }

    /**
     * @notice Create a release verification request.
     * @param repository The canonical repository identifier (e.g., "org/repo").
     * @param commit The pinned git commit SHA being verified.
     * @param publishedHash The SHA-256 hash of the officially published artifact.
     * @param builderCount Total number of independent builders expected to reproduce the release.
     * @param quorumRequired Number of matching builder hashes required to reach quorum.
     * @return releaseId The unique ID of the created release.
     */
    function createRelease(
        string calldata repository,
        string calldata commit,
        bytes32 publishedHash,
        uint256 builderCount,
        uint256 quorumRequired
    ) external override returns (uint256 releaseId) {
        if (bytes(repository).length == 0) revert EmptyRepository();
        if (bytes(commit).length == 0) revert EmptyCommit();
        if (publishedHash == bytes32(0)) revert InvalidHash();
        if (builderCount == 0) revert InvalidBuilderCount();
        if (quorumRequired == 0 || quorumRequired > builderCount) {
            revert InvalidQuorum(quorumRequired, builderCount);
        }

        releaseId = ++_releaseCounter;

        _releases[releaseId] = Release({
            id: releaseId,
            repository: repository,
            commit: commit,
            publishedHash: publishedHash,
            builderCount: builderCount,
            quorumRequired: quorumRequired,
            quorumHash: bytes32(0),
            decision: Decision.NONE,
            isFinalized: false
        });

        emit ReleaseCreated(
            releaseId,
            repository,
            commit,
            publishedHash,
            builderCount,
            quorumRequired
        );
    }

    /**
     * @notice Submit a builder attestation containing the SHA-256 hash of the reproduced artifact.
     * @dev Only registered builders may submit. Builder identity is authenticated by msg.sender.
     * @param releaseId The ID of the release being attested.
     * @param artifactHash The SHA-256 hash of the builder's reproduced artifact.
     */
    function submitAttestation(
        uint256 releaseId,
        bytes32 artifactHash
    ) external override {
        if (releaseId == 0 || releaseId > _releaseCounter) revert ReleaseNotFound(releaseId);

        Release storage rel = _releases[releaseId];
        if (rel.isFinalized) revert ReleaseAlreadyFinalized(releaseId);
        if (!isBuilder[msg.sender]) revert BuilderNotRegistered(msg.sender);
        if (hasSubmittedAttestation[releaseId][msg.sender]) {
            revert DuplicateAttestation(releaseId, msg.sender);
        }
        if (artifactHash == bytes32(0)) revert InvalidHash();
        if (_attestations[releaseId].length >= rel.builderCount) {
            revert MaxAttestationsReached(releaseId);
        }

        hasSubmittedAttestation[releaseId][msg.sender] = true;

        _attestations[releaseId].push(Attestation({
            builder: msg.sender,
            artifactHash: artifactHash,
            timestamp: block.timestamp
        }));

        emit AttestationSubmitted(releaseId, msg.sender, artifactHash, block.timestamp);
    }

    /**
     * @notice Finalize a release and independently calculate the verification decision on-chain.
     * @dev Determines if any hash reached quorumRequired. If yes: VERIFIED (matches published) or REJECTED.
     * If no hash reached quorum and all builders have submitted: DISPUTED.
     * Reverts if finalizing before sufficient evidence is available.
     * @param releaseId The ID of the release to finalize.
     */
    function finalizeRelease(uint256 releaseId) external override {
        if (releaseId == 0 || releaseId > _releaseCounter) revert ReleaseNotFound(releaseId);

        Release storage rel = _releases[releaseId];
        if (rel.isFinalized) revert ReleaseAlreadyFinalized(releaseId);

        Attestation[] storage atts = _attestations[releaseId];
        uint256 attCount = atts.length;

        // Calculate quorum independently on-chain
        bytes32 quorumHash = bytes32(0);
        bool reachedQuorum = false;

        for (uint256 i = 0; i < attCount; i++) {
            bytes32 candidate = atts[i].artifactHash;
            uint256 count = 0;
            for (uint256 j = 0; j < attCount; j++) {
                if (atts[j].artifactHash == candidate) {
                    count++;
                }
            }
            if (count >= rel.quorumRequired) {
                quorumHash = candidate;
                reachedQuorum = true;
                break;
            }
        }

        // If no quorum reached yet and not all builders have submitted, cannot determine final state
        if (!reachedQuorum && attCount < rel.builderCount) {
            revert InsufficientAttestations(attCount, rel.builderCount);
        }

        Decision finalDecision;
        if (!reachedQuorum) {
            // All builders submitted but no hash achieved quorumRequired
            finalDecision = Decision.DISPUTED;
            quorumHash = bytes32(0);
        } else {
            if (quorumHash == rel.publishedHash) {
                finalDecision = Decision.VERIFIED;
            } else {
                finalDecision = Decision.REJECTED;
            }
        }

        rel.quorumHash = quorumHash;
        rel.decision = finalDecision;
        rel.isFinalized = true;

        emit VerificationFinalized(releaseId, finalDecision, quorumHash);
    }

    /**
     * @notice Retrieve complete release details.
     * @param releaseId The ID of the release.
     */
    function getRelease(uint256 releaseId) external view override returns (Release memory) {
        if (releaseId == 0 || releaseId > _releaseCounter) revert ReleaseNotFound(releaseId);
        return _releases[releaseId];
    }

    /**
     * @notice Retrieve all attestations submitted for a release.
     * @param releaseId The ID of the release.
     */
    function getAttestations(uint256 releaseId) external view override returns (Attestation[] memory) {
        if (releaseId == 0 || releaseId > _releaseCounter) revert ReleaseNotFound(releaseId);
        return _attestations[releaseId];
    }

    /**
     * @notice Total number of releases created.
     */
    function releaseCount() external view override returns (uint256) {
        return _releaseCounter;
    }
}
