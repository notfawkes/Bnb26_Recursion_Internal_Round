"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  ShieldCheck,
  GitCommit,
  Search,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileCode2,
  RefreshCw,
  Clock,
} from "lucide-react";

export interface VerificationCardItem {
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
  builderCount: number;
  agreementCount: number;
  txHash?: string;
  onOpenModal: () => void;
}

interface VerificationsViewProps {
  releases: VerificationCardItem[];
  onRefresh?: () => void;
  isLoading?: boolean;
}

export default function VerificationsView({
  releases,
  onRefresh,
  isLoading = false,
}: VerificationsViewProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterState, setFilterState] = useState<string>("ALL");

  const filtered = releases.filter((item) => {
    const matchesSearch =
      item.repoUrl.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.fullCommitHash.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.id.toLowerCase().includes(searchQuery.toLowerCase());

    if (filterState === "ALL") return matchesSearch;
    if (filterState === "VERIFIED") return matchesSearch && item.verificationState === "Verified";
    if (filterState === "REJECTED") return matchesSearch && item.verificationState === "Rejected";
    if (filterState === "DISPUTED") return matchesSearch && item.verificationState === "Disputed";
    if (filterState === "PENDING") return matchesSearch && item.verificationState === "Pending";
    return matchesSearch;
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      className="space-y-12 max-w-5xl mx-auto px-6 sm:px-10 lg:px-12 py-10 sm:py-16 font-sans"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-6 pb-8 border-b border-white/10">
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-[11px] font-mono uppercase tracking-wider text-zinc-400">
            <ShieldCheck className="w-3.5 h-3.5 text-white" />
            Immutable On-Chain Ledger
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white">
            Verifications
          </h1>
          <p className="text-base text-zinc-400 max-w-2xl leading-relaxed">
            Every verification request recorded on the Ethereum smart contract. Verified builds
            confirm that independent builders produced identical cryptographic artifacts.
          </p>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-zinc-950 hover:bg-zinc-900 border border-white/10 text-xs font-mono text-zinc-300 hover:text-white transition-all cursor-pointer self-start sm:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            <span>Sync Ledger</span>
          </button>
        )}
      </div>

      {/* Search and Filters Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter by repository, commit, or release ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-zinc-950 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-white/30 font-mono transition-all"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-zinc-950 border border-white/10 self-start sm:self-auto text-xs font-mono">
          {["ALL", "VERIFIED", "REJECTED", "DISPUTED"].map((tab) => {
            const isActive = filterState === tab;
            return (
              <button
                key={tab}
                onClick={() => setFilterState(tab)}
                className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                  isActive
                    ? "bg-white text-black font-semibold shadow-sm"
                    : "text-zinc-400 hover:text-white"
                }`}
              >
                {tab}
              </button>
            );
          })}
        </div>
      </div>

      {/* Verifications Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {filtered.map((item) => {
          const isVerified = item.verificationState === "Verified";
          const isRejected = item.verificationState === "Rejected";
          const isDisputed = item.verificationState === "Disputed";
          const isPending = item.verificationState === "Pending";

          return (
            <motion.div
              key={item.id}
              whileHover={{ y: -3 }}
              transition={{ duration: 0.2 }}
              className="rounded-2xl bg-zinc-950/80 border border-white/10 p-8 flex flex-col justify-between hover:border-white/25 transition-all shadow-2xl space-y-6"
            >
              <div className="space-y-5">
                {/* Top Row: Release ID & State Badge */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold text-white bg-white/5 px-2.5 py-1 rounded-md border border-white/5">
                      Release #{item.id}
                    </span>
                    <span className="text-xs text-zinc-500 font-mono flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {item.dateTime}
                    </span>
                  </div>

                  <span
                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono border ${
                      isVerified
                        ? "bg-white/10 text-white border-white/20"
                        : isRejected
                        ? "bg-red-500/10 text-red-300 border-red-500/20"
                        : isDisputed
                        ? "bg-amber-500/10 text-amber-300 border-amber-500/20"
                        : "bg-zinc-900 text-zinc-400 border-white/10"
                    }`}
                  >
                    {isVerified && <CheckCircle2 className="w-3.5 h-3.5 text-white" />}
                    {isRejected && <XCircle className="w-3.5 h-3.5 text-red-400" />}
                    {isDisputed && <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />}
                    {item.verificationState}
                  </span>
                </div>

                {/* Repository URL */}
                <div>
                  <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
                    Source Repository
                  </span>
                  <span className="text-base font-bold text-white truncate block mt-1">
                    {item.repoUrl}
                  </span>
                </div>

                {/* Commit & Policy Grid */}
                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div className="p-3 rounded-xl bg-black border border-white/5 space-y-1">
                    <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 flex items-center gap-1">
                      <GitCommit className="w-3 h-3 text-zinc-400" /> Pinned Commit
                    </span>
                    <span className="font-mono text-xs text-white block truncate">
                      {item.fullCommitHash ? item.fullCommitHash.slice(0, 10) + "..." : item.commitHash}
                    </span>
                  </div>

                  <div className="p-3 rounded-xl bg-black border border-white/5 space-y-1">
                    <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
                      Quorum Policy
                    </span>
                    <span className="font-mono text-xs text-zinc-200 block truncate">
                      {item.quorumPolicy}
                    </span>
                  </div>
                </div>

                {/* Checksums Display */}
                <div className="p-4 rounded-xl bg-black border border-white/5 space-y-2.5">
                  <div>
                    <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
                      Published Artifact Checksum
                    </span>
                    <span className="font-mono text-xs text-zinc-300 truncate block mt-1">
                      {item.fullArtifactHash || item.publishedArtifactHash}
                    </span>
                  </div>

                  {item.quorumHash && (
                    <div className="pt-2 border-t border-white/5">
                      <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
                        On-Chain Quorum Checksum
                      </span>
                      <span className="font-mono text-xs text-white truncate block mt-1">
                        {item.quorumHash}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Action Button */}
              <div className="pt-4 border-t border-white/10">
                <button
                  type="button"
                  onClick={item.onOpenModal}
                  className="w-full py-3 px-4 rounded-xl bg-white/5 hover:bg-white hover:text-black border border-white/10 text-white text-xs font-semibold uppercase tracking-wider transition-all duration-200 cursor-pointer text-center font-mono inline-flex items-center justify-center gap-2"
                >
                  <span>Inspect Audit Proof</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              </div>
            </motion.div>
          );
        })}

        {filtered.length === 0 && (
          <div className="col-span-full py-20 text-center text-zinc-500 font-mono text-xs border border-dashed border-white/10 rounded-2xl space-y-2">
            <div>No verifications found in on-chain ledger.</div>
            {onRefresh && (
              <button
                onClick={onRefresh}
                className="text-xs text-white underline underline-offset-4 cursor-pointer"
              >
                Click to reload releases from blockchain
              </button>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
