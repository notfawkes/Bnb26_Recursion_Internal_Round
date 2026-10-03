import React, { useState } from 'react';
import { GitBranch, Shield, RotateCcw, AlertTriangle } from 'lucide-react';
import { Button } from '../ui/Button';
import type { QuorumPolicy, VerificationScenario } from '../../types';

export interface RepositoryInputProps {
  onStartVerification: (params: {
    repoUrl: string;
    commitSha: string;
    policy: QuorumPolicy;
    scenario: VerificationScenario;
  }) => void;
  isVerifying: boolean;
  onReset: () => void;
}

export const RepositoryInput: React.FC<RepositoryInputProps> = ({
  onStartVerification,
  isVerifying,
  onReset,
}) => {
  const [repoUrl, setRepoUrl] = useState('https://github.com/example/project');
  const [commitSha, setCommitSha] = useState('8f72a91b4c3e');
  const [policy, setPolicy] = useState<QuorumPolicy>('2-of-3');
  const [scenario, setScenario] = useState<VerificationScenario>('normal');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl) return;
    onStartVerification({
      repoUrl,
      commitSha: commitSha || '8f72a91b4c3e',
      policy,
      scenario,
    });
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: 'var(--radius-md)',
        padding: '28px 32px',
        boxShadow: 'var(--shadow-md)',
        marginBottom: '40px',
        transition: 'all 0.2s ease',
      }}
    >
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '20px' }}>
          <label
            htmlFor="repoUrl"
            style={{
              display: 'block',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: 'var(--text-secondary)',
              marginBottom: '8px',
            }}
          >
            Repository URL
          </label>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-sm)',
              padding: '0 12px',
              transition: 'border-color 0.2s ease',
            }}
          >
            <GitBranch size={16} color="var(--text-muted)" style={{ marginRight: '8px' }} />
            <input
              id="repoUrl"
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/owner/repository"
              disabled={isVerifying}
              style={{
                width: '100%',
                padding: '12px 0',
                border: 'none',
                outline: 'none',
                background: 'transparent',
                fontSize: '14px',
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-primary)',
              }}
            />
          </div>
        </div>

        {/* Technical parameters row */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px',
            marginBottom: '24px',
          }}
        >
          {/* Commit SHA */}
          <div>
            <label
              htmlFor="commitSha"
              style={{
                display: 'block',
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                color: 'var(--text-muted)',
                marginBottom: '6px',
                textTransform: 'uppercase',
              }}
            >
              Pinned Commit SHA
            </label>
            <input
              id="commitSha"
              type="text"
              value={commitSha}
              onChange={(e) => setCommitSha(e.target.value)}
              disabled={isVerifying}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
                outline: 'none',
              }}
            />
          </div>

          {/* Quorum Policy */}
          <div>
            <label
              htmlFor="policySelect"
              style={{
                display: 'block',
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                color: 'var(--text-muted)',
                marginBottom: '6px',
                textTransform: 'uppercase',
              }}
            >
              Quorum Policy Threshold
            </label>
            <select
              id="policySelect"
              value={policy}
              onChange={(e) => setPolicy(e.target.value as QuorumPolicy)}
              disabled={isVerifying}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--text-primary)',
                fontSize: '12px',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value="2-of-3">2-of-3 (Fault Tolerant Quorum)</option>
              <option value="3-of-3">3-of-3 (Strict Unanimous Quorum)</option>
            </select>
          </div>

          {/* Demo Scenario Simulator */}
          <div>
            <label
              htmlFor="scenarioSelect"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                color: 'var(--text-muted)',
                marginBottom: '6px',
                textTransform: 'uppercase',
              }}
            >
              <AlertTriangle size={12} color="var(--color-muted-brown)" /> Simulation Mode
            </label>
            <select
              id="scenarioSelect"
              value={scenario}
              onChange={(e) => setScenario(e.target.value as VerificationScenario)}
              disabled={isVerifying}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-surface)',
                color: scenario === 'compromised_builder_c' ? 'var(--warning-color)' : 'var(--text-primary)',
                fontSize: '12px',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value="normal">Normal Release (All 3 Agree)</option>
              <option value="compromised_builder_c">Attack: Builder C Compromised</option>
            </select>
          </div>
        </div>

        {/* Action Button */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: '12px' }}>
          {!isVerifying ? (
            <Button
              type="submit"
              size="lg"
              icon={<Shield size={16} />}
              style={{ minWidth: '220px' }}
            >
              VERIFY RELEASE
            </Button>
          ) : (
            <Button
              type="button"
              variant="outline"
              size="lg"
              icon={<RotateCcw size={16} />}
              onClick={onReset}
              style={{ minWidth: '220px' }}
            >
              RESET VERIFICATION
            </Button>
          )}
        </div>
      </form>
    </div>
  );
};
