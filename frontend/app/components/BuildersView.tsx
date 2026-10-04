"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Cpu,
  Shield,
  KeyRound,
  CheckCircle2,
  Lock,
  Wallet,
  Container,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { fetchBuilders, BuilderModel } from "../lib/api";

export default function BuildersView() {
  const [builders, setBuilders] = useState<BuilderModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadBuilders = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBuilders();
      setBuilders(data);
    } catch (err: any) {
      console.error("Failed to load builders:", err);
      setError(err.message || "Failed to load builder registry from backend");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBuilders();
  }, []);

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
            <Cpu className="w-3.5 h-3.5 text-white" />
            Backend Builder Registry
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white">
            Builder Network
          </h1>
          <p className="text-base text-zinc-400 max-w-2xl leading-relaxed">
            Authorized builder instances registered with the protocol. Each builder operates in an
            isolated hermetic Docker container, signs artifact evidence using a unique Ed25519 keypair,
            and submits attestations via its designated Ethereum wallet address.
          </p>
        </div>

        <button
          onClick={loadBuilders}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-zinc-950 hover:bg-zinc-900 border border-white/10 text-xs font-mono text-zinc-300 hover:text-white transition-all cursor-pointer self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-300 font-mono flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="p-16 text-center text-zinc-500 font-mono text-xs flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin" />
          <span>Querying builder registry from backend...</span>
        </div>
      )}

      {/* Real Builders Detailed Cards */}
      {!loading && (
        <div className="space-y-8">
          {builders.map((builder, idx) => (
            <motion.div
              key={builder.builder_id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: idx * 0.08 }}
              className="rounded-2xl bg-zinc-950/80 border border-white/10 p-8 hover:border-white/25 transition-all shadow-2xl space-y-6"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-white/5">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-white text-black flex items-center justify-center font-bold text-base shadow-[0_0_20px_rgba(255,255,255,0.2)]">
                    0{idx + 1}
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white tracking-tight">
                      {builder.name}
                    </h3>
                    <span className="text-xs text-zinc-400 font-mono">
                      {builder.role} • ID: {builder.builder_id}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-mono border ${
                      builder.is_registered_on_chain
                        ? "bg-white/10 text-white border-white/20"
                        : "bg-zinc-900 text-zinc-500 border-white/5"
                    }`}
                  >
                    <CheckCircle2
                      className={`w-3.5 h-3.5 ${
                        builder.is_registered_on_chain ? "text-white" : "text-zinc-500"
                      }`}
                    />
                    {builder.is_registered_on_chain ? "On-Chain Registered" : "Standby / Unregistered"}
                  </span>
                </div>
              </div>

              {/* Spec Details Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="p-4 rounded-xl bg-black border border-white/5 space-y-1.5">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5 text-zinc-400" /> Execution Environment
                  </span>
                  <span className="text-zinc-200 block text-xs">
                    {builder.execution_environment}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-black border border-white/5 space-y-1.5">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 flex items-center gap-1.5">
                    <Container className="w-3.5 h-3.5 text-zinc-400" /> Docker Image Profile
                  </span>
                  <span className="font-mono text-zinc-200 block truncate text-xs">
                    {builder.container_image}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-black border border-white/5 space-y-1.5">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 flex items-center gap-1.5">
                    <Wallet className="w-3.5 h-3.5 text-zinc-400" /> Ethereum Signer Wallet (msg.sender)
                  </span>
                  <span className="font-mono text-white block truncate text-xs">
                    {builder.wallet_address || "None"}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-black border border-white/5 space-y-1.5">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 flex items-center gap-1.5">
                    <KeyRound className="w-3.5 h-3.5 text-zinc-400" /> Ed25519 Key Identifier
                  </span>
                  <span className="font-mono text-zinc-200 block truncate text-xs">
                    {builder.public_key_id} ({builder.signature_algorithm})
                  </span>
                </div>

                <div className="md:col-span-2 p-4 rounded-xl bg-black border border-white/5 space-y-1.5">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block">
                    Public Key Hex
                  </span>
                  <span className="font-mono text-zinc-400 block break-all text-[11px] bg-zinc-950 p-2.5 rounded border border-white/5">
                    {builder.public_key || "Not available"}
                  </span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Architectural FAQ: Why identical container configuration */}
      <div className="rounded-2xl bg-zinc-950 border border-white/10 p-8 sm:p-10 space-y-4">
        <h3 className="text-base font-bold text-white flex items-center gap-2.5">
          <Container className="w-5 h-5 text-white" />
          Why Are the Container Configurations Identical?
        </h3>
        <p className="text-xs text-zinc-400 leading-relaxed max-w-4xl">
          In reproducible build verification, <strong className="text-white">standardized build environments are mandatory</strong>. If builders ran differing OS distributions, compiler versions, or package toolchains, compiled wheels and binaries would vary in bytecode and timestamps, creating false discrepancies.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-2">
          <div className="p-4 rounded-xl bg-black border border-white/5 space-y-1.5">
            <span className="text-white font-semibold block">Identical Build Specification</span>
            <p className="text-zinc-400 leading-relaxed">
              All builders use the declared build config (<code className="text-zinc-200">python-package-v1</code>) with fixed timestamps (<code className="text-zinc-200">SOURCE_DATE_EPOCH</code>) and identical Python toolchains so that byte-for-byte binary reproducibility can be objectively proven.
            </p>
          </div>
          <div className="p-4 rounded-xl bg-black border border-white/5 space-y-1.5">
            <span className="text-white font-semibold block">Independent Trust Boundaries</span>
            <p className="text-zinc-400 leading-relaxed">
              While the image is standardized, the <strong className="text-zinc-200">execution is completely separate</strong>: separate container instances, separate disk mounts, distinct Ed25519 private keys, and distinct Ethereum wallets submitting evidence to the blockchain.
            </p>
          </div>
        </div>
      </div>

      {/* Security Principles Banner */}
      <div className="rounded-2xl bg-zinc-950 border border-white/10 p-8 sm:p-10 space-y-6">
        <h3 className="text-lg font-bold text-white flex items-center gap-2.5">
          <Lock className="w-5 h-5 text-white" />
          Protocol Isolation Guarantees
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs text-zinc-400 leading-relaxed font-sans">
          <div className="p-5 rounded-xl bg-black border border-white/5 space-y-2">
            <span className="text-white font-semibold text-sm block">1. Hermetic Isolation</span>
            <p>
              Build containers are executed with zero external host key mounts. All compilation and
              wheel generation occurs in pristine, disposable environments.
            </p>
          </div>
          <div className="p-5 rounded-xl bg-black border border-white/5 space-y-2">
            <span className="text-white font-semibold text-sm block">2. Zero Target Leakage</span>
            <p>
              Expected artifact hashes are strictly withheld from builder containers. Builders only
              receive repository coordinates and pinned commit SHAs.
            </p>
          </div>
          <div className="p-5 rounded-xl bg-black border border-white/5 space-y-2">
            <span className="text-white font-semibold text-sm block">3. Cryptographic Proof</span>
            <p>
              Attestations are signed on the host via Ed25519 and transmitted on-chain by the
              builder's authorized Ethereum wallet matching the contract whitelist.
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
