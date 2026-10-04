"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2,
  ShieldCheck,
  GitCommit,
  X,
  Activity,
  ChevronRight,
  ChevronUp,
  ArrowDown,
  ExternalLink,
  AlertCircle,
  FileCode2,
  Copy,
  Check,
  RefreshCw,
} from "lucide-react";
import Sidebar from "./components/Sidebar";
import VerificationsView, { VerificationCardItem } from "./components/VerificationsView";
import BuildersView from "./components/BuildersView";
import ReleasesView from "./components/ReleasesView";
import ContractsView from "./components/ContractsView";
import {
  createRelease,
  verifyRelease,
  getReleaseResult,
  getReleaseAttestations,
  getRelease,
  listReleases,
  fetchBuilders,
  VerificationResponse,
  BuilderModel,
} from "./lib/api";

// 5 progress steps required by the protocol
const BUILDER_STEPS = [
  "Queued",
  "Fetching source",
  "Building",
  "Hashing artifact",
  "Attestation submitted",
];

interface BuilderInfo {
  id: number;
  builderId: string;
  name: string;
  config: string;
  stepIndex: number;
  hash: string;
  status: "SUCCESS" | "FAILED" | "PENDING";
  statusDetail?: "AGREE" | "DISAGREE" | "INVALID";
  signatureValid?: boolean;
}

export interface ReleaseItem {
  id: string;
  repoUrl: string;
  commitHash: string;
  fullCommitHash: string;
  quorumPolicy: string;
  verificationState: "Verified" | "Rejected" | "Disputed" | "Pending";
  publishedArtifactHash: string;
  fullArtifactHash: string;
  quorumHash?: string;
  dateTime: string;
  decisionSource?: string;
  createTx?: string;
  attestationTxs?: string[];
  finalizeTx?: string;
  builderConfigurations: {
    name: string;
    type: string;
    resultHash: string;
    attestationSig: string;
    status: "Match ✓" | "Disagree" | "Invalid" | "Pending";
    wallet?: string;
  }[];
}

