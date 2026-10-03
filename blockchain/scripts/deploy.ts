import { network, artifacts, globalOptions } from "hardhat";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  const targetNetwork = globalOptions.network || "localhost";
  console.log(`Connecting to network: ${targetNetwork}...`);

  const connection = await network.create(targetNetwork);
  const { ethers } = connection;

  const signers = await ethers.getSigners();
  if (signers.length === 0) {
    throw new Error("No signers found. Make sure the network/Anvil node is running.");
  }

  const deployer = signers[0];
  console.log(`Deploying QuorumVerifier with deployer account: ${deployer.address}`);

  const verifier = await ethers.deployContract("QuorumVerifier", [], deployer);
  await verifier.waitForDeployment();
  const contractAddress = await verifier.getAddress();
  console.log(`QuorumVerifier deployed to: ${contractAddress}`);

  // Determine builder addresses
  const b1 =
    process.env.BUILDER_1_ADDRESS ||
    (signers[1] ? signers[1].address : "0x70997970C51812dc3A010C7d01b50e0d17dc79C8");
  const b2 =
    process.env.BUILDER_2_ADDRESS ||
    (signers[2] ? signers[2].address : "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC");
  const b3 =
    process.env.BUILDER_3_ADDRESS ||
    (signers[3] ? signers[3].address : "0x90F79bf6EB2c4f870365E785982E1f101E93b906");

  console.log(`Registering builder accounts on-chain:`);
  console.log(`  Builder 1: ${b1}`);
  console.log(`  Builder 2: ${b2}`);
  console.log(`  Builder 3: ${b3}`);

  const regTx = await verifier.registerBuilders([b1, b2, b3]);
  await regTx.wait();
  console.log(`Builders successfully registered.`);

  // Read artifact ABI
  const artifact = await artifacts.readArtifact("QuorumVerifier");

  // Get network details
  const networkDetails = await ethers.provider.getNetwork();
  const chainId = Number(networkDetails.chainId);

  const deploymentData = {
    network: targetNetwork,
    rpcUrl:
      targetNetwork === "anvil" || targetNetwork === "localhost"
        ? "http://127.0.0.1:8545"
        : "",
    chainId: chainId,
    contractAddress: contractAddress,
    deployer: deployer.address,
    builders: [b1, b2, b3],
    abi: artifact.abi,
  };

  const deploymentsDir = path.resolve(__dirname, "../deployments");
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir, { recursive: true });
  }

  const deploymentPath = path.join(deploymentsDir, "quorum-verifier.json");
  fs.writeFileSync(deploymentPath, JSON.stringify(deploymentData, null, 2), "utf-8");
  console.log(`Deployment metadata written to: ${deploymentPath}`);

  const abiPath = path.join(deploymentsDir, "QuorumVerifier.abi.json");
  fs.writeFileSync(abiPath, JSON.stringify(artifact.abi, null, 2), "utf-8");
  console.log(`Standalone ABI written to: ${abiPath}`);

  console.log("\n==================================================");
  console.log("DEPLOYMENT COMPLETE");
  console.log("==================================================");
  console.log(`Network:          ${targetNetwork}`);
  console.log(`Chain ID:         ${chainId}`);
  console.log(`Contract Address: ${contractAddress}`);
  console.log(`Deployer:         ${deployer.address}`);
  console.log(`Builder 1:        ${b1}`);
  console.log(`Builder 2:        ${b2}`);
  console.log(`Builder 3:        ${b3}`);
  console.log("==================================================\n");
}

main().catch((err) => {
  console.error("Deployment failed:", err);
  process.exit(1);
});
