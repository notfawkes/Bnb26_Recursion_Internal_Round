"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  FileCode2,
  CheckCircle2,
  ShieldAlert,
  HelpCircle,
  Search,
  ExternalLink,
  Code,
  Layers,
} from "lucide-react";
import { getRelease, getReleaseResult, getReleaseAttestations } from "../lib/api";

export default function ContractsView() {
  const [queryReleaseId, setQueryReleaseId] = useState("11");
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryResult, setQueryResult] = useState<any>(null);
  const [queryError, setQueryError] = useState<string | null>(null);

  const contractDetails = {
    address: "0x5FbDB2315678afecb367f032d93F642f64180aa3",
    network: "Hardhat / Anvil Local",
    chainId: 31337,
    rpcUrl: "http://127.0.0.1:8545",
    compiler: "Solidity ^0.8.20",
    deployer: "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
  };

  const handleQueryOnChain = async () => {
    if (!queryReleaseId.trim()) return;
    setQueryLoading(true);
    setQueryError(null);
    setQueryResult(null);

    try {
      const [rel, audit, attestations] = await Promise.all([
        getRelease(queryReleaseId.trim()),
        getReleaseResult(queryReleaseId.trim()).catch(() => null),
        getReleaseAttestations(queryReleaseId.trim()).catch(() => ({ count: 0, attestations: [] })),
      ]);

      setQueryResult({
        release: rel,
        audit,
        attestations,
      });
    } catch (err: any) {
      setQueryError(err.message || "Failed to query on-chain release");
    } finally {
      setQueryLoading(false);
    }
  };

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
          <FileCode2 className="w-3.5 h-3.5 text-white" />
          Smart Contract Verification
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white">
          QuorumVerifier.sol
        </h1>
        <p className="text-base text-zinc-400 max-w-2xl">
          The smart contract is the single persistent source of truth and authoritative verification
          component. Consensus and final verdicts are computed directly on-chain.
        </p>
      </div>

      {/* Contract Metadata Card */}
      <div className="rounded-2xl bg-zinc-950/80 border border-white/10 p-7 space-y-6 shadow-xl">
        <div className="flex items-center justify-between pb-4 border-b border-white/5">
          <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">
            Deployed Instance Configuration
          </span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 text-white text-xs font-mono border border-white/15">
            <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
            Live on Anvil
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 rounded-xl bg-black border border-white/5 space-y-1">
            <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
              Contract Address
            </span>
            <span className="font-mono text-zinc-200 block truncate">{contractDetails.address}</span>
          </div>

          <div className="p-3.5 rounded-xl bg-black border border-white/5 space-y-1">
            <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
              Network & Chain ID
            </span>
            <span className="font-mono text-zinc-200 block">
              {contractDetails.network} (Chain ID: {contractDetails.chainId})
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-black border border-white/5 space-y-1">
            <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
              RPC Endpoint
            </span>
            <span className="font-mono text-zinc-200 block">{contractDetails.rpcUrl}</span>
          </div>

          <div className="p-3.5 rounded-xl bg-black border border-white/5 space-y-1">
            <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
              Deployer Account
            </span>
            <span className="font-mono text-zinc-200 block truncate">{contractDetails.deployer}</span>
          </div>
        </div>
      </div>

      {/* Decision Rules Matrix */}
      <div className="space-y-4">
        <h3 className="text-sm font-mono uppercase tracking-wider text-zinc-400">
          On-Chain Consensus Decision Rules
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="rounded-2xl bg-zinc-950/80 border border-white/10 p-6 space-y-3">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/10 text-white text-xs font-mono border border-white/20">
              <CheckCircle2 className="w-3 h-3 text-white" />
              1. VERIFIED
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              A valid artifact hash reaches the configured quorum threshold AND that quorum hash equals the published hash.
            </p>
            <div className="font-mono text-[10px] text-zinc-500 bg-black p-2.5 rounded border border-white/5">
              quorumHash == publishedHash
            </div>
          </div>

          <div className="rounded-2xl bg-zinc-950/80 border border-white/10 p-6 space-y-3">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-red-500/10 text-red-300 text-xs font-mono border border-red-500/20">
              <ShieldAlert className="w-3 h-3 text-red-400" />
              2. REJECTED
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              A valid artifact hash reaches the configured quorum, BUT that quorum hash differs from the official published artifact hash.
            </p>
            <div className="font-mono text-[10px] text-zinc-500 bg-black p-2.5 rounded border border-white/5">
              quorumHash != publishedHash
            </div>
          </div>

          <div className="rounded-2xl bg-zinc-950/80 border border-white/10 p-6 space-y-3">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-300 text-xs font-mono border border-amber-500/20">
              <HelpCircle className="w-3 h-3 text-amber-400" />
              3. DISPUTED
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              No single artifact hash reaches the required quorum after all builders have submitted attestations.
            </p>
            <div className="font-mono text-[10px] text-zinc-500 bg-black p-2.5 rounded border border-white/5">
              maxVotes &lt; quorumRequired
            </div>
          </div>
        </div>
      </div>

      {/* Live On-Chain Query Section */}
      <div className="rounded-2xl bg-zinc-950/80 border border-white/10 p-7 space-y-6 shadow-xl">
        <div>
          <h3 className="text-lg font-bold text-white">Live On-Chain State Inspector</h3>
          <p className="text-xs text-zinc-400 mt-1">
            Directly query <code className="font-mono text-zinc-300">getRelease(releaseId)</code> and{" "}
            <code className="font-mono text-zinc-300">getAttestations(releaseId)</code> from the smart contract.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3">
          <input
            type="text"
            placeholder="Enter release ID (e.g. 11)"
            value={queryReleaseId}
            onChange={(e) => setQueryReleaseId(e.target.value)}
            className="w-full sm:w-64 bg-black border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white placeholder-zinc-500 font-mono focus:outline-none focus:border-white/30"
          />

          <button
            type="button"
            onClick={handleQueryOnChain}
            disabled={queryLoading}
            className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-white text-black font-semibold text-xs uppercase tracking-wider hover:bg-zinc-200 transition-colors cursor-pointer font-mono inline-flex items-center justify-center gap-2"
          >
            {queryLoading ? (
              <span>Querying Node...</span>
            ) : (
              <>
                <Search className="w-3.5 h-3.5" />
                <span>Query Contract</span>
              </>
            )}
          </button>
        </div>

        {queryError && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-300 font-mono">
            {queryError}
          </div>
        )}

        {queryResult && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            className="p-5 rounded-xl bg-black border border-white/10 space-y-4 text-xs font-mono"
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <span className="text-zinc-400">On-Chain Record: Release #{queryReleaseId}</span>
              <span className="px-2.5 py-0.5 rounded bg-white/10 text-white font-bold">
                {queryResult.release.status}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
              <div>
                <span className="text-zinc-500 block">Repository URL:</span>
                <span className="text-zinc-200 truncate block">{queryResult.release.repository_url}</span>
              </div>
              <div>
                <span className="text-zinc-500 block">Pinned Commit:</span>
                <span className="text-zinc-200 truncate block">{queryResult.release.commit_sha}</span>
              </div>
              <div>
                <span className="text-zinc-500 block">Published Hash:</span>
                <span className="text-zinc-200 truncate block">{queryResult.release.published_hash}</span>
              </div>
              <div>
                <span className="text-zinc-500 block">Quorum Rule:</span>
                <span className="text-zinc-200 block">
                  {queryResult.release.quorum_required} of {queryResult.release.builder_count} consensus
                </span>
              </div>
            </div>

            {queryResult.attestations && queryResult.attestations.attestations?.length > 0 && (
              <div className="pt-3 border-t border-white/5 space-y-2">
                <span className="text-zinc-400 block">
                  Submitted Builder Attestations ({queryResult.attestations.count}):
                </span>
                <div className="space-y-1.5">
                  {queryResult.attestations.attestations.map((a: any, i: number) => (
                    <div key={i} className="p-2 rounded bg-zinc-950 border border-white/5 flex items-center justify-between text-[10px]">
                      <span className="text-zinc-400 truncate max-w-[200px]">Sender: {a.builder}</span>
                      <span className="text-zinc-200 truncate max-w-[300px]">Hash: {a.artifactHash}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
