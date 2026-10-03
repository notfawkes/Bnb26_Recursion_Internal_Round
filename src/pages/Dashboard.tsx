import React, { useState, useRef } from 'react';
import { PageHeader } from '../components/verification/PageHeader';
import { RepositoryInput } from '../components/verification/RepositoryInput';
import { VerificationPipeline } from '../components/verification/VerificationPipeline';
import { BuilderDetail } from '../components/verification/BuilderDetail';
import type {
  BuilderData,
  BuilderId,
  VerificationPhase,
  VerificationScenario,
  QuorumPolicy,
  QuorumDecisionResult,
  BlockchainRecord,
  VerificationStep,
} from '../types';

const INITIAL_STEPS: VerificationStep[] = [
  { id: '1', label: 'Repository fetched', status: 'pending' },
  { id: '2', label: 'Commit verified', status: 'pending' },
  { id: '3', label: 'Dependencies installed', status: 'pending' },
  { id: '4', label: 'Building artifact', status: 'pending' },
  { id: '5', label: 'Artifact generation', status: 'pending' },
  { id: '6', label: 'SHA-256 calculation', status: 'pending' },
  { id: '7', label: 'Attestation generation', status: 'pending' },
  { id: '8', label: 'Signature verification', status: 'pending' },
];

const INITIAL_BUILDERS: BuilderData[] = [
  {
    id: 'A',
    name: 'Builder A',
    dockerImage: 'docker: alpine-builder-a:3.19',
    environment: 'Linux x86_64 / Alpine 3.19',
    compiler: 'gcc 13.2.1 / musl libc',
    status: 'idle',
    progress: 0,
    currentStepIndex: 0,
    steps: JSON.parse(JSON.stringify(INITIAL_STEPS)),
    publicKey: 'ed25519_pk_7b99c2d1fae489c72e45a019488',
  },
  {
    id: 'B',
    name: 'Builder B',
    dockerImage: 'docker: debian-builder-b:12-slim',
    environment: 'Linux x86_64 / Debian 12 Bookworm',
    compiler: 'gcc 12.2.0 / glibc 2.36',
    status: 'idle',
    progress: 0,
    currentStepIndex: 0,
    steps: JSON.parse(JSON.stringify(INITIAL_STEPS)),
    publicKey: 'ed25519_pk_9a12c884eb09210c4fe91129aa7',
  },
  {
    id: 'C',
    name: 'Builder C',
    dockerImage: 'docker: ubuntu-builder-c:24.04',
    environment: 'Linux x86_64 / Ubuntu 24.04 LTS',
    compiler: 'gcc 13.2.0 / glibc 2.39',
    status: 'idle',
    progress: 0,
    currentStepIndex: 0,
    steps: JSON.parse(JSON.stringify(INITIAL_STEPS)),
    publicKey: 'ed25519_pk_44fe881903ba21c44901ee77218',
  },
];

const CANONICAL_HASH = 'a81f72e9c21b4a09e13d9876a3e144dc921f008892ca8ef1284532bfa1199c21';
const ROGUE_HASH = 'b72c1982af330dc85a769821ef9a12bc55d048997a0014ee8812c3210aa982af';

