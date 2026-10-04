"use client";

import React, { useState } from "react";
import {
  LayoutDashboard,
  ShieldCheck,
  Cpu,
  History,
  FileCode2,
  Settings,
  Menu,
  X,
  Radio,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface SidebarProps {
  activeTab?: string;
  onTabChange?: (tab: string) => void;
}

export default function Sidebar({
  activeTab = "dashboard",
  onTabChange = () => {},
}: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems = [
    {
      id: "dashboard",
      label: "Dashboard",
      icon: LayoutDashboard,
      badge: null,
    },
    {
      id: "verifications",
      label: "Verifications",
      icon: ShieldCheck,
      badge: "3",
    },
    {
      id: "builders",
      label: "Builder Enclaves",
      icon: Cpu,
      badge: "Active",
    },
    {
      id: "releases",
      label: "Recent Releases",
      icon: History,
      badge: null,
    },
    {
      id: "contracts",
      label: "Smart Contract",
      icon: FileCode2,
      badge: "v1.0",
    },
  ];

  const sidebarContent = (
    <div className="flex flex-col h-full justify-between bg-black text-white p-5 select-none font-sans">
      {/* Top Brand Section */}
      <div className="space-y-6">
        <div className="flex items-center justify-between px-2 pt-1 pb-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-white text-black flex items-center justify-center font-bold text-base shadow-[0_0_15px_rgba(255,255,255,0.2)]">
              <img src="/quorum-logo.png" alt="Quorum Logo" />
            </div>
            <div> 
              <span className="font-extrabold tracking-tight text-sm text-white block">
                QUORUM
              </span>
              <span className="text-[10px] font-mono text-zinc-500 block -mt-0.5">
                Build Verifier
              </span>
            </div>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-zinc-400">
            v1.4
          </span>
        </div>

        {/* Navigation Items */}
        <div className="space-y-1">
          <div className="text-[10px] font-mono uppercase tracking-widest text-zinc-500 px-3 pb-2">
            Overview
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => {
                  onTabChange(item.id);
                  setMobileOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-150 cursor-pointer ${
                  isActive
                    ? "bg-white text-black font-semibold shadow-sm"
                    : "text-zinc-400 hover:text-white hover:bg-white/5"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`w-4 h-4 ${isActive ? "text-black" : "text-zinc-400"}`} />
                  <span>{item.label}</span>
                </div>

                {item.badge && (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                      isActive
                        ? "bg-black/10 text-black font-bold"
                        : "bg-white/5 text-zinc-400 border border-white/5"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Network & Protocol Status */}
        <div className="pt-4 space-y-3">
          <div className="text-[10px] font-mono uppercase tracking-widest text-zinc-500 px-3">
            Network Status
          </div>
          <div className="mx-1 p-3 rounded-xl bg-zinc-950 border border-white/10 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-zinc-400 flex items-center gap-1.5">
                <Radio className="w-3 h-3 text-white animate-pulse" />
                Consensus
              </span>
              <span className="text-[10px] font-mono text-zinc-300">Hardhat Local</span>
            </div>
            <div className="flex items-center justify-between text-[11px] text-zinc-500 pt-1 border-t border-white/5 font-mono">
              <span>Enclaves Active:</span>
              <span className="text-zinc-300">3 / 3 Online</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Profile / Contract Info */}
      <div className="pt-6 border-t border-white/10 space-y-3">
        <div className="flex items-center justify-between px-2 py-1.5 rounded-xl hover:bg-white/5 transition-colors cursor-pointer text-zinc-400 hover:text-white">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-[10px] font-mono font-bold text-white">
              0x
            </div>
            <div className="text-left">
              <div className="text-xs font-mono text-zinc-200">0x5FbD...8aa3</div>
              <div className="text-[10px] text-zinc-500">QuorumVerifier</div>
            </div>
          </div>
          <Settings className="w-3.5 h-3.5 text-zinc-500 hover:text-white" />
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile Top Bar with Hamburger */}
      <div className="lg:hidden flex items-center justify-between px-5 py-4 border-b border-white/10 bg-black sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-white text-black flex items-center justify-center font-bold text-sm">
            Q
          </div>
          <span className="font-extrabold tracking-tight text-sm text-white">
            QUORUM
          </span>
        </div>

        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 rounded-xl bg-zinc-900 border border-white/10 text-zinc-300 hover:text-white"
          aria-label="Toggle navigation"
        >
          {mobileOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
        </button>
      </div>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="lg:hidden fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex"
            onClick={() => setMobileOpen(false)}
          >
            <motion.div
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="w-72 max-w-[80vw] h-full bg-black border-r border-white/10 shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              {sidebarContent}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Desktop Sticky Sidebar */}
      <aside className="hidden lg:block w-64 shrink-0 h-screen sticky top-0 border-r border-white/10 bg-black z-30">
        {sidebarContent}
      </aside>
    </>
  );
}
