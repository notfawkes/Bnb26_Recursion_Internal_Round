import React from 'react';
import { Check, X, ArrowLeftRight, Hash } from 'lucide-react';
import { Badge } from '../ui/Badge';
import type { BuilderData } from '../../types';

export interface HashComparisonProps {
  builders: BuilderData[];
}

export const HashComparison: React.FC<HashComparisonProps> = ({ builders }) => {
  const builderA = builders.find((b) => b.id === 'A');
  const builderB = builders.find((b) => b.id === 'B');
  const builderC = builders.find((b) => b.id === 'C');

  const hashA = builderA?.hash || '';
  const hashB = builderB?.hash || '';
  const hashC = builderC?.hash || '';

  const matchAB = Boolean(hashA && hashB && hashA === hashB);
  const matchAC = Boolean(hashA && hashC && hashA === hashC);
  const matchBC = Boolean(hashB && hashC && hashB === hashC);

  const pairs = [
    { label: 'Builder A ↔ Builder B', match: matchAB, hash1: hashA, hash2: hashB },
    { label: 'Builder A ↔ Builder C', match: matchAC, hash1: hashA, hash2: hashC },
    { label: 'Builder B ↔ Builder C', match: matchBC, hash1: hashB, hash2: hashC },
  ];

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
          marginBottom: '18px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Hash size={16} color="var(--brand-color)" />
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
            COMPARING ARTIFACTS
          </span>
        </div>

        <Badge variant="mono" size="sm">
          Bit-for-Bit Reproducibility Matrix
        </Badge>
      </div>

      {/* Builder Hashes Summary */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '12px',
          marginBottom: '20px',
        }}
      >
        {builders.map((b) => (
          <div
            key={b.id}
            style={{
              padding: '10px 14px',
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <div
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: 'var(--text-muted)',
                marginBottom: '4px',
              }}
            >
              {b.name}
            </div>
            <code
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                color: b.isCompromised ? 'var(--danger-color)' : 'var(--text-primary)',
                wordBreak: 'break-all',
                fontWeight: 500,
              }}
            >
              {b.hash || 'Calculating...'}
            </code>
          </div>
        ))}
      </div>

      {/* Pairwise Matches */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '12px',
        }}
      >
        {pairs.map((p, idx) => (
          <div
            key={idx}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              backgroundColor: p.match ? 'var(--success-bg)' : 'var(--danger-bg)',
              border: `1px solid ${p.match ? 'var(--success-border)' : 'var(--danger-border)'}`,
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ArrowLeftRight
                size={14}
                color={p.match ? 'var(--success-color)' : 'var(--danger-color)'}
              />
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                }}
              >
                {p.label}
              </span>
            </div>

            <Badge variant={p.match ? 'success' : 'danger'} size="sm">
              {p.match ? (
                <>
                  <Check size={11} style={{ marginRight: '2px' }} /> MATCH
                </>
              ) : (
                <>
                  <X size={11} style={{ marginRight: '2px' }} /> MISMATCH
                </>
              )}
            </Badge>
          </div>
        ))}
      </div>
    </div>
  );
};
