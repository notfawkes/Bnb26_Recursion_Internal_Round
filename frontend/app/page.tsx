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
} from "lucide-react";
import Sidebar from "./components/Sidebar";

// 5 progress steps required by the user
const BUILDER_STEPS = [
  "Queued",
  "Fetching source",
  "Building",
  "Hashing artifact",
  "Attestation submitted",
];

interface BuilderInfo {
  id: number;
  name: string;
  config: string;
  stepIndex: number;
  hash: string;
}

interface ReleaseItem {
  id: string;
  repoUrl: string;
  commitHash: string;
  fullCommitHash: string;
  quorumPolicy: string;
  verificationState: "Verified" | "Quorum Achieved" | "Pending";
  publishedArtifactHash: string;
  fullArtifactHash: string;
  dateTime: string;
  builderConfigurations: {
    name: string;
    type: string;
    resultHash: string;
    attestationSig: string;
    status: "Match ✓" | "Pending";
  }[];
}

const RECENT_RELEASES: ReleaseItem[] = [
  {
    id: "rel-1",
    repoUrl: "https://github.com/quorum-network/core-verifier",
    commitHash: "c5092a4",
    fullCommitHash: "c5092a4a9b6c1e389d0f2b3e4a7812bc89e34a1b",
    quorumPolicy: "2 of 3 Consensus",
    verificationState: "Verified",
    publishedArtifactHash: "sha256:7f9a88e...3b12",
    fullArtifactHash: "sha256:7f9a88e21a3b4c5d6e7f809123456789abcdef0123456789abcdef0123456789",
    dateTime: "Oct 03, 2026 • 21:40 UTC",
    builderConfigurations: [
      {
        name: "Builder #1",
        type: "AWS Nitro Enclave (us-east-1) • TEE Isolated",
        resultHash: "sha256:7f9a88e...3b12",
        attestationSig: "0x8fa1b9347209df9e1983084bc67d4410",
        status: "Match ✓",
      },
      {
        name: "Builder #2",
        type: "GCP Confidential Space (us-central1) • AMD SEV-SNP",
        resultHash: "sha256:7f9a88e...3b12",
        attestationSig: "0x3db5719ef08819a842fbc947091288cc",
        status: "Match ✓",
      },
      {
        name: "Builder #3",
        type: "Azure DCsv3 SGX (westeurope) • Intel SGX",
        resultHash: "sha256:7f9a88e...3b12",
        attestationSig: "0x1bc8429188402ff7188172ac48d071ef",
        status: "Match ✓",
      },
    ],
  },
  {
    id: "rel-2",
    repoUrl: "https://github.com/quorum-network/evm-attestor",
    commitHash: "9f1d8b2",
    fullCommitHash: "9f1d8b24479e0a112cd5868205fbc30f9a2e6612",
    quorumPolicy: "3 of 3 Multi-Sig",
    verificationState: "Verified",
    publishedArtifactHash: "sha256:3b19fa2...a4bc",
    fullArtifactHash: "sha256:3b19fa2c4d8e709a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef01",
    dateTime: "Oct 02, 2026 • 15:12 UTC",
    builderConfigurations: [
      {
        name: "Builder #1",
        type: "AWS Nitro Enclave (us-east-1) • TEE Isolated",
        resultHash: "sha256:3b19fa2...a4bc",
        attestationSig: "0x77c29e1fba0298a449178cbef1044391",
        status: "Match ✓",
      },
      {
        name: "Builder #2",
        type: "GCP Confidential Space (us-central1) • AMD SEV-SNP",
        resultHash: "sha256:3b19fa2...a4bc",
        attestationSig: "0x44d1830bb03947ca79382bca8190334a",
        status: "Match ✓",
      },
      {
        name: "Builder #3",
        type: "Azure DCsv3 SGX (westeurope) • Intel SGX",
        resultHash: "sha256:3b19fa2...a4bc",
        attestationSig: "0x91a382e70f6630bce1102947118205f1",
        status: "Match ✓",
      },
    ],
  },
  {
    id: "rel-3",
    repoUrl: "https://github.com/quorum-network/reproducible-runtime",
    commitHash: "4e7a301",
    fullCommitHash: "4e7a301889c201d4a8e23bb4108861ea55639147",
    quorumPolicy: "2 of 3 Consensus",
    verificationState: "Verified",
    publishedArtifactHash: "sha256:a8204cd...9876",
    fullArtifactHash: "sha256:a8204cd19fb8372615a4c3d2e1f09876543210fedcba9876543210fedcba9876",
    dateTime: "Sep 30, 2026 • 09:05 UTC",
    builderConfigurations: [
      {
        name: "Builder #1",
        type: "AWS Nitro Enclave (us-east-1) • TEE Isolated",
        resultHash: "sha256:a8204cd...9876",
        attestationSig: "0x61f093b19280dca88921bdfc081977a2",
        status: "Match ✓",
      },
      {
        name: "Builder #2",
        type: "GCP Confidential Space (us-central1) • AMD SEV-SNP",
        resultHash: "sha256:a8204cd...9876",
        attestationSig: "0x19d846c003fa91bb402837bc901ef540",
        status: "Match ✓",
      },
      {
        name: "Builder #3",
        type: "Azure DCsv3 SGX (westeurope) • Intel SGX",
        resultHash: "sha256:a8204cd...9876",
        attestationSig: "0x82f912c9304bd8ae300188efb011492b",
        status: "Match ✓",
      },
    ],
  },
];

