"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  History,
  GitCommit,
  CheckCircle2,
  ExternalLink,
  Search,
  Copy,
  Check,
} from "lucide-react";
import { VerificationCardItem } from "./VerificationsView";

interface ReleasesViewProps {
  releases: VerificationCardItem[];
}

export default function ReleasesView({ releases }: ReleasesViewProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  const filtered = releases.filter(
    (r) =>
      r.repoUrl.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.fullCommitHash.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
          <History className="w-3.5 h-3.5 text-white" />
          Release Registry
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white">
          Recent Releases
        </h1>
        <p className="text-base text-zinc-400 max-w-2xl">
          Historical record of verified build artifacts, provenance metadata, and cryptographic quorum attestations.
        </p>
      </div>

      {/* Search Input */}
      <div className="relative w-full max-w-md">
        <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          placeholder="Search releases by repository or commit..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-zinc-950 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-white/30 font-mono transition-all"
        />
      </div>

      {/* Timeline List of Releases */}
      <div className="space-y-4">
        {filtered.map((item, idx) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: idx * 0.05 }}
            className="rounded-2xl bg-zinc-950/80 border border-white/10 p-6 hover:border-white/20 transition-all shadow-xl space-y-4"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs text-zinc-500 bg-white/5 px-2.5 py-1 rounded-md border border-white/5">
                  #{item.id}
                </span>
                <span className="font-bold text-white text-base truncate max-w-md">
                  {item.repoUrl}
                </span>
              </div>

              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-white/10 text-white border border-white/15 font-mono self-start sm:self-auto">
                <CheckCircle2 className="w-3 h-3 text-white" />
                {item.verificationState}
              </span>
            </div>

            {/* Release Metadata Row */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-black border border-white/5 space-y-1">
                <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 flex items-center gap-1">
                  <GitCommit className="w-3 h-3" /> Commit
                </span>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-zinc-300 truncate max-w-[140px]">
                    {item.commitHash}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleCopy(item.fullCommitHash, `commit-${item.id}`)}
                    className="text-zinc-500 hover:text-white transition-colors cursor-pointer"
                    title="Copy full commit SHA"
                  >
                    {copiedId === `commit-${item.id}` ? (
                      <Check className="w-3.5 h-3.5 text-white" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-black border border-white/5 space-y-1">
                <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
                  Consensus Quorum
                </span>
                <span className="font-mono text-white block">
                  {item.quorumPolicy} ({item.agreementCount}/{item.builderCount})
                </span>
              </div>

              <div className="p-3 rounded-xl bg-black border border-white/5 space-y-1">
                <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
                  Verification Timestamp
                </span>
                <span className="text-zinc-300 block truncate">{item.dateTime}</span>
              </div>
            </div>

            {/* Checksum Snippet & Action Button */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-3 border-t border-white/5">
              <div className="flex items-center gap-2 text-xs font-mono text-zinc-400 truncate max-w-lg">
                <span className="text-zinc-600">SHA256:</span>
                <span className="text-zinc-300 truncate">{item.fullArtifactHash}</span>
              </div>

              <button
                type="button"
                onClick={item.onOpenModal}
                className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white hover:text-black border border-white/10 text-white text-xs font-semibold uppercase tracking-wider transition-all font-mono inline-flex items-center gap-2 cursor-pointer self-start sm:self-auto"
              >
                <span>Audit Certificate</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            </div>
          </motion.div>
        ))}

        {filtered.length === 0 && (
          <div className="py-16 text-center text-zinc-500 font-mono text-xs border border-dashed border-white/10 rounded-2xl">
            No releases found.
          </div>
        )}
      </div>
    </motion.div>
  );
}
