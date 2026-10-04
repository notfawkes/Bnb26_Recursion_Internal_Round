/**
 * Quorum Backend API Client
 * Connects the Next.js frontend to the authoritative FastAPI + Anvil smart contract verification pipeline.
 */

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

export interface CreateReleasePayload {
  repository_url: string;
  commit_sha: string;
  build_config_id?: string;
  published_hash: string;
  artifact_name?: string;
  builder_count?: number;
  quorum_required?: number;
}

export interface CreateReleaseResponse {
  release_id: string;
  repository_url: string;
  repository?: string;
  commit_sha: string;
  commit?: string;
  build_config_id: string;
  published_hash: string;
  artifact_name: string;
  builder_count: number;
  quorum_required: number;
  status: string;
  created_at: string;
}

export interface BuilderVerificationDetail {
  builder_id: string;
  status: string;
  artifact_name: string;
  artifact_sha256: string;
  signature_valid: boolean;
  identity_valid: boolean;
  source_match: boolean;
  commit_match: boolean;
  valid: boolean;
  status_detail: "AGREE" | "DISAGREE" | "INVALID";
}

export interface BlockchainRecord {
  release_id: string;
  published_hash: string;
  quorum_hash: string;
  decision: "VERIFIED" | "REJECTED" | "DISPUTED" | "NONE";
  is_finalized: boolean;
  create_release_tx: string | null;
  attestation_txs: string[];
  finalize_tx: string | null;
}

export interface VerificationResponse {
  release_id: string;
  repository_url: string;
  commit_sha: string;
  build_config_id: string;
  published_hash: string;
  builders: BuilderVerificationDetail[];
  local_quorum: {
    achieved: boolean;
    agreement: string;
    quorum_hash: string;
    expected_decision: string;
  };
  blockchain: BlockchainRecord;
  decision: "VERIFIED" | "REJECTED" | "DISPUTED";
  decision_source: string;
  blockchain_consistent: boolean;
}

export interface VerificationResultResponse {
  release_id: string;
  repository_url: string;
  commit_sha: string;
  published_hash: string;
  quorum_hash: string;
  decision: "VERIFIED" | "REJECTED" | "DISPUTED" | "NONE";
  is_finalized: boolean;
  decision_source: string;
}

export interface OnChainAttestation {
  builder: string;
  artifactHash: string;
  timestamp: number;
}

export interface AttestationsListResponse {
  release_id: string;
  count: number;
  attestations: OnChainAttestation[];
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function createRelease(
  payload: CreateReleasePayload
): Promise<CreateReleaseResponse> {
  const res = await fetch(`${API_BASE}/api/v1/releases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      repository_url: payload.repository_url,
      commit_sha: payload.commit_sha,
      build_config_id: payload.build_config_id || "python-package-v1",
      published_hash: payload.published_hash,
      artifact_name: payload.artifact_name || "sampleproject-3.0.0-py3-none-any.whl",
      builder_count: payload.builder_count || 3,
      quorum_required: payload.quorum_required || 2,
    }),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errData.detail || `Create release failed (${res.status})`);
  }

  return res.json();
}

export async function verifyRelease(
  releaseId: string
): Promise<VerificationResponse> {
  const res = await fetch(`${API_BASE}/api/v1/releases/${releaseId}/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errData.detail || `Verification failed (${res.status})`);
  }

  return res.json();
}

export async function getReleaseResult(
  releaseId: string
): Promise<VerificationResultResponse> {
  const res = await fetch(`${API_BASE}/api/v1/releases/${releaseId}/result`, {
    method: "GET",
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errData.detail || `Get result failed (${res.status})`);
  }

  return res.json();
}

export async function getReleaseAttestations(
  releaseId: string
): Promise<AttestationsListResponse> {
  const res = await fetch(
    `${API_BASE}/api/v1/releases/${releaseId}/attestations`,
    {
      method: "GET",
    }
  );

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errData.detail || `Get attestations failed (${res.status})`);
  }

  return res.json();
}

export interface BuilderModel {
  builder_id: string;
  name: string;
  role: string;
  wallet_address: string;
  public_key_id: string;
  public_key: string;
  execution_environment: string;
  container_image: string;
  signature_algorithm: string;
  status: "ONLINE" | "UNREGISTERED";
  is_registered_on_chain: boolean;
}

export async function listReleases(): Promise<CreateReleaseResponse[]> {
  const res = await fetch(`${API_BASE}/api/v1/releases`, {
    method: "GET",
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errData.detail || `List releases failed (${res.status})`);
  }

  return res.json();
}

export async function fetchBuilders(): Promise<BuilderModel[]> {
  const res = await fetch(`${API_BASE}/api/v1/builders`, {
    method: "GET",
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errData.detail || `Fetch builders failed (${res.status})`);
  }

  return res.json();
}

export async function getRelease(
  releaseId: string
): Promise<CreateReleaseResponse> {
  const res = await fetch(`${API_BASE}/api/v1/releases/${releaseId}`, {
    method: "GET",
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errData.detail || `Get release failed (${res.status})`);
  }

  return res.json();
}
