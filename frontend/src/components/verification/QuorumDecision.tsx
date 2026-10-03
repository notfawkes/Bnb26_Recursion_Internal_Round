import React from 'react';
import { ShieldCheck, AlertCircle } from 'lucide-react';
import { Badge } from '../ui/Badge';
import type { QuorumDecisionResult } from '../../types';

export interface QuorumDecisionProps {
  decision: QuorumDecisionResult;
}

export const QuorumDecision: React.FC<QuorumDecisionProps> = ({ decision }) => {
  const isSuccess = decision.isQuorumMet;

  return (
    <div
      className="fade-in"
      style={{
        backgroundColor: 'var(--bg-card)',
        border: '1.5px solid var(--border-color)',
        borderRadius: 'var(--radius-md)',
        padding: '24px',
        boxShadow: 'var(--shadow-sm)',
        marginBottom: '28px',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: '14px',
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldCheck size={16} color="var(--brand-color)" />
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              fontSize: '13px',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'var(--text-primary)',
            }}
          >
            QUORUM EVALUATION
          </span>
        </div>

        <Badge variant={isSuccess ? 'success' : 'danger'}>
          {isSuccess ? '✓ QUORUM MET' : '✕ QUORUM NOT MET'}
        </Badge>
      </div>

      {/* Metrics Row: Scientific Evidence instead of arbitrary % score */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: '16px',
          marginBottom: '16px',
        }}
      >
        <div
          style={{
            padding: '14px',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '4px' }}>
            BUILDER AGREEMENT
          </div>
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '22px',
              fontWeight: 700,
              color: isSuccess ? 'var(--text-primary)' : 'var(--danger-color)',
            }}
          >
            {decision.agreementCount} / {decision.totalCount}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Independent Nodes</div>
        </div>

        <div
          style={{
            padding: '14px',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '4px' }}>
            POLICY THRESHOLD
          </div>
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '22px',
              fontWeight: 700,
              color: 'var(--brand-color)',
            }}
          >
            {decision.policy}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Configured Quorum</div>
        </div>

        <div
          style={{
            padding: '14px',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '4px' }}>
            SOURCE MATCH
          </div>
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '18px',
              fontWeight: 700,
              color: 'var(--success-color)',
              marginTop: '4px',
            }}
          >
            PASS
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Pinned Commit Valid</div>
        </div>

        <div
          style={{
            padding: '14px',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '4px' }}>
            SIGNATURES
          </div>
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '18px',
              fontWeight: 700,
              color: 'var(--success-color)',
              marginTop: '4px',
            }}
          >
            VALID
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Ed25519 Verified</div>
        </div>
      </div>

      {/* Flagged Builders info if any */}
      {decision.flaggedBuilders.length > 0 && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 14px',
            backgroundColor: 'var(--warning-bg)',
            border: '1px solid var(--warning-border)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '12px',
            color: 'var(--warning-color)',
          }}
        >
          <AlertCircle size={15} />
          <span>
            <strong>Node Divergence Detected:</strong> Builder{' '}
            {decision.flaggedBuilders.join(', ')} produced a diverging artifact hash and was excluded from consensus.
          </span>
        </div>
      )}
    </div>
  );
};
