import React from 'react';
import { BuilderTesting } from './BuilderTesting';
import { FlowLines } from './FlowLines';
import { BuilderGrid } from './BuilderGrid';
import { HashComparison } from './HashComparison';
import { QuorumDecision } from './QuorumDecision';
import { VerdictCard } from './VerdictCard';
import { BlockchainStatus } from '../blockchain/BlockchainStatus';
import type {
  BuilderData,
  VerificationPhase,
  QuorumDecisionResult,
  BlockchainRecord,
  BuilderId,
} from '../../types';

export interface VerificationPipelineProps {
  phase: VerificationPhase;
  builders: BuilderData[];
  onSelectBuilder: (builder: BuilderData) => void;
  decisionResult: QuorumDecisionResult | null;
  blockchainRecord: BlockchainRecord | null;
  mismatchedBuilders: BuilderId[];
}

export const VerificationPipeline: React.FC<VerificationPipelineProps> = ({
  phase,
  builders,
  onSelectBuilder,
  decisionResult,
  blockchainRecord,
  mismatchedBuilders,
}) => {
  const isFlowing = phase === 'initializing' || phase === 'building';
  const showResults = phase === 'comparing' || phase === 'evaluating' || phase === 'completed';

  return (
    <section
      aria-label="Verification Pipeline"
      style={{
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}
    >
      {/* 1. Master Builder Testing Node */}
      <BuilderTesting phase={phase} />

      {/* 2. Animated Downward Dashed Flow Lines to Builders A, B, C */}
      <FlowLines isFlowing={isFlowing} />

      {/* 3. Three Independent Builder Cards */}
      <BuilderGrid
        builders={builders}
        onSelectBuilder={onSelectBuilder}
        mismatchedBuilders={mismatchedBuilders}
      />

      {/* 4. Sequential Post-Build Stages */}
      {showResults && (
        <div style={{ width: '100%', maxWidth: '960px' }}>
          {/* Hash Comparison Matrix */}
          <HashComparison builders={builders} />

          {/* Quorum Decision Evaluation */}
          {decisionResult && <QuorumDecision decision={decisionResult} />}

          {/* Blockchain On-Chain Record */}
          {blockchainRecord && <BlockchainStatus record={blockchainRecord} />}

          {/* Final Verdict Card */}
          {decisionResult && <VerdictCard decision={decisionResult} />}
        </div>
      )}
    </section>
  );
};
