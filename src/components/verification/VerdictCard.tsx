import React from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';
import type { QuorumDecisionResult } from '../../types';

export interface VerdictCardProps {
  decision: QuorumDecisionResult;
}

export const VerdictCard: React.FC<VerdictCardProps> = ({ decision }) => {
  const isAccepted = decision.decision === 'ACCEPTED';

  return (
    <div
      className="fade-in"
      style={{
        backgroundColor: isAccepted ? 'var(--success-bg)' : 'var(--danger-bg)',
        border: `2px solid ${isAccepted ? 'var(--success-border)' : 'var(--danger-border)'}`,
        borderRadius: 'var(--radius-lg)',
        padding: '36px 24px',
        textAlign: 'center',
        boxShadow: 'var(--shadow-md)',
        marginBottom: '32px',
        transition: 'all 0.3s ease',
      }}
    >
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          backgroundColor: isAccepted ? 'var(--success-color)' : 'var(--danger-color)',
          color: '#FFFFFF',
          marginBottom: '16px',
          boxShadow: `0 0 20px ${isAccepted ? 'rgba(59, 110, 68, 0.3)' : 'rgba(158, 58, 51, 0.3)'}`,
        }}
      >
        {isAccepted ? <CheckCircle2 size={32} /> : <XCircle size={32} />}
      </div>

      <h2
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '24px',
          fontWeight: 800,
          letterSpacing: '0.08em',
          color: isAccepted ? 'var(--success-color)' : 'var(--danger-color)',
          textTransform: 'uppercase',
          marginBottom: '10px',
        }}
      >
        {isAccepted ? '✓ RELEASE ACCEPTED' : '✕ RELEASE REJECTED'}
      </h2>

      <p
        style={{
          fontSize: '15px',
          fontWeight: 600,
          color: 'var(--text-primary)',
          marginBottom: '6px',
        }}
      >
        {isAccepted
          ? `${decision.agreementCount} OF ${decision.totalCount} BUILDERS PRODUCED MATCHING ARTIFACTS`
          : 'QUORUM NOT MET — ARTIFACTS DIVERGED BEYOND ACCEPTABLE THRESHOLD'}
      </p>

      <div
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '13px',
          color: 'var(--text-muted)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '16px',
          marginTop: '8px',
        }}
      >
        <span>Policy Threshold: <strong>{decision.policy}</strong></span>
        <span>•</span>
        <span>Consensus Status: <strong>{isAccepted ? 'PASSED' : 'FAILED'}</strong></span>
      </div>
    </div>
  );
};