export const Dashboard: React.FC = () => {
  const [isVerifying, setIsVerifying] = useState(false);
  const [phase, setPhase] = useState<VerificationPhase>('idle');
  const [repoUrl, setRepoUrl] = useState('https://github.com/example/project');
  const [commitSha, setCommitSha] = useState('8f72a91b4c3e');

  const [builders, setBuilders] = useState<BuilderData[]>(INITIAL_BUILDERS);
  const [selectedBuilder, setSelectedBuilder] = useState<BuilderData | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  const [decisionResult, setDecisionResult] = useState<QuorumDecisionResult | null>(null);
  const [blockchainRecord, setBlockchainRecord] = useState<BlockchainRecord | null>(null);
  const [mismatchedBuilders, setMismatchedBuilders] = useState<BuilderId[]>([]);

  const timerRef = useRef<number | null>(null);

  const handleStartVerification = (params: {
    repoUrl: string;
    commitSha: string;
    policy: QuorumPolicy;
    scenario: VerificationScenario;
  }) => {
    setRepoUrl(params.repoUrl);
    setCommitSha(params.commitSha);

    // Reset builders
    const freshBuilders: BuilderData[] = INITIAL_BUILDERS.map((b) => ({
      ...b,
      status: 'processing',
      progress: 5,
      currentStepIndex: 0,
      steps: INITIAL_STEPS.map((s, idx) => ({
        ...s,
        status: idx === 0 ? 'in_progress' : 'pending',
      })),
      hash: undefined,
      isCompromised: params.scenario === 'compromised_builder_c' && b.id === 'C',
    }));

    setBuilders(freshBuilders);
    setIsVerifying(true);
    setPhase('initializing');
    setDecisionResult(null);
    setBlockchainRecord(null);
    setMismatchedBuilders([]);

    // Run simulation timeline
    runSimulationTimeline(freshBuilders, params.scenario, params.policy, params.commitSha);
  };

  const runSimulationTimeline = (
    currentBuilders: BuilderData[],
    targetScenario: VerificationScenario,
    currentPolicy: QuorumPolicy,
    currentSha: string
  ) => {
    let stepCount = 0;
    const totalSteps = INITIAL_STEPS.length;

    const interval = window.setInterval(() => {
      stepCount++;

      if (stepCount === 1) {
        setPhase('building');
      }

      setBuilders((prev) =>
        prev.map((b) => {
          const stepIndex = Math.min(stepCount - 1, totalSteps - 1);
          const progress = Math.min(100, Math.round(((stepIndex + 1) / totalSteps) * 100));

          const updatedSteps = b.steps.map((st, idx) => {
            if (idx < stepIndex) return { ...st, status: 'completed' as const };
            if (idx === stepIndex && stepCount <= totalSteps) return { ...st, status: 'in_progress' as const };
            return { ...st, status: 'pending' as const };
          });

          return {
            ...b,
            progress,
            currentStepIndex: stepIndex,
            steps: updatedSteps,
          };
        })
      );

      // Once all build steps complete
      if (stepCount >= totalSteps) {
        window.clearInterval(interval);

        // Finalize builder completion and calculate hashes
        const finalBuilders = currentBuilders.map((b) => {
          const isRogue = targetScenario === 'compromised_builder_c' && b.id === 'C';
          const calculatedHash = isRogue ? ROGUE_HASH : CANONICAL_HASH;

          return {
            ...b,
            status: 'complete' as const,
            progress: 100,
            hash: calculatedHash,
            signature: `MEQCI${b.id}8Fa39bc998ae4e190ba324b1a4e9b7201c90f230daef${b.id}=`,
            isCompromised: isRogue,
            steps: b.steps.map((st) => ({
              ...st,
              status: isRogue && st.id === '5' ? ('failed' as const) : ('completed' as const),
              detail: isRogue && st.id === '5' ? 'Payload Divergence Injected' : 'Verified',
            })),
          };
        });

        setBuilders(finalBuilders);
        setPhase('comparing');

        // Check mismatches
        const mismatches: BuilderId[] =
          targetScenario === 'compromised_builder_c' ? ['C'] : [];
        setMismatchedBuilders(mismatches);

        // Transition to Quorum evaluation & Blockchain after brief realistic delay
        setTimeout(() => {
          setPhase('evaluating');

          const agreementCount = targetScenario === 'compromised_builder_c' ? 2 : 3;
          const totalCount = 3;
          const required = currentPolicy === '3-of-3' ? 3 : 2;
          const isQuorumMet = agreementCount >= required;

          const decision: QuorumDecisionResult = {
            decision: isQuorumMet ? 'ACCEPTED' : 'REJECTED',
            agreementCount,
            totalCount,
            policy: currentPolicy,
            isQuorumMet,
            flaggedBuilders: mismatches,
            summary: isQuorumMet
              ? `${agreementCount}/${totalCount} builders agreed on canonical hash ${CANONICAL_HASH.slice(0, 16)}...`
              : `Quorum policy ${currentPolicy} requires all builders to agree, but Builder C produced divergent artifact.`,
          };

          const blockRecord: BlockchainRecord = {
            network: 'Quorum Private Permissioned EVM (ChainID: 1337)',
            smartContract: '0x91A456C872F129a009B8c72834b29c991872F',
            blockNumber: 184921,
            txHash: '0x8af9201ceb3490918fa2409710cc8791024821c',
            timestamp: new Date().toISOString(),
            evidence: [
              { label: 'Builder Identities Authenticated', verified: true, detail: '3/3 verified against Registry' },
              { label: 'Source & Pinned Commit Anchor', verified: true, detail: `Commit ${currentSha.slice(0, 7)} confirmed` },
              { label: 'Artifact Cryptographic Digests', verified: true, detail: 'Bit-for-bit comparison logged' },
              { label: 'in-toto Attestation Signatures', verified: true, detail: 'Ed25519 digital signatures validated' },
              { label: 'Quorum Policy Threshold Applied', verified: true, detail: `${currentPolicy} evaluation result immutable` },
            ],
          };

          setDecisionResult(decision);
          setBlockchainRecord(blockRecord);
          setPhase('completed');
        }, 1000);
      }
    }, 450);

    timerRef.current = interval;
  };

  const handleReset = () => {
    if (timerRef.current) window.clearInterval(timerRef.current);
    setIsVerifying(false);
    setPhase('idle');
    setBuilders(INITIAL_BUILDERS);
    setDecisionResult(null);
    setBlockchainRecord(null);
    setMismatchedBuilders([]);
    setSelectedBuilder(null);
  };

  const handleSelectBuilder = (builder: BuilderData) => {
    const current = builders.find((b) => b.id === builder.id) || builder;
    setSelectedBuilder(current);
    setIsDetailOpen(true);
  };

  return (
    <>
      <PageHeader />

      <RepositoryInput
        onStartVerification={handleStartVerification}
        isVerifying={isVerifying}
        onReset={handleReset}
      />

      {isVerifying && (
        <VerificationPipeline
          phase={phase}
          builders={builders}
          onSelectBuilder={handleSelectBuilder}
          decisionResult={decisionResult}
          blockchainRecord={blockchainRecord}
          mismatchedBuilders={mismatchedBuilders}
        />
      )}

      {/* Builder Step Detail Modal */}
      <BuilderDetail
        builder={selectedBuilder}
        isOpen={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
        repoUrl={repoUrl}
        commitSha={commitSha}
      />
    </>
  );
};
