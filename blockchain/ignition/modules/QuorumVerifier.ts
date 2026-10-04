import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

export default buildModule("QuorumVerifierModule", (m) => {
  const quorumVerifier = m.contract("QuorumVerifier");

  return { quorumVerifier };
});
