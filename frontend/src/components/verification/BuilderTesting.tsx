import React from 'react';
import { Cpu, CheckCircle, RefreshCw } from 'lucide-react';
import type { VerificationPhase } from '../../types';

export interface BuilderTestingProps {
  phase: VerificationPhase;
}

export const BuilderTesting: React.FC<BuilderTestingProps> = ({ phase }) => {
  const getPhaseInfo = () => {
    switch (phase) {
      case 'initializing':
        return {
          status: 'Initializing...',
          desc: 'Preparing independent container isolation...',
          icon: <RefreshCw size={18} className="animate-spin" style={{ animation: 'spin 1.5s linear infinite' }} />,
        };
      case 'building':
        return {
          status: 'Compiling...',
          desc: 'Builders independently building pinned commit in isolated Docker containers',
          icon: <Cpu size={18} color="var(--brand-color)" />,
        };
      case 'comparing':
        return {
          status: 'Comparing Hashes...',
          desc: 'Cross-verifying SHA-256 artifacts & digital signatures',
          icon: <RefreshCw size={18} style={{ animation: 'spin 2s linear infinite' }} />,
        };
      case 'evaluating':
      case 'completed':
        return {
          status: 'Quorum Verified',
          desc: 'All independent build attestations gathered and evaluated',
          icon: <CheckCircle size={18} color="var(--success-color)" />,
        };
      case 'idle':
      default:
        return {
          status: 'Ready',
          desc: 'Awaiting release verification trigger',
          icon: <Cpu size={18} />,
        };
    }
  };

  const info = getPhaseInfo();

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        margin: '0 auto',
        width: '100%',
        maxWidth: '460px',
      }}
    >
      <div
        style={{
          width: '100%',
          backgroundColor: 'var(--bg-card)',
          border: '1.5px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          padding: '18px 24px',
          textAlign: 'center',
          boxShadow: 'var(--shadow-sm)',
          position: 'relative',
          transition: 'all 0.2s ease',
        }}
      >
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            fontFamily: 'var(--font-mono)',
            fontSize: '13px',
            fontWeight: 700,
            letterSpacing: '0.1em',
            color: 'var(--brand-color)',
            textTransform: 'uppercase',
            marginBottom: '6px',
          }}
        >
          {info.icon}
          BUILDER TESTING
        </div>

        <div
          style={{
            fontSize: '14px',
            fontWeight: 600,
            color: 'var(--text-primary)',
            marginBottom: '4px',
          }}
        >
          {info.status}
        </div>

        <div
          style={{
            fontSize: '12px',
            color: 'var(--text-muted)',
            lineHeight: '1.4',
          }}
        >
          {info.desc}
        </div>
      </div>
    </div>
  );
};