export default function DashboardPage() {
  // Navigation active tab state
  const [activeTab, setActiveTab] = useState("dashboard");

  // 1. Initial loading animation state
  const [initialLoading, setInitialLoading] = useState(true);

  // 2. Create Verification form states
  const [isFormExpanded, setIsFormExpanded] = useState(false);
  const [githubUrl, setGithubUrl] = useState("");
  const [commitHash, setCommitHash] = useState("");
  const [quorumPolicy, setQuorumPolicy] = useState("2 of 3 Consensus");

  // 3. Verification Execution states
  const [isVerifying, setIsVerifying] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [builders, setBuilders] = useState<BuilderInfo[]>([
    {
      id: 1,
      name: "Builder #1",
      config: "AWS Nitro Enclave",
      stepIndex: 0,
      hash: "Pending build...",
    },
    {
      id: 2,
      name: "Builder #2",
      config: "GCP Confidential Space",
      stepIndex: 0,
      hash: "Pending build...",
    },
    {
      id: 3,
      name: "Builder #3",
      config: "Azure DCsv3 SGX",
      stepIndex: 0,
      hash: "Pending build...",
    },
  ]);

  // 4. Modal state for detailed analysis (80% opacity black)
  const [activeModalRelease, setActiveModalRelease] = useState<ReleaseItem | null>(null);

  // Initial loading simulation
  useEffect(() => {
    const timer = setTimeout(() => {
      setInitialLoading(false);
    }, 1000);
    return () => clearTimeout(timer);
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

  // Builder progression simulation
  useEffect(() => {
    if (!isVerifying || isCompleted) return;

    const interval = setInterval(() => {
      setBuilders((prev) => {
        let allDone = true;
        const updated = prev.map((builder) => {
          if (builder.stepIndex < BUILDER_STEPS.length - 1) {
            allDone = false;
            // Realistic slight variation between independent builders
            const shouldAdvance =
              builder.id === 1
                ? Math.random() > 0.15
                : builder.id === 2
                ? Math.random() > 0.25
                : Math.random() > 0.35;

            const nextStep = shouldAdvance ? builder.stepIndex + 1 : builder.stepIndex;
            const updatedHash =
              nextStep >= 3 ? "sha256:7f4a08b9e...d81a" : "Computing checksum...";

            return {
              ...builder,
              stepIndex: nextStep,
              hash: updatedHash,
            };
          }
          return builder;
        });

        if (allDone) {
          setIsCompleted(true);
          clearInterval(interval);
        }

        return updated;
      });
    }, 950);

    return () => clearInterval(interval);
  }, [isVerifying, isCompleted]);

  // Handle start verification button click
  const handleStartVerification = () => {
    if (!isFormComplete) return;
    setIsVerifying(true);
    setIsCompleted(false);
    setBuilders([
      {
        id: 1,
        name: "Builder #1",
        config: "AWS Nitro Enclave",
        stepIndex: 0,
        hash: "Computing checksum...",
      },
      {
        id: 2,
        name: "Builder #2",
        config: "GCP Confidential Space",
        stepIndex: 0,
        hash: "Computing checksum...",
      },
      {
        id: 3,
        name: "Builder #3",
        config: "Azure DCsv3 SGX",
        stepIndex: 0,
        hash: "Computing checksum...",
      },
    ]);
  };

  // Shrink / collapse create verification div
  const handleShrink = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsFormExpanded(false);
    setIsVerifying(false);
    setIsCompleted(false);
  };

  // Open the newly completed verification in the detailed modal
  const handleOpenCompletedVerification = () => {
    const newRelease: ReleaseItem = {
      id: "rel-current",
      repoUrl: githubUrl || "https://github.com/quorum-network/verified-source",
      commitHash: commitHash.slice(0, 7) || "7f8b9a1",
      fullCommitHash: commitHash || "7f8b9a103e294bc178d055102abf990184c7a102",
      quorumPolicy: quorumPolicy,
      verificationState: "Verified",
      publishedArtifactHash: "sha256:7f4a08b...d81a",
      fullArtifactHash:
        "sha256:7f4a08b9e11894d078a6ec192837bc901ef54061f093b19280dca88921bdfc08",
      dateTime: "Just now • Verification Complete",
      builderConfigurations: [
        {
          name: "Builder #1",
          type: "AWS Nitro Enclave (us-east-1) • Linux x86_64",
          resultHash: "sha256:7f4a08b...d81a",
          attestationSig: "0x8fa1b9347209df9e1983084bc67d4410",
          status: "Match ✓",
        },
        {
          name: "Builder #2",
          type: "GCP Confidential Space (us-central1) • AMD SEV-SNP",
          resultHash: "sha256:7f4a08b...d81a",
          attestationSig: "0x3db5719ef08819a842fbc947091288cc",
          status: "Match ✓",
        },
        {
          name: "Builder #3",
          type: "Azure DCsv3 (westeurope) • Intel SGX",
          resultHash: "sha256:7f4a08b...d81a",
          attestationSig: "0x1bc8429188402ff7188172ac48d071ef",
          status: "Match ✓",
        },
      ],
    };
    setActiveModalRelease(newRelease);
  };

  // Quick fill sample release data
  const handleQuickFill = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsFormExpanded(true);
    setGithubUrl("https://github.com/quorum-network/reproducible-core");
    setCommitHash("7f8b9a103e294bc178d055102abf");
    setQuorumPolicy("2 of 3 Consensus");
  };

  // 1. Initial Loading Animation (Linear / Vercel minimalist loader)
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
            Initializing Quorum Runtime
          </span>
          <div className="w-32 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent mt-4" />
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white flex flex-col lg:flex-row relative font-sans selection:bg-white selection:text-black">
      {/* Sidebar Component */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 relative">
        {/* Background ambient lighting */}
        <div className="linear-grid absolute inset-0 opacity-40 pointer-events-none" />
        <div className="radial-spotlight absolute inset-0 pointer-events-none" />

        {/* Main Container */}
        <div className="relative z-10 max-w-5xl mx-auto px-6 sm:px-10 lg:px-12 py-10 sm:py-16 space-y-16">
          
          {/* Top Header / Navigation */}
          <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-6 pb-8 border-b border-white/10">
            <div className="space-y-2">
              <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-[11px] font-mono uppercase tracking-wider text-zinc-400">
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                Consensus Protocol v1.4
              </div>
              <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white">
                Dashboard
              </h1>
              <p className="text-base text-zinc-400 max-w-xl">
                Decentralized reproducible build verification and multi-builder cryptographic consensus.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-zinc-950 border border-white/10 text-xs font-mono text-zinc-300 shadow-sm">
                <Activity className="w-3.5 h-3.5 text-zinc-400" />
                <span>3 Active Enclaves</span>
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
                  Verify repository reproducibility across isolated enclave builders
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
                        className="text-xs text-zinc-400 hover:text-white transition-colors underline underline-offset-4 cursor-pointer"
                      >
                        Quick Fill Sample
                      </button>
                    )}

                    {/* Option to shrink / collapse the verification div */}
                    <button
                      onClick={handleShrink}
                      type="button"
                      className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 px-3 py-1.5 rounded-full transition-all cursor-pointer font-mono"
                      title="Shrink back to minimal"
                    >
                      <ChevronUp className="w-3.5 h-3.5" />
                      <span>Shrink</span>
                    </button>

                    {/* Go to Verification Page button when completed */}
                    {isCompleted && (
                      <motion.button
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => handleOpenCompletedVerification()}
                        className="px-4 py-1.5 rounded-full bg-white text-black font-semibold text-xs hover:bg-zinc-200 transition-all shadow-[0_0_15px_rgba(255,255,255,0.2)] cursor-pointer inline-flex items-center gap-1.5 font-mono"
                      >
                        <span>Go to Verification Page</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </motion.button>
                    )}
                  </>
                )}
              </div>
            </div>

            {/* GitHub Repository Input - Primary input */}
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
                        <span>Release Commit Hash</span>
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. 7f8b9a103e294bc178d055102abf"
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
                          <option value="Majority Quorum" className="bg-zinc-900 text-white">
                            Majority Quorum (&gt;50%)
                          </option>
                        </select>
                        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-zinc-400">
                          <ArrowDown className="w-3.5 h-3.5" />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Verification Trigger Button: Blurred until inputs are entered, then sharp */}
                  <div className="pt-4 flex flex-col sm:flex-row items-center justify-between gap-4">
                    <span className="text-xs text-zinc-400 font-mono">
                      {isFormComplete
                        ? "Ready to initiate multi-builder consensus pipeline"
                        : "Enter GitHub repository, commit hash, and policy to unlock"}
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
                      Start Verification
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
                    <linearGradient id="divergeGradient" x1="0" y1="0" x2="0" y2="64" gradientUnits="userSpaceOnUse">
                      <stop offset="0%" stopColor="#ffffff" stopOpacity="0.8" />
                      <stop offset="60%" stopColor="#ffffff" stopOpacity="0.4" />
                      <stop offset="100%" stopColor="#ffffff" stopOpacity="0.25" />
                    </linearGradient>
                  </defs>

                  {/* Clean Origin Node from GitHub Repository */}
                  <circle cx="450" cy="2" r="3.5" fill="#ffffff" />
                  <circle cx="450" cy="2" r="6" stroke="#ffffff" strokeOpacity="0.25" strokeWidth="1" fill="none" />

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

            {/* Expanded 3 Builders Section: Direct connection from SVG to 3 Builder Cards */}
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
                  {/* 3 Spacious Minimal Builder Cards with Loading Bars */}
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
                          {/* Minimal Header */}
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

                            <p className="text-xs text-zinc-400">
                              {builder.config}
                            </p>
                          </div>

                          {/* Minimal Essential Detail */}
                          <div className="bg-zinc-950/80 border border-white/5 rounded-lg p-3 space-y-1">
                            <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 block">
                              Artifact Checksum
                            </span>
                            <span className="font-mono text-xs text-zinc-300 truncate block">
                              {builder.hash}
                            </span>
                          </div>

                          {/* Loading Bar Component (Replacing the old bulky list) */}
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

                            {/* Minimalist Progress Loading Bar */}
                            <div className="w-full h-2 bg-zinc-900 border border-white/10 rounded-full overflow-hidden p-[1px]">
                              <motion.div
                                className="h-full bg-white rounded-full shadow-[0_0_12px_rgba(255,255,255,0.4)]"
                                initial={{ width: 0 }}
                                animate={{ width: `${stepPercent}%` }}
                                transition={{ duration: 0.4, ease: "easeOut" }}
                              />
                            </div>

                            {/* 5 Minimal Stage Dots */}
                            <div className="flex items-center justify-between pt-1 px-1">
                              {BUILDER_STEPS.map((s, idx) => (
                                <div key={s} className="flex flex-col items-center gap-1" title={s}>
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

                          {/* Modal Trigger for In-Depth Information */}
                          <div className="pt-2 border-t border-white/5">
                            <button
                              type="button"
                              onClick={() => handleOpenCompletedVerification(builder.id)}
                              className="w-full py-2 px-3 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-300 hover:text-white text-xs font-mono transition-colors text-center cursor-pointer"
                            >
                              View Full Details →
                            </button>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>

                  {/* Final Completion Action Bar */}
                  {isCompleted && (
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
                            Consensus Verified (3/3 Attestations Matched)
                          </h4>
                          <p className="text-xs text-zinc-400">
                            Deterministic artifacts confirmed and verified on-chain.
                          </p>
                        </div>
                      </div>

                      <button
                        onClick={() => handleOpenCompletedVerification()}
                        className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-white text-black font-bold text-sm hover:bg-zinc-200 transition-colors cursor-pointer"
                      >
                        More details
                      </button>
                    </motion.div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.section>

          {/* SECTION 2: Recent Releases (Wireframe Left Section) */}
          <section className="space-y-8">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2 pb-2">
              <div>
                <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                  Recent Releases
                </h2>
                <p className="text-sm text-zinc-400 mt-1">
                  Latest cryptographic attestations verified by the network
                </p>
              </div>
              <span className="text-xs font-mono text-zinc-500">
                Showing 3 verified releases
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
              {RECENT_RELEASES.map((release) => (
                <motion.div
                  key={release.id}
                  whileHover={{ y: -3 }}
                  transition={{ duration: 0.2 }}
                  className="rounded-2xl bg-zinc-950/80 border border-white/10 p-7 flex flex-col justify-between hover:border-white/25 transition-all shadow-xl space-y-6"
                >
                  <div className="space-y-5">
                    {/* Verification State */}
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-mono">
                        Verification State
                      </span>
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-white/10 text-white border border-white/15">
                        {release.verificationState}
                      </span>
                    </div>

                    {/* Quorum Policy */}
                    <div>
                      <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-mono block">
                        Quorum Policy
                      </span>
                      <span className="text-sm font-semibold text-white mt-1 block">
                        {release.quorumPolicy}
                      </span>
                    </div>

                    {/* Commit */}
                    <div>
                      <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-mono block">
                        Commit
                      </span>
                      <span className="font-mono text-xs text-white bg-black px-2.5 py-1 rounded border border-white/10 inline-block mt-1">
                        {release.commitHash}
                      </span>
                    </div>

                    {/* Published Artifact Hash */}
                    <div>
                      <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-mono block">
                        Published artifact hash
                      </span>
                      <span className="font-mono text-xs text-zinc-300 truncate block mt-1">
                        {release.publishedArtifactHash}
                      </span>
                    </div>

                    {/* Date / Time */}
                    <div>
                      <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-mono block">
                        Date/time
                      </span>
                      <span className="text-xs text-zinc-400 mt-1 block">
                        {release.dateTime}
                      </span>
                    </div>
                  </div>

                  {/* Action to open verification details */}
                  <div className="pt-6 border-t border-white/10">
                    <button
                      type="button"
                      onClick={() => setActiveModalRelease(release)}
                      className="w-full py-3 px-4 rounded-xl bg-white/5 hover:bg-white hover:text-black border border-white/10 text-white text-xs font-semibold uppercase tracking-wider transition-all duration-200 cursor-pointer text-center"
                    >
                      More details
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          </section>

        </div>
      </main>

      {/* MODAL: 80% Opacity Black Backdrop with Detailed Analysis */}
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
            className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-md"
            onClick={() => setActiveModalRelease(null)}
          >
            <motion.div
              key="modal-content"
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="w-full max-w-2xl bg-zinc-950 border border-white/15 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6 text-white max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Top Bar */}
              <div className="flex items-start justify-between border-b border-white/10 pb-5">
                <div>
                  <div className="inline-flex items-center gap-2 text-xs font-mono text-zinc-400 uppercase tracking-wider">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    Cryptographic Audit Report
                  </div>
                  <h3 className="text-2xl font-bold tracking-tight text-white mt-1">
                    Detailed Verification Analysis
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveModalRelease(null)}
                  className="w-8 h-8 rounded-full bg-black border border-white/10 text-zinc-400 flex items-center justify-center hover:text-white hover:border-white/30 transition-colors cursor-pointer"
                  aria-label="Close modal"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Core Release Metadata */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-black p-5 rounded-xl border border-white/10 text-xs">
                <div>
                  <span className="text-zinc-500 uppercase tracking-wider text-[10px] block">
                    Repository URL
                  </span>
                  <span className="font-mono text-zinc-200 break-all block mt-1">
                    {activeModalRelease.repoUrl}
                  </span>
                </div>

                <div>
                  <span className="text-zinc-500 uppercase tracking-wider text-[10px] block">
                    Verification State
                  </span>
                  <span className="font-semibold text-white mt-1 inline-flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-white" />
                    {activeModalRelease.verificationState} (Quorum Consensual)
                  </span>
                </div>

                <div>
                  <span className="text-zinc-500 uppercase tracking-wider text-[10px] block">
                    Full Commit Hash
                  </span>
                  <span className="font-mono text-zinc-300 break-all block mt-1">
                    {activeModalRelease.fullCommitHash}
                  </span>
                </div>

                <div>
                  <span className="text-zinc-500 uppercase tracking-wider text-[10px] block">
                    Quorum Policy
                  </span>
                  <span className="text-white mt-1 block font-medium">
                    {activeModalRelease.quorumPolicy}
                  </span>
                </div>

                <div className="sm:col-span-2">
                  <span className="text-zinc-500 uppercase tracking-wider text-[10px] block">
                    Published Artifact Hash (SHA-256)
                  </span>
                  <span className="font-mono text-zinc-200 break-all block mt-1 bg-zinc-950 p-2 rounded border border-white/5">
                    {activeModalRelease.fullArtifactHash}
                  </span>
                </div>

                <div className="sm:col-span-2">
                  <span className="text-zinc-500 uppercase tracking-wider text-[10px] block">
                    Date & Timestamp
                  </span>
                  <span className="text-zinc-400 mt-1 block">
                    {activeModalRelease.dateTime}
                  </span>
                </div>
              </div>

              {/* Builder Configuration Analysis */}
              <div className="space-y-4">
                <h4 className="text-xs font-mono uppercase tracking-wider text-zinc-400">
                  Builder Attestation Breakdown
                </h4>

                <div className="space-y-3">
                  {activeModalRelease.builderConfigurations.map((builder, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl bg-black border border-white/10 text-xs space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white text-sm">
                          {builder.name}
                        </span>
                        <span className="px-2.5 py-0.5 rounded-full bg-white/10 text-white font-mono text-[11px] border border-white/15">
                          {builder.status}
                        </span>
                      </div>
                      <div className="text-zinc-400">
                        Configuration:{" "}
                        <span className="text-zinc-300">{builder.type}</span>
                      </div>
                      <div className="text-zinc-400">
                        Result Hash:{" "}
                        <span className="font-mono text-white">{builder.resultHash}</span>
                      </div>
                      <div className="text-zinc-400">
                        Attestation Signature:{" "}
                        <span className="font-mono text-zinc-400">{builder.attestationSig}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Modal Footer */}
              <div className="flex justify-end pt-4 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setActiveModalRelease(null)}
                  className="px-6 py-2.5 rounded-xl bg-white text-black font-semibold text-xs uppercase tracking-wider hover:bg-zinc-200 transition-colors cursor-pointer"
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
