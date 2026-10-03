import { ethers } from "ethers";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Decision enum mapping matching Solidity contract
enum Decision {
  NONE = 0,
  VERIFIED = 1,
  REJECTED = 2,
  DISPUTED = 3,
}

const DECISION_LABELS: Record<Decision, string> = {
  [Decision.NONE]: "NONE",
  [Decision.VERIFIED]: "VERIFIED",
  [Decision.REJECTED]: "REJECTED",
  [Decision.DISPUTED]: "DISPUTED",
};

// Deterministic Anvil dev private keys for local testing
const ANVIL_KEYS = [
  "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80", // Account 0 (Backend / Owner)
  "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d", // Account 1 (Builder A)
  "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a", // Account 2 (Builder B)
  "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6", // Account 3 (Builder C)
];

async function main() {
  console.log("==================================================");
  console.log("QUORUM VERIFICATION - END-TO-END BACKEND SERVICE EXAMPLE");
  console.log("==================================================");

  // 1. Connect to Anvil JSON-RPC
  const rpcUrl = process.env.RPC_URL || "http://127.0.0.1:8545";
  console.log(`Connecting to JSON-RPC at ${rpcUrl}...`);
  const provider = new ethers.JsonRpcProvider(rpcUrl);

  const network = await provider.getNetwork();
  console.log(`Connected to chain ID: ${network.chainId}`);

  // 2. Load deployment info
  const deploymentPath = path.resolve(__dirname, "../deployments/quorum-verifier.json");
  if (!fs.existsSync(deploymentPath)) {
    throw new Error(
      `Deployment file not found at ${deploymentPath}. Please run deploy script first.`
    );
  }

  const deployment = JSON.parse(fs.readFileSync(deploymentPath, "utf-8"));
  const contractAddress = deployment.contractAddress;
  const abi = deployment.abi;
  console.log(`Loaded QuorumVerifier at: ${contractAddress}\n`);

  // 3. Set up signers using Anvil unlocked accounts
  const backendSigner = await provider.getSigner(0);
  const builderASigner = await provider.getSigner(1);
  const builderBSigner = await provider.getSigner(2);
  const builderCSigner = await provider.getSigner(3);

  const contractAsBackend = new ethers.Contract(contractAddress, abi, backendSigner);
  const contractAsBuilderA = new ethers.Contract(contractAddress, abi, builderASigner);
  const contractAsBuilderB = new ethers.Contract(contractAddress, abi, builderBSigner);
  const contractAsBuilderC = new ethers.Contract(contractAddress, abi, builderCSigner);

  const HASH_AAA = ethers.sha256(ethers.toUtf8Bytes("artifact-v1.0.0-AAA"));
  const HASH_BBB = ethers.sha256(ethers.toUtf8Bytes("artifact-v1.0.0-BBB"));
  const HASH_CCC = ethers.sha256(ethers.toUtf8Bytes("artifact-v1.0.0-CCC"));

  // ------------------------------------------------------------
  // FLOW 1: VERIFIED DECISION (2/3 quorum matches published)
  // ------------------------------------------------------------
  console.log("--------------------------------------------------");
  console.log("FLOW 1: VERIFIED OUTCOME");
  console.log("Scenario: 2/3 builders produce HASH_AAA, published = HASH_AAA");
  console.log("--------------------------------------------------");

  const tx1 = await contractAsBackend.createRelease(
    "quorum/core",
    "commit-v1.0.0",
    HASH_AAA, // published hash is AAA
    3n,
    2n
  );
  const receipt1 = await tx1.wait();
  const relId1 = await getReleaseIdFromReceipt(contractAsBackend, receipt1);
  console.log(`1. Release created with ID: ${relId1}`);

  console.log("2. Builders submitting attestations...");
  await (await contractAsBuilderA.submitAttestation(relId1, HASH_AAA)).wait();
  await (await contractAsBuilderB.submitAttestation(relId1, HASH_AAA)).wait();
  await (await contractAsBuilderC.submitAttestation(relId1, HASH_BBB)).wait();

  console.log("3. Finalizing release...");
  await (await contractAsBackend.finalizeRelease(relId1)).wait();

  const rel1 = await contractAsBackend.getRelease(relId1);
  const dec1 = DECISION_LABELS[Number(rel1.decision) as Decision];
  console.log(`4. Result: Decision = ${dec1} (Expected: VERIFIED)`);
  console.log(`   Quorum Hash = ${rel1.quorumHash}\n`);

  // ------------------------------------------------------------
  // FLOW 2: REJECTED DECISION (2/3 quorum differs from published)
  // ------------------------------------------------------------
  console.log("--------------------------------------------------");
  console.log("FLOW 2: REJECTED OUTCOME");
  console.log("Scenario: 2/3 builders produce HASH_AAA, published = HASH_BBB");
  console.log("--------------------------------------------------");

  const tx2 = await contractAsBackend.createRelease(
    "quorum/core",
    "commit-v1.0.1",
    HASH_BBB, // published hash is BBB
    3n,
    2n
  );
  const receipt2 = await tx2.wait();
  const relId2 = await getReleaseIdFromReceipt(contractAsBackend, receipt2);
  console.log(`1. Release created with ID: ${relId2}`);

  console.log("2. Builders submitting attestations...");
  await (await contractAsBuilderA.submitAttestation(relId2, HASH_AAA)).wait();
  await (await contractAsBuilderB.submitAttestation(relId2, HASH_AAA)).wait();
  await (await contractAsBuilderC.submitAttestation(relId2, HASH_BBB)).wait();

  console.log("3. Finalizing release...");
  await (await contractAsBackend.finalizeRelease(relId2)).wait();

  const rel2 = await contractAsBackend.getRelease(relId2);
  const dec2 = DECISION_LABELS[Number(rel2.decision) as Decision];
  console.log(`4. Result: Decision = ${dec2} (Expected: REJECTED)`);
  console.log(`   Quorum Hash = ${rel2.quorumHash}`);
  console.log(`   Published Hash = ${rel2.publishedHash}\n`);

  // ------------------------------------------------------------
  // FLOW 3: DISPUTED DECISION (No hash reaches quorum)
  // ------------------------------------------------------------
  console.log("--------------------------------------------------");
  console.log("FLOW 3: DISPUTED OUTCOME");
  console.log("Scenario: 3 builders produce 3 distinct hashes (no 2/3 quorum)");
  console.log("--------------------------------------------------");

  const tx3 = await contractAsBackend.createRelease(
    "quorum/core",
    "commit-v1.0.2",
    HASH_AAA,
    3n,
    2n
  );
  const receipt3 = await tx3.wait();
  const relId3 = await getReleaseIdFromReceipt(contractAsBackend, receipt3);
  console.log(`1. Release created with ID: ${relId3}`);

  console.log("2. Builders submitting attestations...");
  await (await contractAsBuilderA.submitAttestation(relId3, HASH_AAA)).wait();
  await (await contractAsBuilderB.submitAttestation(relId3, HASH_BBB)).wait();
  await (await contractAsBuilderC.submitAttestation(relId3, HASH_CCC)).wait();

  console.log("3. Finalizing release...");
  await (await contractAsBackend.finalizeRelease(relId3)).wait();

  const rel3 = await contractAsBackend.getRelease(relId3);
  const dec3 = DECISION_LABELS[Number(rel3.decision) as Decision];
  console.log(`4. Result: Decision = ${dec3} (Expected: DISPUTED)`);
  console.log(`   Quorum Hash = ${rel3.quorumHash} (ZeroHash)\n`);

  console.log("==================================================");
  console.log("ALL 3 VERIFICATION FLOWS COMPLETED SUCCESSFULLY!");
  console.log("==================================================");
}

async function getReleaseIdFromReceipt(contract: ethers.Contract, receipt: any): Promise<bigint> {
  for (const log of receipt.logs) {
    try {
      const parsed = contract.interface.parseLog(log);
      if (parsed && parsed.name === "ReleaseCreated") {
        return parsed.args.releaseId;
      }
    } catch {
      // ignore
    }
  }
  return 0n;
}

main().catch((err) => {
  console.error("Example flow failed:", err);
  process.exit(1);
});
