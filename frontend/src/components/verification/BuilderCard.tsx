import React from 'react';
import { Check, AlertTriangle, Layers, ExternalLink } from 'lucide-react';
import { Badge } from '../ui/Badge';
import { StatusIndicator } from '../ui/StatusIndicator';
import type { BuilderData } from '../../types';

export interface BuilderCardProps {
  builder: BuilderData;
  onClick: (builder: BuilderData) => void;
  isMismatch?: boolean;
}

export const BuilderCard: React.FC<BuilderCardProps> = ({
  builder,
  onClick,
  isMismatch = false,
}) => {
  const isComplete = builder.status === 'complete';
  const isProcessing = builder.status === 'processing';

  return (
    <div
      onClick={() => onClick(builder)}
      role="button"
      tabIndex={0}
      title="Click to view detailed builder verification pipeline"
      style={{
        backgroundColor: 'var(--bg-card)',
        border: `1.5px solid ${isMismatch ? 'var(--danger-border)' : 'var(--border-color)'}`,
        borderRadius: 'var(--radius-md)',
        padding: '20px',
        boxShadow: 'var(--shadow-sm)',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        outline: 'none',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)';
        e.currentTarget.style.boxShadow = 'var(--shadow-md)';
        e.currentTarget.style.borderColor = isMismatch ? 'var(--danger-color)' : 'var(--border-active)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
        e.currentTarget.style.borderColor = isMismatch ? 'var(--danger-border)' : 'var(--border-color)';
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              fontSize: '14px',
              letterSpacing: '0.04em',
              color: 'var(--text-primary)',
            }}
          >
            {builder.name}
          </span>
          <Badge variant="mono" size="sm">
            Node {builder.id}
          </Badge>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {isProcessing && (
            <Badge variant="warning" size="sm">
              <StatusIndicator status="processing" label="PROCESSING" />
            </Badge>
          )}

          {isComplete && !isMismatch && (
            <Badge variant="success" size="sm">
              <Check size={11} style={{ marginRight: '2px' }} /> COMPLETE
            </Badge>
          )}

          {isComplete && isMismatch && (
            <Badge variant="danger" size="sm">
              <AlertTriangle size={11} style={{ marginRight: '2px' }} /> DIVERGENT
            </Badge>
          )}

          <ExternalLink size={12} color="var(--text-muted)" />
        </div>
      </div>

      {/* Environment / Isolation Info */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '11px',
          color: 'var(--text-muted)',
          marginBottom: '16px',
          fontFamily: 'var(--font-mono)',
        }}
      >
        <Layers size={12} />
        <span>{builder.dockerImage}</span>
      </div>

      {/* Processing State */}
      {isProcessing && (
        <div style={{ marginTop: 'auto' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '12px',
              color: 'var(--text-secondary)',
              marginBottom: '6px',
              fontFamily: 'var(--font-mono)',
            }}
          >
            <span style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: '75%' }}>
              {builder.steps[builder.currentStepIndex]?.label || 'Building artifact...'}
            </span>
            <span>{Math.round(builder.progress)}%</span>
          </div>

          {/* Progress Bar */}
          <div
            style={{
              width: '100%',
              height: '6px',
              backgroundColor: 'var(--bg-surface)',
              borderRadius: '3px',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                width: `${builder.progress}%`,
                height: '100%',
                backgroundColor: 'var(--brand-color)',
                transition: 'width 0.25s ease',
              }}
            />
          </div>
        </div>
      )}

      {/* Completed State: Hash Display */}
      {isComplete && (
        <div
          style={{
            marginTop: 'auto',
            padding: '12px',
            backgroundColor: isMismatch ? 'var(--danger-bg)' : 'var(--bg-surface)',
            border: `1px solid ${isMismatch ? 'var(--danger-border)' : 'var(--border-subtle)'}`,
            borderRadius: 'var(--radius-sm)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '4px',
            }}
          >
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                fontWeight: 700,
                color: isMismatch ? 'var(--danger-color)' : 'var(--text-muted)',
                letterSpacing: '0.04em',
              }}
            >
              SHA-256 ARTIFACT
            </span>
            <span
              style={{
                fontSize: '10px',
                color: 'var(--text-muted)',
              }}
            >
              Ed25519 Signed
            </span>
          </div>

          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              fontWeight: 600,
              color: isMismatch ? 'var(--danger-color)' : 'var(--text-primary)',
              wordBreak: 'break-all',
              letterSpacing: '0.04em',
            }}
          >
            {builder.hash || 'Calculating...'}
          </div>
        </div>
      )}

      {/* Idle State */}
      {builder.status === 'idle' && (
        <div
          style={{
            marginTop: 'auto',
            padding: '12px',
            backgroundColor: 'var(--bg-surface)',
            borderRadius: 'var(--radius-sm)',
            textAlign: 'center',
            fontSize: '12px',
            color: 'var(--text-muted)',
          }}
        >
          Waiting for verification trigger...
        </div>
      )}

      {/* Footer hint */}
      <div
        style={{
          marginTop: '12px',
          textAlign: 'right',
          fontSize: '10px',
          color: 'var(--text-muted)',
        }}
      >
        Click card for step-by-step logs ➔
      </div>
    </div>
  );
};
