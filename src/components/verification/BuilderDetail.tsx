import React, { useEffect } from 'react';
import { X, Check, AlertTriangle, Layers, GitCommit, ShieldCheck, FileCheck } from 'lucide-react';
import { Badge } from '../ui/Badge';
import { StatusIndicator } from '../ui/StatusIndicator';
import type { BuilderData } from '../../types';

export interface BuilderDetailProps {
  builder: BuilderData | null;
  isOpen: boolean;
  onClose: () => void;
  repoUrl: string;
  commitSha: string;
}

export const BuilderDetail: React.FC<BuilderDetailProps> = ({
  builder,
  isOpen,
  onClose,
  repoUrl,
  commitSha,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'auto';
    };
  }, [isOpen, onClose]);

  if (!isOpen || !builder) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(24, 21, 18, 0.65)',
        backdropFilter: 'blur(3px)',
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '560px',
          backgroundColor: 'var(--bg-card)',
          border: '1.5px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-lg)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '90vh',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '18px 24px',
            borderBottom: '1px solid var(--border-color)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'var(--bg-surface)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
                fontSize: '16px',
                color: 'var(--text-primary)',
              }}
            >
              {builder.name}
            </span>
            <Badge variant="mono" size="sm">
              Node ID: {builder.id}
            </Badge>
            {builder.isCompromised && (
              <Badge variant="danger" size="sm">
                Compromised Node
              </Badge>
            )}
          </div>

          <button
            onClick={onClose}
            aria-label="Close details"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '28px',
              height: '28px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-secondary)',
              backgroundColor: 'var(--bg-card)',
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Scrollable Content */}
        <div
          style={{
            padding: '24px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
          }}
        >
          {/* Metadata Section */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '12px',
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '14px',
            }}
          >
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '2px', fontWeight: 600 }}>
                STATUS
              </div>
              <StatusIndicator
                status={builder.status}
                label={builder.status.toUpperCase()}
              />
            </div>

            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '2px', fontWeight: 600 }}>
                CONTAINER ISOLATION
              </div>
              <div style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Layers size={13} color="var(--text-muted)" />
                {builder.dockerImage}
              </div>
            </div>

            <div style={{ gridColumn: 'span 2' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '2px', fontWeight: 600 }}>
                SOURCE REPOSITORY
              </div>
              <div style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', wordBreak: 'break-all' }}>
                {repoUrl}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '2px', fontWeight: 600 }}>
                PINNED COMMIT
              </div>
              <div style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <GitCommit size={13} color="var(--text-muted)" />
                {commitSha}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '2px', fontWeight: 600 }}>
                TOOLCHAIN
              </div>
              <div style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                {builder.compiler}
              </div>
            </div>
          </div>

          {/* Verification Steps */}
          <div>
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                fontWeight: 700,
                letterSpacing: '0.08em',
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                marginBottom: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <FileCheck size={14} />
              VERIFICATION PROCESS
            </div>

            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              {builder.steps.map((step, idx) => {
                const isStepCompleted = step.status === 'completed';
                const isStepInProgress = step.status === 'in_progress';
                const isStepFailed = step.status === 'failed';

                return (
                  <div
                    key={step.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: isStepInProgress
                        ? 'var(--badge-bg)'
                        : 'var(--bg-surface)',
                      border: `1px solid ${
                        isStepInProgress
                          ? 'var(--border-active)'
                          : isStepFailed
                          ? 'var(--danger-border)'
                          : 'var(--border-subtle)'
                      }`,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span
                        style={{
                          width: '18px',
                          height: '18px',
                          borderRadius: '50%',
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '11px',
                          backgroundColor: isStepCompleted
                            ? 'var(--success-bg)'
                            : isStepFailed
                            ? 'var(--danger-bg)'
                            : 'var(--bg-card)',
                          color: isStepCompleted
                            ? 'var(--success-color)'
                            : isStepFailed
                            ? 'var(--danger-color)'
                            : 'var(--text-muted)',
                          border: `1px solid ${
                            isStepCompleted
                              ? 'var(--success-border)'
                              : isStepFailed
                              ? 'var(--danger-border)'
                              : 'var(--border-subtle)'
                          }`,
                        }}
                      >
                        {isStepCompleted ? (
                          <Check size={11} />
                        ) : isStepFailed ? (
                          <AlertTriangle size={11} />
                        ) : isStepInProgress ? (
                          <span
                            style={{
                              width: '6px',
                              height: '6px',
                              borderRadius: '50%',
                              backgroundColor: 'var(--warning-color)',
                            }}
                          />
                        ) : (
                          <span style={{ fontSize: '10px' }}>{idx + 1}</span>
                        )}
                      </span>

                      <span
                        style={{
                          fontSize: '13px',
                          fontWeight: isStepInProgress ? 600 : 500,
                          color: isStepCompleted
                            ? 'var(--text-primary)'
                            : isStepInProgress
                            ? 'var(--color-dark-brown)'
                            : 'var(--text-muted)',
                        }}
                      >
                        {step.label}
                      </span>
                    </div>

                    <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      {step.detail || (isStepCompleted ? 'DONE' : isStepInProgress ? 'RUNNING' : 'PENDING')}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Cryptographic Artifact & Keys */}
          {builder.status === 'complete' && (
            <div
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-sm)',
                padding: '14px',
              }}
            >
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: 'var(--text-secondary)',
                  marginBottom: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <ShieldCheck size={14} color="var(--success-color)" />
                CRYPTOGRAPHIC ATTESTATION
              </div>

              <div style={{ marginBottom: '8px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '2px' }}>
                  Artifact Digest (SHA-256):
                </span>
                <code
                  style={{
                    display: 'block',
                    padding: '6px 8px',
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    color: builder.isCompromised ? 'var(--danger-color)' : 'var(--text-primary)',
                    wordBreak: 'break-all',
                  }}
                >
                  {builder.hash}
                </code>
              </div>

              <div style={{ marginBottom: '8px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '2px' }}>
                  Builder Ed25519 Public Key:
                </span>
                <code
                  style={{
                    display: 'block',
                    padding: '6px 8px',
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-secondary)',
                    wordBreak: 'break-all',
                  }}
                >
                  {builder.publicKey || 'ed25519_pk_7b99c2d1fae489c72e45'}
                </code>
              </div>

              <div>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '2px' }}>
                  Digital Signature (in-toto statement envelope):
                </span>
                <code
                  style={{
                    display: 'block',
                    padding: '6px 8px',
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-muted)',
                    wordBreak: 'break-all',
                  }}
                >
                  {builder.signature || 'MEQCIDe719Fa34bc988ae4e190ba32...2a4e9b7201c='}
                </code>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
