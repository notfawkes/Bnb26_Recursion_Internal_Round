import { expect } from "chai";
import { network } from "hardhat";

const { ethers } = await network.create();

describe("QuorumVerifier", function () {
  enum Decision {
    NONE = 0,
    VERIFIED = 1,
    REJECTED = 2,
    DISPUTED = 3,
  }

  const REPO = "quorum/sample-app";
  const COMMIT = "a1b2c3d4e5f6071829304152637485960718293a";
  const HASH_AAA = ethers.sha256(ethers.toUtf8Bytes("artifact-hash-AAA"));
  const HASH_BBB = ethers.sha256(ethers.toUtf8Bytes("artifact-hash-BBB"));
  const HASH_CCC = ethers.sha256(ethers.toUtf8Bytes("artifact-hash-CCC"));
  const HASH_DIFF = ethers.sha256(ethers.toUtf8Bytes("artifact-hash-DIFF"));

  let verifier: any;
  let owner: any;
  let builder1: any;
  let builder2: any;
  let builder3: any;
  let unregisteredUser: any;

  beforeEach(async function () {
    [owner, builder1, builder2, builder3, unregisteredUser] = await ethers.getSigners();
    verifier = await ethers.deployContract("QuorumVerifier");
    await verifier.waitForDeployment();

    // Register builder1, builder2, builder3
    await verifier.registerBuilders([
      builder1.address,
      builder2.address,
      builder3.address,
    ]);
  });

  describe("Builder Registration", function () {
    it("should allow the owner to register and verify builders", async function () {
      expect(await verifier.isBuilder(builder1.address)).to.be.true;
      expect(await verifier.isBuilder(builder2.address)).to.be.true;
      expect(await verifier.isBuilder(builder3.address)).to.be.true;
      expect(await verifier.isBuilder(unregisteredUser.address)).to.be.false;
    });

    it("should emit BuilderRegistered event", async function () {
      const [, , , , , newBuilder] = await ethers.getSigners();
      await expect(verifier.registerBuilder(newBuilder.address))
        .to.emit(verifier, "BuilderRegistered")
        .withArgs(newBuilder.address);
      expect(await verifier.isBuilder(newBuilder.address)).to.be.true;
    });

    it("should prevent duplicate builder registration", async function () {
      await expect(verifier.registerBuilder(builder1.address))
        .to.be.revertedWithCustomError(verifier, "BuilderAlreadyRegistered")
        .withArgs(builder1.address);
    });

    it("should prevent registering address(0)", async function () {
      await expect(verifier.registerBuilder(ethers.ZeroAddress))
        .to.be.revertedWithCustomError(verifier, "InvalidBuilderAddress");
    });

    it("should allow the owner to unregister a builder", async function () {
      await expect(verifier.unregisterBuilder(builder1.address))
        .to.emit(verifier, "BuilderUnregistered")
        .withArgs(builder1.address);
      expect(await verifier.isBuilder(builder1.address)).to.be.false;
    });

    it("should revert if unregistering a non-registered builder", async function () {
      await expect(verifier.unregisterBuilder(unregisteredUser.address))
        .to.be.revertedWithCustomError(verifier, "BuilderNotRegistered")
        .withArgs(unregisteredUser.address);
    });

    it("should prevent non-owner from registering builders", async function () {
      const nonOwnerVerifier = verifier.connect(unregisteredUser);
      await expect(
        nonOwnerVerifier.registerBuilder(unregisteredUser.address)
      ).to.be.revertedWithCustomError(verifier, "OwnableUnauthorizedAccount");
    });
  });

  describe("Release Creation", function () {
    it("should create a release and emit ReleaseCreated event", async function () {
      const tx = await verifier.createRelease(REPO, COMMIT, HASH_AAA, 3n, 2n);
      await expect(tx)
        .to.emit(verifier, "ReleaseCreated")
        .withArgs(1n, REPO, COMMIT, HASH_AAA, 3n, 2n);

      const release = await verifier.getRelease(1n);
      expect(release.id).to.equal(1n);
      expect(release.repository).to.equal(REPO);
      expect(release.commit).to.equal(COMMIT);
      expect(release.publishedHash).to.equal(HASH_AAA);
      expect(release.builderCount).to.equal(3n);
      expect(release.quorumRequired).to.equal(2n);
      expect(release.quorumHash).to.equal(ethers.ZeroHash);
      expect(release.decision).to.equal(Decision.NONE);
      expect(release.isFinalized).to.be.false;
    });

    it("should increment release ID on multiple releases", async function () {
      await verifier.createRelease(REPO, COMMIT, HASH_AAA, 3n, 2n);
      await verifier.createRelease(REPO, COMMIT, HASH_BBB, 3n, 2n);
      expect(await verifier.releaseCount()).to.equal(2n);

      const r2 = await verifier.getRelease(2n);
      expect(r2.id).to.equal(2n);
      expect(r2.publishedHash).to.equal(HASH_BBB);
    });

    it("should reject release with empty repository", async function () {
      await expect(
        verifier.createRelease("", COMMIT, HASH_AAA, 3n, 2n)
      ).to.be.revertedWithCustomError(verifier, "EmptyRepository");
    });

    it("should reject release with empty commit", async function () {
      await expect(
        verifier.createRelease(REPO, "", HASH_AAA, 3n, 2n)
      ).to.be.revertedWithCustomError(verifier, "EmptyCommit");
    });

    it("should reject release with zero published hash", async function () {
      await expect(
        verifier.createRelease(REPO, COMMIT, ethers.ZeroHash, 3n, 2n)
      ).to.be.revertedWithCustomError(verifier, "InvalidHash");
    });

    it("should reject release with zero builder count", async function () {
      await expect(
        verifier.createRelease(REPO, COMMIT, HASH_AAA, 0n, 0n)
      ).to.be.revertedWithCustomError(verifier, "InvalidBuilderCount");
    });

    it("should reject release with invalid quorum required (0)", async function () {
      await expect(
        verifier.createRelease(REPO, COMMIT, HASH_AAA, 3n, 0n)
      ).to.be.revertedWithCustomError(verifier, "InvalidQuorum")
        .withArgs(0n, 3n);
    });

    it("should reject release with invalid quorum required (> builderCount)", async function () {
      await expect(
        verifier.createRelease(REPO, COMMIT, HASH_AAA, 3n, 4n)
      ).to.be.revertedWithCustomError(verifier, "InvalidQuorum")
        .withArgs(4n, 3n);
    });
  });

  describe("Attestation Submission", function () {
    let releaseId: bigint;

    beforeEach(async function () {
      await verifier.createRelease(REPO, COMMIT, HASH_AAA, 3n, 2n);
      releaseId = 1n;
    });

    it("should allow registered builder to submit attestation and emit event", async function () {
      const vB1 = verifier.connect(builder1);
      const tx = await vB1.submitAttestation(releaseId, HASH_AAA);

      await expect(tx)
        .to.emit(verifier, "AttestationSubmitted");

      const attestations = await verifier.getAttestations(releaseId);
      expect(attestations.length).to.equal(1);
      expect(attestations[0].builder).to.equal(builder1.address);
      expect(attestations[0].artifactHash).to.equal(HASH_AAA);
      expect(attestations[0].timestamp).to.be.gt(0n);
    });

    it("should reject attestation from unregistered builder", async function () {
      const vUnreg = verifier.connect(unregisteredUser);
      await expect(
        vUnreg.submitAttestation(releaseId, HASH_AAA)
      ).to.be.revertedWithCustomError(verifier, "BuilderNotRegistered")
        .withArgs(unregisteredUser.address);
    });

    it("should reject duplicate attestation from same builder", async function () {
      const vB1 = verifier.connect(builder1);
      await vB1.submitAttestation(releaseId, HASH_AAA);

      await expect(
        vB1.submitAttestation(releaseId, HASH_AAA)
      ).to.be.revertedWithCustomError(verifier, "DuplicateAttestation")
        .withArgs(releaseId, builder1.address);
    });

    it("should reject attestation with zero hash", async function () {
      const vB1 = verifier.connect(builder1);
      await expect(
        vB1.submitAttestation(releaseId, ethers.ZeroHash)
      ).to.be.revertedWithCustomError(verifier, "InvalidHash");
    });

    it("should reject attestation for non-existent release", async function () {
      const vB1 = verifier.connect(builder1);
      await expect(
        vB1.submitAttestation(999n, HASH_AAA)
      ).to.be.revertedWithCustomError(verifier, "ReleaseNotFound")
        .withArgs(999n);
    });
  });

  describe("Quorum Verification Scenarios", function () {
    // 1. 3/3 builders produce same hash, published = same hash -> VERIFIED
    it("Scenario 1: 3/3 builders produce same hash, published = same hash -> VERIFIED", async function () {
      await verifier.createRelease(REPO, COMMIT, HASH_AAA, 3n, 2n);
      const releaseId = 1n;

      await verifier.connect(builder1).submitAttestation(releaseId, HASH_AAA);
      await verifier.connect(builder2).submitAttestation(releaseId, HASH_AAA);
      await verifier.connect(builder3).submitAttestation(releaseId, HASH_AAA);

      await expect(verifier.finalizeRelease(releaseId))
        .to.emit(verifier, "VerificationFinalized")
        .withArgs(releaseId, Decision.VERIFIED, HASH_AAA);

      const release = await verifier.getRelease(releaseId);
      expect(release.decision).to.equal(Decision.VERIFIED);
      expect(release.quorumHash).to.equal(HASH_AAA);
      expect(release.isFinalized).to.be.true;
    });

    // 2. 3/3 builders produce same hash, published = different hash -> REJECTED
    it("Scenario 2: 3/3 builders produce same hash, published = different hash -> REJECTED", async function () {
      await verifier.createRelease(REPO, COMMIT, HASH_DIFF, 3n, 2n);
      const releaseId = 1n;

      await verifier.connect(builder1).submitAttestation(releaseId, HASH_AAA);
      await verifier.connect(builder2).submitAttestation(releaseId, HASH_AAA);
      await verifier.connect(builder3).submitAttestation(releaseId, HASH_AAA);

      await expect(verifier.finalizeRelease(releaseId))
        .to.emit(verifier, "VerificationFinalized")
        .withArgs(releaseId, Decision.REJECTED, HASH_AAA);

      const release = await verifier.getRelease(releaseId);
      expect(release.decision).to.equal(Decision.REJECTED);
      expect(release.quorumHash).to.equal(HASH_AAA);
      expect(release.isFinalized).to.be.true;
    });

    // 3. 2/3 builders produce same hash, published = quorum hash -> VERIFIED
    it("Scenario 3: 2/3 builders produce same hash, published = quorum hash -> VERIFIED", async function () {
      await verifier.createRelease(REPO, COMMIT, HASH_AAA, 3n, 2n);
      const releaseId = 1n;

      // Builder 1 and 2 produce HASH_AAA, Builder 3 produces HASH_BBB
      await verifier.connect(builder1).submitAttestation(releaseId, HASH_AAA);
      await verifier.connect(builder2).submitAttestation(releaseId, HASH_AAA);
      await verifier.connect(builder3).submitAttestation(releaseId, HASH_BBB);

      await expect(verifier.finalizeRelease(releaseId))
        .to.emit(verifier, "VerificationFinalized")
        .withArgs(releaseId, Decision.VERIFIED, HASH_AAA);

      const release = await verifier.getRelease(releaseId);
      expect(release.decision).to.equal(Decision.VERIFIED);
      expect(release.quorumHash).to.equal(HASH_AAA);
      expect(release.isFinalized).to.be.true;
    });

    // 4. 2/3 builders produce same hash, published = different hash -> REJECTED
    it("Scenario 4: 2/3 builders produce same hash, published = different hash -> REJECTED", async function () {
      await verifier.createRelease(REPO, COMMIT, HASH_BBB, 3n, 2n);
      const releaseId = 1n;

      // Builder 1 and 2 produce HASH_AAA (2/3 quorum), Builder 3 produces HASH_BBB
      // Published hash is HASH_BBB, but quorum is HASH_AAA -> REJECTED
      await verifier.connect(builder1).submitAttestation(releaseId, HASH_AAA);
      await verifier.connect(builder2).submitAttestation(releaseId, HASH_AAA);
      await verifier.connect(builder3).submitAttestation(releaseId, HASH_BBB);

      await expect(verifier.finalizeRelease(releaseId))
        .to.emit(verifier, "VerificationFinalized")
        .withArgs(releaseId, Decision.REJECTED, HASH_AAA);

      const release = await verifier.getRelease(releaseId);
      expect(release.decision).to.equal(Decision.REJECTED);
      expect(release.quorumHash).to.equal(HASH_AAA);
      expect(release.isFinalized).to.be.true;
    });

    // 5. 1/1/1 hashes -> DISPUTED
    it("Scenario 5: 1/1/1 hashes (no quorum reached) -> DISPUTED", async function () {
      await verifier.createRelease(REPO, COMMIT, HASH_AAA, 3n, 2n);
      const releaseId = 1n;

      await verifier.connect(builder1).submitAttestation(releaseId, HASH_AAA);
      await verifier.connect(builder2).submitAttestation(releaseId, HASH_BBB);
      await verifier.connect(builder3).submitAttestation(releaseId, HASH_CCC);

      await expect(verifier.finalizeRelease(releaseId))
        .to.emit(verifier, "VerificationFinalized")
        .withArgs(releaseId, Decision.DISPUTED, ethers.ZeroHash);

      const release = await verifier.getRelease(releaseId);
      expect(release.decision).to.equal(Decision.DISPUTED);
      expect(release.quorumHash).to.equal(ethers.ZeroHash);
      expect(release.isFinalized).to.be.true;
    });
  });

  describe("Finalization Restrictions & Edge Cases", function () {
    let releaseId: bigint;

    beforeEach(async function () {
      await verifier.createRelease(REPO, COMMIT, HASH_AAA, 3n, 2n);
      releaseId = 1n;
    });

    it("should revert if finalized before sufficient evidence (premature finalization)", async function () {
      // Only 1 builder has submitted and quorum is 2
      await verifier.connect(builder1).submitAttestation(releaseId, HASH_AAA);

      await expect(
        verifier.finalizeRelease(releaseId)
      ).to.be.revertedWithCustomError(verifier, "InsufficientAttestations")
        .withArgs(1n, 3n);
    });

    it("should allow finalization as soon as quorum is reached even before all builders submit", async function () {
      // 2 builders submit HASH_AAA, which satisfies quorumRequired = 2
      await verifier.connect(builder1).submitAttestation(releaseId, HASH_AAA);
      await verifier.connect(builder2).submitAttestation(releaseId, HASH_AAA);

      await verifier.finalizeRelease(releaseId);
      const release = await verifier.getRelease(releaseId);
      expect(release.decision).to.equal(Decision.VERIFIED);
      expect(release.isFinalized).to.be.true;
    });

    it("should prevent attestation submission after release is finalized", async function () {
      await verifier.connect(builder1).submitAttestation(releaseId, HASH_AAA);
      await verifier.connect(builder2).submitAttestation(releaseId, HASH_AAA);
      await verifier.finalizeRelease(releaseId);

      await expect(
        verifier.connect(builder3).submitAttestation(releaseId, HASH_AAA)
      ).to.be.revertedWithCustomError(verifier, "ReleaseAlreadyFinalized")
        .withArgs(releaseId);
    });

    it("should prevent finalizing a release twice", async function () {
      await verifier.connect(builder1).submitAttestation(releaseId, HASH_AAA);
      await verifier.connect(builder2).submitAttestation(releaseId, HASH_AAA);
      await verifier.finalizeRelease(releaseId);

      await expect(
        verifier.finalizeRelease(releaseId)
      ).to.be.revertedWithCustomError(verifier, "ReleaseAlreadyFinalized")
        .withArgs(releaseId);
    });

    it("should revert if finalizing a non-existent release", async function () {
      await expect(
        verifier.finalizeRelease(999n)
      ).to.be.revertedWithCustomError(verifier, "ReleaseNotFound")
        .withArgs(999n);
    });

    it("should revert getRelease for unknown release", async function () {
      await expect(
        verifier.getRelease(999n)
      ).to.be.revertedWithCustomError(verifier, "ReleaseNotFound")
        .withArgs(999n);
    });

    it("should revert getAttestations for unknown release", async function () {
      await expect(
        verifier.getAttestations(999n)
      ).to.be.revertedWithCustomError(verifier, "ReleaseNotFound")
        .withArgs(999n);
    });

    it("should correctly retrieve all attestations", async function () {
      await verifier.connect(builder1).submitAttestation(releaseId, HASH_AAA);
      await verifier.connect(builder2).submitAttestation(releaseId, HASH_BBB);

      const attestations = await verifier.getAttestations(releaseId);
      expect(attestations.length).to.equal(2);
      expect(attestations[0].builder).to.equal(builder1.address);
      expect(attestations[0].artifactHash).to.equal(HASH_AAA);
      expect(attestations[1].builder).to.equal(builder2.address);
      expect(attestations[1].artifactHash).to.equal(HASH_BBB);
    });
  });
});
