// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IQuorumVerifier
 * @notice Interface for the Quorum software supply-chain verification contract.
 */
interface IQuorumVerifier {
    enum Decision {
        NONE,
        VERIFIED,
        REJECTED,
        DISPUTED
    }

    struct Release {
        uint256 id;
        string repository;
        string commit;
        bytes32 publishedHash;
        uint256 builderCount;
        uint256 quorumRequired;
        bytes32 quorumHash;
        Decision decision;
        bool isFinalized;
    }

    struct Attestation {
        address builder;
        bytes32 artifactHash;
        uint256 timestamp;
    }

    // Events
    event ReleaseCreated(
        uint256 indexed releaseId,
        string repository,
        string commit,
        bytes32 publishedHash,
        uint256 builderCount,
        uint256 quorumRequired
    );

    event AttestationSubmitted(
        uint256 indexed releaseId,
        address indexed builder,
        bytes32 artifactHash,
        uint256 timestamp
    );

    event VerificationFinalized(
        uint256 indexed releaseId,
        Decision decision,
        bytes32 quorumHash
    );

    event BuilderRegistered(address indexed builder);
    event BuilderUnregistered(address indexed builder);

    // Custom Errors
    error ReleaseNotFound(uint256 releaseId);
    error InvalidBuilderCount();
    error InvalidQuorum(uint256 quorumRequired, uint256 builderCount);
    error BuilderNotRegistered(address builder);
    error BuilderAlreadyRegistered(address builder);
    error InvalidBuilderAddress();
    error DuplicateAttestation(uint256 releaseId, address builder);
    error InvalidHash();
    error EmptyRepository();
    error EmptyCommit();
    error ReleaseAlreadyFinalized(uint256 releaseId);
    error InsufficientAttestations(uint256 currentCount, uint256 requiredCount);
    error MaxAttestationsReached(uint256 releaseId);

    // Builder Management
    function registerBuilder(address builder) external;
    function registerBuilders(address[] calldata builders) external;
    function unregisterBuilder(address builder) external;
    function isBuilder(address builder) external view returns (bool);

    // Release Management & Attestation
    function createRelease(
        string calldata repository,
        string calldata commit,
        bytes32 publishedHash,
        uint256 builderCount,
        uint256 quorumRequired
    ) external returns (uint256 releaseId);

    function submitAttestation(
        uint256 releaseId,
        bytes32 artifactHash
    ) external;

    function finalizeRelease(uint256 releaseId) external;

    // View Functions
    function getRelease(uint256 releaseId) external view returns (Release memory);
    function getAttestations(uint256 releaseId) external view returns (Attestation[] memory);
    function releaseCount() external view returns (uint256);
}
