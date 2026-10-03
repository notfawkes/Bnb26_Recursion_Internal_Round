import React from 'react';

export const PageHeader: React.FC = () => {
  return (
    <div
      style={{
        textAlign: 'center',
        marginBottom: '32px',
      }}
    >
      <div
        style={{
          display: 'inline-block',
          fontFamily: 'var(--font-mono)',
          fontSize: '11px',
          fontWeight: 700,
          color: 'var(--brand-color)',
          letterSpacing: '0.15em',
          textTransform: 'uppercase',
          marginBottom: '8px',
        }}
      >
        Supply-Chain Cryptographic Consensus
      </div>
      <h1
        style={{
          fontSize: '28px',
          fontWeight: 700,
          color: 'var(--text-primary)',
          letterSpacing: '-0.02em',
          marginBottom: '10px',
        }}
      >
        VERIFY A SOFTWARE RELEASE
      </h1>
      <p
        style={{
          fontSize: '14px',
          color: 'var(--text-muted)',
          maxWidth: '560px',
          margin: '0 auto',
          lineHeight: '1.6',
        }}
      >
        Reproduce, compare, and verify a release using independent builders to detect supply-chain tampering and unauthorized source divergence.
      </p>
    </div>
  );
};
