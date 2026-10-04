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
}

export default function VerificationsView({ releases }: VerificationsViewProps) {
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
    return matchesSearch;
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      className="space-y-10 max-w-5xl mx-auto px-6 sm:px-10 lg:px-12 py-10 sm:py-16"
    >
      {/* Header */}
      <div className="space-y-3 pb-8 border-b border-white/10">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-[11px] font-mono uppercase tracking-wider text-zinc-400">
          <ShieldCheck className="w-3.5 h-3.5 text-white" />
          Authoritative Ledger
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white">
          Verifications
        </h1>
        <p className="text-base text-zinc-400 max-w-2xl">
          Cryptographically proven software releases executed across isolated enclave builders
          and recorded immutably on the Ethereum smart contract.
        </p>
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
            className="w-full bg-zinc-950 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-white/30 font-mono transition-all"
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
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {filtered.map((item) => {
          const isVerified = item.verificationState === "Verified";
          const isRejected = item.verificationState === "Rejected";
          const isDisputed = item.verificationState === "Disputed";

          return (
            <motion.div
              key={item.id}
              whileHover={{ y: -3 }}
              transition={{ duration: 0.2 }}
              className="rounded-2xl bg-zinc-950/80 border border-white/10 p-6 flex flex-col justify-between hover:border-white/25 transition-all shadow-xl space-y-6"
            >
              <div className="space-y-4">
                {/* Top Row: Release ID & State Badge */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs uppercase tracking-wider text-zinc-500">
                      Release #{item.id}
                    </span>
                    <span className="text-zinc-600">•</span>
                    <span className="text-[11px] text-zinc-400 font-mono">{item.dateTime}</span>
                  </div>

                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border font-mono ${
                      isVerified
                        ? "bg-white/10 text-white border-white/20"
                        : isRejected
                        ? "bg-red-500/10 text-red-300 border-red-500/20"
                        : "bg-amber-500/10 text-amber-300 border-amber-500/20"
                    }`}
                  >
                    {isVerified && <CheckCircle2 className="w-3 h-3 text-white" />}
                    {isRejected && <XCircle className="w-3 h-3 text-red-400" />}
                    {isDisputed && <AlertTriangle className="w-3 h-3 text-amber-400" />}
                    {item.verificationState}
                  </span>
                </div>

                {/* Repository URL */}
                <div>
                  <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
                    Source Repository
                  </span>
                  <span className="text-sm font-semibold text-white truncate block mt-0.5">
                    {item.repoUrl}
                  </span>
                </div>

                {/* Commit & Policy */}
                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div className="p-2.5 rounded-lg bg-black border border-white/5 space-y-1">
                    <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 flex items-center gap-1">
                      <GitCommit className="w-3 h-3" /> Commit
                    </span>
                    <span className="font-mono text-xs text-zinc-300 block truncate">
                      {item.commitHash}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-black border border-white/5 space-y-1">
                    <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
                      Consensus Quorum
                    </span>
                    <span className="font-mono text-xs text-white block">
                      {item.agreementCount} / {item.builderCount} Enclaves
                    </span>
                  </div>
                </div>

                {/* Published vs Quorum Checksum */}
                <div className="p-3 rounded-lg bg-black border border-white/5 space-y-2">
                  <div>
                    <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
                      Published Checksum
                    </span>
                    <span className="font-mono text-[11px] text-zinc-300 truncate block mt-0.5">
                      {item.publishedArtifactHash}
                    </span>
                  </div>

                  {item.quorumHash && (
                    <div className="pt-1.5 border-t border-white/5">
                      <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
                        On-Chain Quorum Hash
                      </span>
                      <span className="font-mono text-[11px] text-white truncate block mt-0.5">
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
                  className="w-full py-2.5 px-4 rounded-xl bg-white/5 hover:bg-white hover:text-black border border-white/10 text-white text-xs font-semibold uppercase tracking-wider transition-all duration-200 cursor-pointer text-center font-mono inline-flex items-center justify-center gap-2"
                >
                  <span>Inspect Audit Proof</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              </div>
            </motion.div>
          );
        })}

        {filtered.length === 0 && (
          <div className="col-span-full py-16 text-center text-zinc-500 font-mono text-xs border border-dashed border-white/10 rounded-2xl">
            No verifications match the search query.
          </div>
        )}
      </div>
    </motion.div>
  );
}