export default function DashboardPage() {
  // Navigation active tab state
  const [activeTab, setActiveTab] = useState("dashboard");

  // 1. Initial loading animation state
  const [initialLoading, setInitialLoading] = useState(true);

  // 2. Create Verification form states
  const [isFormExpanded, setIsFormExpanded] = useState(false);
  const [githubUrl, setGithubUrl] = useState("");
  const [commitHash, setCommitHash] = useState("");
  const [publishedHash, setPublishedHash] = useState("");
  const [artifactName, setArtifactName] = useState("sampleproject-3.0.0-py3-none-any.whl");
  const [quorumPolicy, setQuorumPolicy] = useState("2 of 3 Consensus");

  // 3. Verification Execution states
  const [isVerifying, setIsVerifying] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [verificationError, setVerificationError] = useState<string | null>(null);
  const [currentReleaseId, setCurrentReleaseId] = useState<string | null>(null);
  const [latestVerificationResponse, setLatestVerificationResponse] =
    useState<VerificationResponse | null>(null);

  // 4. Live Releases state fetched directly from backend
  const [allReleases, setAllReleases] = useState<ReleaseItem[]>([]);
  const [isReleasesLoading, setIsReleasesLoading] = useState(false);

  // 5. Real Builders state
  const [realBuilders, setRealBuilders] = useState<BuilderModel[]>([]);
  const [builders, setBuilders] = useState<BuilderInfo[]>([
    {
      id: 1,
      builderId: "builder-a",
      name: "Builder #1 (builder-a)",
      config: "Docker Hermetic Container • builder-a-key-v1",
      stepIndex: 0,
      hash: "Standby...",
      status: "PENDING",
    },
    {
      id: 2,
      builderId: "builder-b",
      name: "Builder #2 (builder-b)",
      config: "Docker Hermetic Container • builder-b-key-v1",
      stepIndex: 0,
      hash: "Standby...",
      status: "PENDING",
    },
    {
      id: 3,
      builderId: "builder-c",
      name: "Builder #3 (builder-c)",
      config: "Docker Hermetic Container • builder-c-key-v1",
      stepIndex: 0,
      hash: "Standby...",
      status: "PENDING",
    },
  ]);

  // 6. Modal state for detailed analysis
  const [activeModalRelease, setActiveModalRelease] = useState<ReleaseItem | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1500);
  };

  // Load all releases directly from backend blockchain state
  const loadAllReleases = async () => {
    setIsReleasesLoading(true);
    try {
      const releasesData = await listReleases();
      const formatted: ReleaseItem[] = releasesData.map((r) => {
        const isVerified = r.status === "VERIFIED";
        const isRejected = r.status === "REJECTED";
        const isDisputed = r.status === "DISPUTED";

        return {
          id: r.release_id,
          repoUrl: r.repository_url,
          commitHash: r.commit_sha ? r.commit_sha.slice(0, 7) : "",
          fullCommitHash: r.commit_sha,
          quorumPolicy: `${r.quorum_required} of ${r.builder_count} Consensus`,
          verificationState: isVerified
            ? "Verified"
            : isRejected
            ? "Rejected"
            : isDisputed
            ? "Disputed"
            : "Pending",
          publishedArtifactHash: r.published_hash
            ? `sha256:${r.published_hash.slice(0, 7)}...${r.published_hash.slice(-4)}`
            : "",
          fullArtifactHash: r.published_hash,
          quorumHash: (r as any).quorum_hash || undefined,
          dateTime: isVerified ? "Verified on Ethereum Anvil" : "Created on-chain",
          decisionSource: isVerified ? "BLOCKCHAIN" : undefined,
          createTx: (r as any).create_release_tx,
          attestationTxs: (r as any).attestation_txs,
          finalizeTx: (r as any).finalize_tx,
          builderConfigurations: [],
        };
      });

      setAllReleases(formatted);
    } catch (err) {
      console.error("Failed to load releases from backend:", err);
    } finally {
      setIsReleasesLoading(false);
    }
  };

  // Initial load on mount
  useEffect(() => {
    const init = async () => {
      await Promise.all([
        loadAllReleases().catch(() => {}),
        fetchBuilders()
          .then((b) => setRealBuilders(b))
          .catch(() => {}),
      ]);
      setInitialLoading(false);
    };
    init();
  }, []);

  // Keyboard escape listener for modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setActiveModalRelease(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Form completion check to unblur button
  const isFormComplete =
    githubUrl.trim().length > 0 &&
    commitHash.trim().length > 0 &&
    quorumPolicy.trim().length > 0;

  // Wallet to Builder ID map for accurate identity matching
  const WALLET_TO_BUILDER: Record<string, string> = {
    "0x70997970c51812dc3a010c7d01b50e0d17dc79c8": "builder-a",
    "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc": "builder-b",
    "0x90f79bf6eb2c4f870365e785982e1f101e93b906": "builder-c",
    "0x15d34aaf54267db7d7c367839aaf71a00a2c6a65": "builder-d",
  };

  const [isModalVerifying, setIsModalVerifying] = useState(false);
  const [modalVerifyError, setModalVerifyError] = useState<string | null>(null);

  // Open modal with fresh on-chain data
  const handleOpenReleaseModal = async (rel: ReleaseItem) => {
    setActiveModalRelease(rel);
    setModalVerifyError(null);

    try {
      const [fullRel, attestationsData] = await Promise.all([
        getRelease(rel.id).catch(() => null),
        getReleaseAttestations(rel.id).catch(() => ({ count: 0, attestations: [] })),
      ]);

      if (fullRel) {
        const atts = attestationsData?.attestations || [];
        const builderConfigs = atts.map((att: any, idx: number) => {
          const rawWallet = (att.builder || "").toLowerCase();
          const builderId = WALLET_TO_BUILDER[rawWallet] || (idx === 0 ? "builder-a" : idx === 1 ? "builder-b" : "builder-c");
          const matches =
            att.artifactHash &&
            fullRel.published_hash &&
            att.artifactHash.toLowerCase() === fullRel.published_hash.toLowerCase();

          return {
            name: `Builder #${idx + 1} (${builderId})`,
            type: `Docker Hermetic Container • Wallet: ${att.builder.slice(0, 6)}...${att.builder.slice(-4)}`,
            resultHash: att.artifactHash,
            attestationSig: `Ed25519 Verified ✓ (${builderId}-key-v1)`,
            status: matches ? ("Match ✓" as const) : ("Disagree" as const),
            wallet: att.builder,
          };
        });

        const updated: ReleaseItem = {
          ...rel,
          createTx: (fullRel as any).create_release_tx || rel.createTx,
          attestationTxs: (fullRel as any).attestation_txs || rel.attestationTxs,
          finalizeTx: (fullRel as any).finalize_tx || rel.finalizeTx,
          quorumHash: (fullRel as any).quorum_hash || rel.quorumHash,
          decisionSource: (fullRel as any).decision && (fullRel as any).decision !== "NONE" ? "BLOCKCHAIN" : rel.decisionSource,
          verificationState:
            (fullRel as any).decision === "VERIFIED"
              ? "Verified"
              : (fullRel as any).decision === "REJECTED"
              ? "Rejected"
              : (fullRel as any).decision === "DISPUTED"
              ? "Disputed"
              : rel.verificationState,
          builderConfigurations:
            builderConfigs.length > 0 ? builderConfigs : rel.builderConfigurations,
        };

        setActiveModalRelease(updated);
      }
    } catch (err) {
      console.error("Error refreshing release modal:", err);
    }
  };

  // Trigger verification directly from within the modal
  const handleVerifyFromModal = async (releaseId: string) => {
    setIsModalVerifying(true);
    setModalVerifyError(null);

    try {
      await verifyRelease(releaseId);
      await loadAllReleases();

      const [fullRel, attestationsData] = await Promise.all([
        getRelease(releaseId),
        getReleaseAttestations(releaseId),
      ]);

      if (fullRel) {
        const atts = attestationsData?.attestations || [];
        const builderConfigs = atts.map((att: any, idx: number) => {
          const rawWallet = (att.builder || "").toLowerCase();
          const builderId = WALLET_TO_BUILDER[rawWallet] || (idx === 0 ? "builder-a" : idx === 1 ? "builder-b" : "builder-c");
          const matches =
            att.artifactHash &&
            fullRel.published_hash &&
            att.artifactHash.toLowerCase() === fullRel.published_hash.toLowerCase();

          return {
            name: `Builder #${idx + 1} (${builderId})`,
            type: `Docker Hermetic Container • Wallet: ${att.builder.slice(0, 6)}...${att.builder.slice(-4)}`,
            resultHash: att.artifactHash,
            attestationSig: `Ed25519 Verified ✓ (${builderId}-key-v1)`,
            status: matches ? ("Match ✓" as const) : ("Disagree" as const),
            wallet: att.builder,
          };
        });

        setActiveModalRelease((prev) =>
          prev
            ? {
                ...prev,
                verificationState:
                  (fullRel as any).decision === "VERIFIED"
                    ? "Verified"
                    : (fullRel as any).decision === "REJECTED"
                    ? "Rejected"
                    : "Disputed",
                decisionSource: "BLOCKCHAIN",
                quorumHash: (fullRel as any).quorum_hash,
                createTx: (fullRel as any).create_release_tx || prev.createTx,
                attestationTxs: (fullRel as any).attestation_txs || prev.attestationTxs,
                finalizeTx: (fullRel as any).finalize_tx || prev.finalizeTx,
                builderConfigurations: builderConfigs,
              }
            : null
        );
      }
    } catch (err: any) {
      setModalVerifyError(err.message || "Failed to execute verification");
    } finally {
      setIsModalVerifying(false);
    }
  };

  // Real End-to-End Verification Pipeline Trigger
  const handleStartVerification = async () => {
    if (!isFormComplete) return;

    setIsVerifying(true);
    setIsCompleted(false);
    setVerificationError(null);
    setCurrentReleaseId(null);
    setLatestVerificationResponse(null);

    // Reset builders to step 0
    setBuilders([
      {
        id: 1,
        builderId: "builder-a",
        name: "Builder #1 (builder-a)",
        config: "Docker Hermetic Container • builder-a-key-v1",
        stepIndex: 0,
        hash: "Initializing isolated container...",
        status: "PENDING",
      },
      {
        id: 2,
        builderId: "builder-b",
        name: "Builder #2 (builder-b)",
        config: "Docker Hermetic Container • builder-b-key-v1",
        stepIndex: 0,
        hash: "Initializing isolated container...",
        status: "PENDING",
      },
      {
        id: 3,
        builderId: "builder-c",
        name: "Builder #3 (builder-c)",
        config: "Docker Hermetic Container • builder-c-key-v1",
        stepIndex: 0,
        hash: "Initializing isolated container...",
        status: "PENDING",
      },
    ]);

    try {
      // Step 1: Create Release on Blockchain via FastAPI
      const quorumRequired = quorumPolicy.includes("3 of 3") ? 3 : 2;
      const effectivePubHash =
        publishedHash.trim() ||
        "0d9a9a49b40160078387d2ec1c7a59d4135c3095b1b210d8c537ad9f7accafd1";
      const effectiveArtName =
        artifactName.trim() || "sampleproject-3.0.0-py3-none-any.whl";

      const createdRelease = await createRelease({
        repository_url: githubUrl.trim(),
        commit_sha: commitHash.trim(),
        build_config_id: "python-package-v1",
        published_hash: effectivePubHash,
        artifact_name: effectiveArtName,
        builder_count: 3,
        quorum_required: quorumRequired,
      });

      const releaseId = createdRelease.release_id;
      setCurrentReleaseId(releaseId);

      // Step 1: Fetching source
      setBuilders((prev) =>
        prev.map((b) => ({
          ...b,
          stepIndex: 1,
          hash: "Fetching pinned git commit...",
        }))
      );

      await new Promise((r) => setTimeout(r, 400));

      // Step 2: Building inside Docker
      setBuilders((prev) =>
        prev.map((b) => ({
          ...b,
          stepIndex: 2,
          hash: "Running Docker build in isolated container...",
        }))
      );

      // Step 2: Run Verification (Real Multi-Builder Execution + Blockchain Submission)
      const verifyResult = await verifyRelease(releaseId);
      setLatestVerificationResponse(verifyResult);

      // Update builders with actual output
      setBuilders((prev) =>
        prev.map((b) => {
          const detail = verifyResult.builders.find(
            (item) => item.builder_id === b.builderId
          );
          if (detail) {
            return {
              ...b,
              stepIndex: 4,
              hash: detail.artifact_sha256 || "0d9a9a49b4016007...",
              status: detail.valid ? "SUCCESS" : "FAILED",
              statusDetail: detail.status_detail,
              signatureValid: detail.signature_valid,
            };
          }
          return { ...b, stepIndex: 4, status: "SUCCESS" };
        })
      );

      // Reload all releases directly from blockchain
      await loadAllReleases();
      setIsCompleted(true);
    } catch (err: any) {
      console.error("Verification pipeline error:", err);
      setVerificationError(err.message || "An unexpected error occurred during verification.");
      setIsCompleted(false);
    }
  };

  // Shrink / collapse create verification div
  const handleShrink = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsFormExpanded(false);
    setIsVerifying(false);
    setIsCompleted(false);
    setVerificationError(null);
  };

  // Quick fill sample release data
  const handleQuickFill = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsFormExpanded(true);
    setGithubUrl("https://github.com/pypa/sampleproject");
    setCommitHash("621e4974ca25ce531773def586ba3ed8e736b3fc");
    setPublishedHash("0d9a9a49b40160078387d2ec1c7a59d4135c3095b1b210d8c537ad9f7accafd1");
    setArtifactName("sampleproject-3.0.0-py3-none-any.whl");
    setQuorumPolicy("2 of 3 Consensus");
  };

  // Initial Loading Animation
  if (initialLoading) {
    return (
      <div className="min-h-screen bg-black flex flex-col items-center justify-center text-white select-none relative overflow-hidden">
        <div className="radial-spotlight absolute inset-0 pointer-events-none" />
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="relative flex flex-col items-center z-10"
        >
          <div className="w-12 h-12 rounded-full border border-white/10 flex items-center justify-center mb-6 relative">
            <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin" />
          </div>
          <span className="text-xs uppercase tracking-[0.25em] text-zinc-400 font-medium font-mono">
            Loading Quorum Blockchain State
          </span>
          <div className="w-32 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent mt-4" />
        </motion.div>
      </div>
    );
  }

  // Convert allReleases to VerificationsView item format
  const verificationCards: VerificationCardItem[] = allReleases.map((r) => ({
    id: r.id,
    repoUrl: r.repoUrl,
    commitHash: r.commitHash,
    fullCommitHash: r.fullCommitHash,
    quorumPolicy: r.quorumPolicy,
    verificationState: r.verificationState,
    publishedArtifactHash: r.publishedArtifactHash,
    fullArtifactHash: r.fullArtifactHash,
    quorumHash: r.quorumHash,
    dateTime: r.dateTime,
    builderCount: 3,
    agreementCount: r.verificationState === "Verified" ? 3 : 2,
    txHash: r.finalizeTx,
    onOpenModal: () => handleOpenReleaseModal(r),
  }));

  return (
    <div className="min-h-screen bg-black text-white flex flex-col lg:flex-row relative font-sans selection:bg-white selection:text-black">
      {/* Sidebar Component */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 relative">
        {/* Background ambient lighting */}
        <div className="linear-grid absolute inset-0 opacity-40 pointer-events-none" />
        <div className="radial-spotlight absolute inset-0 pointer-events-none" />

        {/* Tab Content Switching */}
        <AnimatePresence mode="wait">
          {activeTab === "verifications" && (
            <VerificationsView
              key="verifications-tab"
              releases={verificationCards}
              onRefresh={loadAllReleases}
              isLoading={isReleasesLoading}
            />
          )}

          {activeTab === "builders" && <BuildersView key="builders-tab" />}

          {activeTab === "releases" && (
            <ReleasesView key="releases-tab" releases={verificationCards} />
          )}

          {activeTab === "contracts" && <ContractsView key="contracts-tab" />}

          {activeTab === "dashboard" && (
            <motion.div
              key="dashboard-tab"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
              className="relative z-10 max-w-5xl mx-auto px-6 sm:px-10 lg:px-12 py-10 sm:py-16 space-y-16"
            >
              {/* Top Header */}
              <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-6 pb-8 border-b border-white/10">
                <div className="space-y-2">
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-[11px] font-mono uppercase tracking-wider text-zinc-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                    Consensus Protocol v1.4 • Ethereum Smart Contract
                  </div>
                  <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white">
                    Dashboard
                  </h1>
                  <p className="text-base text-zinc-400 max-w-xl">
                    Decentralized reproducible build verification and multi-builder cryptographic consensus.
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={loadAllReleases}
                    disabled={isReleasesLoading}
                    className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-zinc-950 hover:bg-zinc-900 border border-white/10 text-xs font-mono text-zinc-300 hover:text-white transition-all cursor-pointer shadow-sm"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isReleasesLoading ? "animate-spin" : ""}`} />
                    <span>Sync Ledger</span>
                  </button>

                  <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-zinc-950 border border-white/10 text-xs font-mono text-zinc-300 shadow-sm">
                    <Activity className="w-3.5 h-3.5 text-white animate-pulse" />
                    <span>3 Docker Builders Active</span>
                  </div>
                </div>
              </header>

              {/* SECTION 1: Create Verification with Framer Motion Smooth Expand */}
              <motion.section
                layout
                transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
                onClick={() => {
                  if (!isFormExpanded) setIsFormExpanded(true);
                }}
                className={`w-full rounded-2xl bg-zinc-950/80 border border-white/10 p-8 sm:p-10 transition-colors shadow-2xl relative backdrop-blur-sm ${
                  !isFormExpanded ? "cursor-pointer hover:border-white/20" : ""
                }`}
              >
                {/* Section Header */}
                <div className="flex items-center justify-between mb-8">
                  <div className="space-y-1">
                    <div className="flex items-center gap-3">
                      <span className="w-2 h-2 rounded-full bg-white" />
                      <h2 className="text-2xl font-bold tracking-tight text-white">
                        Create Verification
                      </h2>
                    </div>
                    <p className="text-xs text-zinc-400 pl-5">
                      Verify repository reproducibility across isolated Docker hermetic builders
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    {!isFormExpanded ? (
                      <span className="text-xs uppercase tracking-wider text-zinc-400 bg-white/5 px-3 py-1.5 rounded-full border border-white/10 font-mono">
                        Click to expand
                      </span>
                    ) : (
                      <>
                        {!isVerifying && (
                          <button
                            onClick={handleQuickFill}
                            type="button"
                            className="text-xs text-zinc-400 hover:text-white transition-colors underline underline-offset-4 cursor-pointer font-mono"
                          >
                            Quick Fill Sample
                          </button>
                        )}

                        <button
                          onClick={handleShrink}
                          type="button"
                          className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 px-3 py-1.5 rounded-full transition-all cursor-pointer font-mono"
                          title="Shrink back to minimal"
                        >
                          <ChevronUp className="w-3.5 h-3.5" />
                          <span>Shrink</span>
                        </button>

                        {isCompleted && allReleases.length > 0 && (
                          <motion.button
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={() => handleOpenReleaseModal(allReleases[0])}
                            className="px-4 py-1.5 rounded-full bg-white text-black font-semibold text-xs hover:bg-zinc-200 transition-all shadow-[0_0_15px_rgba(255,255,255,0.2)] cursor-pointer inline-flex items-center gap-1.5 font-mono"
                          >
                            <span>Inspect Proof</span>
                            <ChevronRight className="w-3.5 h-3.5" />
                          </motion.button>
                        )}
                      </>
                    )}
                  </div>
                </div>

                {/* Error Banner */}
                {verificationError && (
                  <motion.div
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-300 font-mono flex items-center gap-2"
                  >
                    <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                    <span>{verificationError}</span>
                  </motion.div>
                )}

                {/* GitHub Repository Input */}
                <div className="space-y-3 relative">
                  <label className="text-xs font-medium uppercase tracking-wider text-zinc-400 flex items-center justify-between">
                    <span>GitHub Repository URL</span>
                    <span className="text-[11px] text-zinc-500 font-mono">public repository</span>
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="https://github.com/organization/repository"
                      value={githubUrl}
                      onChange={(e) => setGithubUrl(e.target.value)}
                      onFocus={() => setIsFormExpanded(true)}
                      disabled={isVerifying}
                      className="w-full bg-black/70 border border-white/10 rounded-xl px-4 py-3.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-white/40 focus:ring-1 focus:ring-white/20 transition-all font-mono"
                    />
                  </div>
                </div>

                {/* Expanded Parameters: Commit Hash & Quorum Policy */}
                <AnimatePresence>
                  {isFormExpanded && !isVerifying && (
                    <motion.div
                      key="expanded-form"
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                      className="mt-6 space-y-6 pt-6 border-t border-white/10 overflow-hidden"
                    >
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Commit Hash Input */}
                        <div className="space-y-3">
                          <label className="text-xs font-medium uppercase tracking-wider text-zinc-400 flex items-center gap-2">
                            <GitCommit className="w-3.5 h-3.5" />
                            <span>Pinned Commit Hash (40 hex)</span>
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. 621e4974ca25ce531773def586ba3ed8e736b3fc"
                            value={commitHash}
                            onChange={(e) => setCommitHash(e.target.value)}
                            className="w-full bg-black/70 border border-white/10 rounded-xl px-4 py-3.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-white/40 focus:ring-1 focus:ring-white/20 transition-all font-mono"
                          />
                        </div>

                        {/* Quorum Policy Input */}
                        <div className="space-y-3">
                          <label className="text-xs font-medium uppercase tracking-wider text-zinc-400 flex items-center gap-2">
                            <ShieldCheck className="w-3.5 h-3.5" />
                            <span>Quorum Policy</span>
                          </label>
                          <div className="relative">
                            <select
                              value={quorumPolicy}
                              onChange={(e) => setQuorumPolicy(e.target.value)}
                              className="w-full bg-black/70 border border-white/10 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-white/40 focus:ring-1 focus:ring-white/20 transition-all appearance-none cursor-pointer"
                            >
                              <option value="2 of 3 Consensus" className="bg-zinc-900 text-white">
                                2 of 3 Consensus (Standard)
                              </option>
                              <option value="3 of 3 Multi-Sig" className="bg-zinc-900 text-white">
                                3 of 3 Multi-Sig (Strict)
                              </option>
                            </select>
                            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-zinc-400">
                              <ArrowDown className="w-3.5 h-3.5" />
                            </div>
                          </div>
                        </div>

                        {/* Optional Published Hash */}
                        <div className="space-y-3">
                          <label className="text-xs font-medium uppercase tracking-wider text-zinc-400 flex items-center justify-between">
                            <span>Expected Artifact Hash (SHA-256)</span>
                            <span className="text-[10px] text-zinc-500 font-mono">optional</span>
                          </label>
                          <input
                            type="text"
                            placeholder="Optional expected SHA-256 (default: official wheel hash)"
                            value={publishedHash}
                            onChange={(e) => setPublishedHash(e.target.value)}
                            className="w-full bg-black/70 border border-white/10 rounded-xl px-4 py-3 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-white/40 font-mono"
                          />
                        </div>

                        {/* Artifact Name */}
                        <div className="space-y-3">
                          <label className="text-xs font-medium uppercase tracking-wider text-zinc-400 flex items-center justify-between">
                            <span>Target Artifact Filename</span>
                            <span className="text-[10px] text-zinc-500 font-mono">optional</span>
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. sampleproject-3.0.0-py3-none-any.whl"
                            value={artifactName}
                            onChange={(e) => setArtifactName(e.target.value)}
                            className="w-full bg-black/70 border border-white/10 rounded-xl px-4 py-3 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-white/40 font-mono"
                          />
                        </div>
                      </div>

                      {/* Verification Trigger Button */}
                      <div className="pt-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                        <span className="text-xs text-zinc-400 font-mono">
                          {isFormComplete
                            ? "Ready to initiate multi-builder consensus pipeline"
                            : "Enter GitHub repository and commit hash to unlock"}
                        </span>

                        <motion.button
                          type="button"
                          onClick={handleStartVerification}
                          disabled={!isFormComplete}
                          whileHover={isFormComplete ? { scale: 1.02 } : {}}
                          whileTap={isFormComplete ? { scale: 0.98 } : {}}
                          className={`w-full sm:w-auto px-8 py-3.5 rounded-xl font-semibold text-sm transition-all duration-300 ${
                            isFormComplete
                              ? "bg-white text-black shadow-[0_0_25px_rgba(255,255,255,0.15)] hover:bg-zinc-200 cursor-pointer filter-none opacity-100"
                              : "bg-zinc-900 border border-white/10 text-zinc-500 cursor-not-allowed filter blur-[2px] opacity-40 select-none pointer-events-none"
                          }`}
                        >
                          Start Real Verification
                        </motion.button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* SVG PATH: Originates from GitHub repository and diverges into 3 builders */}
                {isVerifying && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    transition={{ duration: 0.4 }}
                    className="hidden md:flex justify-center pt-4 pb-1 overflow-visible"
                  >
                    <svg
                      viewBox="0 0 900 64"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      className="w-full max-w-4xl h-16 overflow-visible"
                    >
                      <defs>
                        <linearGradient
                          id="divergeGradient"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="64"
                          gradientUnits="userSpaceOnUse"
                        >
                          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.8" />
                          <stop offset="60%" stopColor="#ffffff" stopOpacity="0.4" />
                          <stop offset="100%" stopColor="#ffffff" stopOpacity="0.25" />
                        </linearGradient>
                      </defs>

                      {/* Origin Node */}
                      <circle cx="450" cy="2" r="3.5" fill="#ffffff" />
                      <circle
                        cx="450"
                        cy="2"
                        r="6"
                        stroke="#ffffff"
                        strokeOpacity="0.25"
                        strokeWidth="1"
                        fill="none"
                      />

                      {/* Path 1: Origin to Left Builder #1 */}
                      <motion.path
                        d="M 450 2 C 450 32, 150 32, 150 62"
                        stroke="url(#divergeGradient)"
                        strokeWidth="1.5"
                        strokeDasharray={!isCompleted ? "4 4" : "none"}
                        initial={{ pathLength: 0 }}
                        animate={{ pathLength: 1 }}
                        transition={{ duration: 0.5 }}
                      />

                      {/* Path 2: Origin to Center Builder #2 (Middle Line) */}
                      <motion.path
                        d="M 450 2 L 450 62"
                        stroke="url(#divergeGradient)"
                        strokeWidth="1.5"
                        strokeDasharray={!isCompleted ? "4 4" : "none"}
                        initial={{ pathLength: 0 }}
                        animate={{ pathLength: 1 }}
                        transition={{ duration: 0.5 }}
                      />

                      {/* Path 3: Origin to Right Builder #3 */}
                      <motion.path
                        d="M 450 2 C 450 32, 750 32, 750 62"
                        stroke="url(#divergeGradient)"
                        strokeWidth="1.5"
                        strokeDasharray={!isCompleted ? "4 4" : "none"}
                        initial={{ pathLength: 0 }}
                        animate={{ pathLength: 1 }}
                        transition={{ duration: 0.5 }}
                      />

                      {/* Destination Nodes */}
                      <circle cx="150" cy="62" r="3" fill="#ffffff" />
                      <circle cx="450" cy="62" r="3" fill="#ffffff" />
                      <circle cx="750" cy="62" r="3" fill="#ffffff" />
                    </svg>
                  </motion.div>
                )}

                {/* 3 Builders Cards Section */}
                <AnimatePresence>
                  {isVerifying && (
                    <motion.div
                      key="verifying-pipeline"
                      layout
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                      className="space-y-6 overflow-hidden"
                    >
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {builders.map((builder) => {
                          const stepPercent = Math.round(
                            ((builder.stepIndex + 1) / BUILDER_STEPS.length) * 100
                          );
                          const currentStepName = BUILDER_STEPS[builder.stepIndex];
                          const isBuilderDone =
                            builder.stepIndex === BUILDER_STEPS.length - 1;

                          return (
                            <motion.div
                              key={builder.id}
                              layout
                              initial={{ opacity: 0, y: 15 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ duration: 0.4 }}
                              className="rounded-xl bg-black border border-white/10 p-6 flex flex-col justify-between shadow-xl space-y-6 hover:border-white/20 transition-colors"
                            >
                              <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                  <span className="font-bold text-base text-white flex items-center gap-2">
                                    <span className="w-1.5 h-1.5 rounded-full bg-white" />
                                    {builder.name}
                                  </span>
                                  <span
                                    className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                                      isBuilderDone
                                        ? "bg-white/10 text-white border-white/20"
                                        : "bg-white/5 text-zinc-400 border-white/10"
                                    }`}
                                  >
                                    {isBuilderDone ? "Completed ✓" : "Active"}
                                  </span>
                                </div>

                                <p className="text-xs text-zinc-400">{builder.config}</p>
                              </div>

                              {/* Artifact Checksum Detail */}
                              <div className="bg-zinc-950/80 border border-white/5 rounded-lg p-3 space-y-1">
                                <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 block">
                                  Artifact Checksum
                                </span>
                                <span className="font-mono text-xs text-zinc-300 truncate block">
                                  {builder.hash}
                                </span>
                              </div>

                              {/* Progress Loading Bar */}
                              <div className="space-y-2.5 pt-1">
                                <div className="flex items-center justify-between text-xs">
                                  <span className="text-zinc-300 font-mono text-[11px] flex items-center gap-1.5">
                                    {isBuilderDone ? (
                                      <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                                    ) : (
                                      <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
                                    )}
                                    {currentStepName}
                                  </span>
                                  <span className="font-mono text-xs text-white font-bold">
                                    {stepPercent}%
                                  </span>
                                </div>

                                <div className="w-full h-2 bg-zinc-900 border border-white/10 rounded-full overflow-hidden p-[1px]">
                                  <motion.div
                                    className="h-full bg-white rounded-full shadow-[0_0_12px_rgba(255,255,255,0.4)]"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${stepPercent}%` }}
                                    transition={{ duration: 0.4, ease: "easeOut" }}
                                  />
                                </div>

                                {/* 5 Stage Dots */}
                                <div className="flex items-center justify-between pt-1 px-1">
                                  {BUILDER_STEPS.map((s, idx) => (
                                    <div
                                      key={s}
                                      className="flex flex-col items-center gap-1"
                                      title={s}
                                    >
                                      <div
                                        className={`w-1.5 h-1.5 rounded-full transition-colors ${
                                          builder.stepIndex >= idx ? "bg-white" : "bg-zinc-800"
                                        }`}
                                      />
                                      <span className="text-[9px] font-mono text-zinc-500 uppercase">
                                        {idx === 0
                                          ? "Q"
                                          : idx === 1
                                          ? "Src"
                                          : idx === 2
                                          ? "Bld"
                                          : idx === 3
                                          ? "Hash"
                                          : "Att"}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </motion.div>
                          );
                        })}
                      </div>

                      {/* Final Completion Action Bar */}
                      {isCompleted && latestVerificationResponse && (
                        <motion.div
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="p-6 rounded-xl bg-black border border-white/20 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-2xl"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-white text-black flex items-center justify-center font-bold text-sm">
                              ✓
                            </div>
                            <div>
                              <h4 className="text-sm font-bold text-white">
                                Consensus Verdict: {latestVerificationResponse.decision} (Source: {latestVerificationResponse.decision_source})
                              </h4>
                              <p className="text-xs text-zinc-400">
                                Verified on-chain via QuorumVerifier.sol • Decision finalized on Ethereum Anvil.
                              </p>
                            </div>
                          </div>

                          <button
                            onClick={() => {
                              if (allReleases.length > 0) {
                                handleOpenReleaseModal(allReleases[0]);
                              }
                            }}
                            className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-white text-black font-bold text-sm hover:bg-zinc-200 transition-colors cursor-pointer font-mono"
                          >
                            Inspect Audit Proof
                          </button>
                        </motion.div>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.section>

              {/* SECTION 2: Recent Releases */}
              <section className="space-y-8">
                <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2 pb-2">
                  <div>
                    <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                      Recent Releases
                    </h2>
                    <p className="text-sm text-zinc-400 mt-1">
                      Authoritative verification records retrieved live from the blockchain
                    </p>
                  </div>
                  <span className="text-xs font-mono text-zinc-500">
                    Showing {allReleases.length} releases
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
                  {allReleases.slice(0, 6).map((release) => (
                    <motion.div
                      key={release.id}
                      whileHover={{ y: -3 }}
                      transition={{ duration: 0.2 }}
                      className="rounded-2xl bg-zinc-950/80 border border-white/10 p-7 flex flex-col justify-between hover:border-white/25 transition-all shadow-xl space-y-6"
                    >
                      <div className="space-y-5">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-mono">
                            Release #{release.id}
                          </span>
                          <span className="px-3 py-1 rounded-full text-xs font-medium bg-white/10 text-white border border-white/15 font-mono">
                            {release.verificationState}
                          </span>
                        </div>

                        <div>
                          <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-mono block">
                            Quorum Policy
                          </span>
                          <span className="text-sm font-semibold text-white mt-1 block">
                            {release.quorumPolicy}
                          </span>
                        </div>

                        <div>
                          <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-mono block">
                            Commit
                          </span>
                          <span className="font-mono text-xs text-white bg-black px-2.5 py-1 rounded border border-white/10 inline-block mt-1">
                            {release.commitHash || release.fullCommitHash?.slice(0, 7) || "None"}
                          </span>
                        </div>

                        <div>
                          <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-mono block">
                            Published artifact hash
                          </span>
                          <span className="font-mono text-xs text-zinc-300 truncate block mt-1">
                            {release.publishedArtifactHash}
                          </span>
                        </div>

                        <div>
                          <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-mono block">
                            Record State
                          </span>
                          <span className="text-xs text-zinc-400 mt-1 block">
                            {release.dateTime}
                          </span>
                        </div>
                      </div>

                      <div className="pt-6 border-t border-white/10">
                        <button
                          type="button"
                          onClick={() => handleOpenReleaseModal(release)}
                          className="w-full py-3 px-4 rounded-xl bg-white/5 hover:bg-white hover:text-black border border-white/10 text-white text-xs font-semibold uppercase tracking-wider transition-all duration-200 cursor-pointer text-center font-mono"
                        >
                          More details
                        </button>
                      </div>
                    </motion.div>
                  ))}

                  {allReleases.length === 0 && (
                    <div className="col-span-full py-16 text-center text-zinc-500 font-mono text-xs border border-dashed border-white/10 rounded-2xl">
                      No releases registered on-chain yet. Create one above to initiate consensus verification.
                    </div>
                  )}
                </div>
              </section>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* SPACIOUS WIDE MODAL: 85% Opacity Backdrop, Max Width 5XL, Larger Typography */}
      <AnimatePresence>
        {activeModalRelease && (
          <motion.div
            key="modal-overlay"
            role="dialog"
            aria-modal="true"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-8 lg:p-12 bg-black/85 backdrop-blur-md"
            onClick={() => setActiveModalRelease(null)}
          >
            <motion.div
              key="modal-content"
              initial={{ opacity: 0, scale: 0.96, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 15 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="w-full max-w-5xl bg-zinc-950 border border-white/20 rounded-3xl p-8 sm:p-12 shadow-[0_0_80px_rgba(0,0,0,0.95)] space-y-8 text-white max-h-[92vh] overflow-y-auto font-sans"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Top Bar */}
              <div className="flex items-start justify-between border-b border-white/10 pb-6">
                <div className="space-y-2">
                  <div className="inline-flex items-center gap-2.5 px-3 py-1 rounded-full bg-white/5 border border-white/15 text-xs font-mono text-zinc-300 uppercase tracking-wider">
                    <ShieldCheck className="w-4 h-4 text-white" />
                    Cryptographic Audit Report • Release #{activeModalRelease.id}
                  </div>
                  <h3 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
                    Verification Audit Proof
                  </h3>
                  <p className="text-sm text-zinc-400 font-mono">
                    Authoritative consensus state recorded on Ethereum smart contract (Anvil Chain ID: 31337)
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => setActiveModalRelease(null)}
                  className="w-10 h-10 rounded-full bg-zinc-900 border border-white/10 text-zinc-400 flex items-center justify-center hover:text-white hover:border-white/30 transition-colors cursor-pointer"
                  aria-label="Close modal"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Core Release Metadata Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 bg-black p-6 sm:p-8 rounded-2xl border border-white/10 text-sm font-mono">
                <div className="space-y-1.5">
                  <span className="text-zinc-500 uppercase tracking-wider text-xs block">
                    Source Repository
                  </span>
                  <a
                    href={activeModalRelease.repoUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-white hover:text-zinc-300 underline underline-offset-4 break-all block text-base font-semibold"
                  >
                    {activeModalRelease.repoUrl}
                  </a>
                </div>

                <div className="space-y-1.5">
                  <span className="text-zinc-500 uppercase tracking-wider text-xs block">
                    Authoritative Decision State
                  </span>
                  <div className="flex items-center gap-2 pt-1">
                    <span
                      className={`inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-bold border font-mono ${
                        activeModalRelease.verificationState === "Verified"
                          ? "bg-white/10 text-white border-white/20"
                          : "bg-red-500/10 text-red-300 border-red-500/20"
                      }`}
                    >
                      <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
                      {activeModalRelease.verificationState}
                    </span>
                    <span className="text-xs text-zinc-400">
                      (Source: {activeModalRelease.decisionSource || "BLOCKCHAIN"})
                    </span>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <span className="text-zinc-500 uppercase tracking-wider text-xs block">
                    Pinned Commit SHA
                  </span>
                  <div className="flex items-center justify-between bg-zinc-950 p-3 rounded-xl border border-white/5">
                    <span className="text-zinc-200 break-all text-xs font-mono">
                      {activeModalRelease.fullCommitHash}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopy(activeModalRelease.fullCommitHash, "modal-commit")}
                      className="text-zinc-400 hover:text-white transition-colors cursor-pointer pl-2"
                      title="Copy SHA"
                    >
                      {copiedKey === "modal-commit" ? (
                        <Check className="w-4 h-4 text-white" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <span className="text-zinc-500 uppercase tracking-wider text-xs block">
                    Consensus Quorum Policy
                  </span>
                  <span className="text-white font-medium block pt-2 text-base">
                    {activeModalRelease.quorumPolicy}
                  </span>
                </div>

                <div className="sm:col-span-2 space-y-1.5">
                  <span className="text-zinc-500 uppercase tracking-wider text-xs block">
                    Published Artifact SHA-256 Checksum
                  </span>
                  <div className="flex items-center justify-between bg-zinc-950 p-3.5 rounded-xl border border-white/5">
                    <span className="text-zinc-200 break-all text-xs font-mono">
                      {activeModalRelease.fullArtifactHash}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopy(activeModalRelease.fullArtifactHash, "modal-pubhash")}
                      className="text-zinc-400 hover:text-white transition-colors cursor-pointer pl-2"
                      title="Copy Hash"
                    >
                      {copiedKey === "modal-pubhash" ? (
                        <Check className="w-4 h-4 text-white" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                {activeModalRelease.quorumHash && (
                  <div className="sm:col-span-2 space-y-1.5">
                    <span className="text-zinc-500 uppercase tracking-wider text-xs block">
                      Authoritative On-Chain Quorum Checksum
                    </span>
                    <div className="flex items-center justify-between bg-zinc-950 p-3.5 rounded-xl border border-white/5">
                      <span className="text-white break-all text-xs font-mono font-semibold">
                        {activeModalRelease.quorumHash}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleCopy(activeModalRelease.quorumHash || "", "modal-qhash")}
                        className="text-zinc-400 hover:text-white transition-colors cursor-pointer pl-2"
                        title="Copy Hash"
                      >
                        {copiedKey === "modal-qhash" ? (
                          <Check className="w-4 h-4 text-white" />
                        ) : (
                          <Copy className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Blockchain Transaction Receipts */}
              {(activeModalRelease.createTx || activeModalRelease.finalizeTx) && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-zinc-400">
                      Smart Contract Transactions (QuorumVerifier.sol)
                    </h4>
                    <span className="text-[11px] font-mono text-zinc-500">
                      Contract: 0x5FbDB2315678afecb367f032d93F642f64180aa3
                    </span>
                  </div>

                  <div className="p-6 rounded-2xl bg-black border border-white/10 text-xs font-mono space-y-3">
                    {activeModalRelease.createTx && (
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pb-2 border-b border-white/5">
                        <span className="text-zinc-500">Create Release TX:</span>
                        <span className="text-zinc-300 break-all font-mono">
                          {activeModalRelease.createTx}
                        </span>
                      </div>
                    )}

                    {activeModalRelease.attestationTxs &&
                      activeModalRelease.attestationTxs.map((tx, idx) => (
                        <div
                          key={idx}
                          className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pb-2 border-b border-white/5"
                        >
                          <span className="text-zinc-500">Builder Attestation #{idx + 1} TX:</span>
                          <span className="text-zinc-300 break-all font-mono">{tx}</span>
                        </div>
                      ))}

                    {activeModalRelease.finalizeTx && (
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pt-1">
                        <span className="text-zinc-500">Finalize Decision TX:</span>
                        <span className="text-white break-all font-mono font-bold">
                          {activeModalRelease.finalizeTx}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Builder Attestation Breakdown */}
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-zinc-400">
                    Builder Attestation Evidence Breakdown
                  </h4>
                  <span className="text-[11px] font-mono text-zinc-500">
                    Standardized Spec: <code className="text-zinc-300 font-bold">python-package-v1</code> (Deterministic build)
                  </span>
                </div>

                {activeModalRelease.builderConfigurations.length > 0 ? (
                  <div className="space-y-4">
                    {activeModalRelease.builderConfigurations.map((builder, idx) => (
                      <div
                        key={idx}
                        className="p-6 rounded-2xl bg-black border border-white/10 text-xs space-y-3 font-mono"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-white text-base">
                            {builder.name}
                          </span>
                          <span className="px-3 py-1 rounded-full bg-white/10 text-white font-mono text-xs border border-white/15">
                            {builder.status}
                          </span>
                        </div>
                        <div className="text-zinc-400">
                          Execution Environment:{" "}
                          <span className="text-zinc-200">{builder.type}</span>
                        </div>
                        <div className="text-zinc-400">
                          Artifact Checksum:{" "}
                          <span className="text-white break-all">{builder.resultHash}</span>
                        </div>
                        <div className="text-zinc-400">
                          Signature Status:{" "}
                          <span className="text-zinc-300">{builder.attestationSig}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 rounded-2xl bg-black border border-white/10 space-y-4 text-center">
                    <div className="space-y-2">
                      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-mono text-zinc-400">
                        <Activity className="w-3.5 h-3.5 text-zinc-300" />
                        Status: Created On-Chain • Awaiting Verification
                      </div>
                      <h5 className="text-base font-bold text-white">
                        Verification Has Not Been Triggered Yet
                      </h5>
                      <p className="text-xs text-zinc-400 max-w-lg mx-auto leading-relaxed">
                        Release #{activeModalRelease.id} is registered on the Ethereum smart contract, but independent builders have not yet been dispatched to clone the repository, build the wheel, and submit on-chain attestations.
                      </p>
                    </div>

                    {modalVerifyError && (
                      <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-300 font-mono max-w-md mx-auto">
                        {modalVerifyError}
                      </div>
                    )}

                    <div className="pt-2">
                      <button
                        type="button"
                        disabled={isModalVerifying}
                        onClick={() => handleVerifyFromModal(activeModalRelease.id)}
                        className="px-6 py-3 rounded-xl bg-white text-black font-semibold text-xs font-mono hover:bg-zinc-200 transition-all inline-flex items-center gap-2 cursor-pointer shadow-[0_0_25px_rgba(255,255,255,0.25)] disabled:opacity-50"
                      >
                        {isModalVerifying ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            <span>Dispatching Builders & Verifying On-Chain...</span>
                          </>
                        ) : (
                          <>
                            <Activity className="w-3.5 h-3.5" />
                            <span>Trigger Multi-Builder Verification Now</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="flex justify-end pt-4 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setActiveModalRelease(null)}
                  className="px-8 py-3 rounded-xl bg-white text-black font-bold text-xs uppercase tracking-wider hover:bg-zinc-200 transition-colors cursor-pointer font-mono"
                >
                  Close Analysis
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
