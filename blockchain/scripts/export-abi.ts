import { artifacts } from "hardhat";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  console.log("Exporting QuorumVerifier ABI...");

  const artifact = await artifacts.readArtifact("QuorumVerifier");
  const deploymentsDir = path.resolve(__dirname, "../deployments");

  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir, { recursive: true });
  }

  // 1. Export standalone ABI JSON
  const abiPath = path.join(deploymentsDir, "QuorumVerifier.abi.json");
  fs.writeFileSync(abiPath, JSON.stringify(artifact.abi, null, 2), "utf-8");
  console.log(`ABI exported to: ${abiPath}`);

  // 2. If quorum-verifier.json exists, sync ABI
  const deploymentPath = path.join(deploymentsDir, "quorum-verifier.json");
  if (fs.existsSync(deploymentPath)) {
    const deploymentData = JSON.parse(fs.readFileSync(deploymentPath, "utf-8"));
    deploymentData.abi = artifact.abi;
    fs.writeFileSync(deploymentPath, JSON.stringify(deploymentData, null, 2), "utf-8");
    console.log(`Updated ABI in: ${deploymentPath}`);
  }

  console.log("QuorumVerifier ABI export complete.");
}

main().catch((error) => {
  console.error("Export ABI failed:", error);
  process.exit(1);
});
