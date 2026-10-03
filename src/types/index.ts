export type BuilderId = 'A' | 'B' | 'C';

export type BuilderStatus = 'idle' | 'processing' | 'complete' | 'failed';

export type StepStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

export interface VerificationStep {
  id: string;
  label: string;
  status: StepStatus;
  detail?: string;
}

export interface BuilderData {
  id: BuilderId;
  name: string;
  dockerImage: string;
  environment: string;
  compiler: string;
  status: BuilderStatus;
  progress: number;
  currentStepIndex: number;
  steps: VerificationStep[];
  hash?: string;
  signature?: string;
  publicKey?: string;
  isCompromised?: boolean;
}

export type VerificationPhase =
  | 'idle'
  | 'initializing'
  | 'building'
  | 'comparing'
  | 'evaluating'
  | 'completed';

export type VerificationScenario = 'normal' | 'compromised_builder_c';

export type QuorumPolicy = '2-of-3' | '3-of-3';

export interface HashComparisonResult {
  pair: [BuilderId, BuilderId];
  match: boolean;
  hash1: string;
  hash2: string;
}

export interface QuorumDecisionResult {
  decision: 'ACCEPTED' | 'REJECTED';
  agreementCount: number;
  totalCount: number;
  policy: QuorumPolicy;
  isQuorumMet: boolean;
  flaggedBuilders: BuilderId[];
  summary: string;
}

export interface BlockchainRecord {
  network: string;
  smartContract: string;
  blockNumber: number;
  txHash: string;
  timestamp: string;
  evidence: {
    label: string;
    verified: boolean;
    detail: string;
  }[];
}
