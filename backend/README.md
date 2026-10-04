# Quorum Person 3 FastAPI Backend Documentation

The **Quorum Person 3 Backend** is a database-free FastAPI application that orchestrates multi-builder release verification. It validates source repositories and pinned commit SHAs, invokes independent builder attestations, calculates expected quorum consensus, and commits all release state, builder evidence, and final verification decisions directly to the **Ethereum / Anvil Smart Contract** (`QuorumVerifier.sol`).

---

## 🏗️ Architecture Overview

```
GitHub Repository & Pinned Commit
              ↓
     FastAPI Backend (Person 3)
              ↓
    Builder Manager (Person 2)
  (Builder A, Builder B, Builder C)
              ↓
  Smart Contract (Person 1 Blockchain)
              ↓
    Authoritative Final Decision
     (VERIFIED / REJECTED / DISPUTED)
```

### Key Principles
1. **100% Database-Free**: No SQLite, PostgreSQL, or local DB persistence. The blockchain smart contract is the single, authoritative persistent source of truth.
2. **Independent Builders**: FastAPI constructs the standard `BuildRequest` without forwarding `published_hash`. Builders independently build from pinned commits and hash their output binaries.
3. **Multi-Signer Attestations**: Each builder's signed Ed25519 attestation is verified and submitted on-chain using that builder's specific Ethereum wallet (`msg.sender`).
4. **Authoritative On-Chain Decision**: The smart contract computes the final decision (`VERIFIED`, `REJECTED`, `DISPUTED`). Local `QuorumService` calculations serve only as pre-validation assertions.

---

## 🛠️ Requirements & Setup

### Prerequisites
- Python 3.11+
- Virtual environment (recommended)
- Optional: Running Anvil node on `http://127.0.0.1:8545` for live on-chain interaction.

### Installation

1. Navigate to the project root or `backend` folder:
   ```bash
   cd backend
   ```

2. Install dependencies:
   ```bash
   pip install -r ../requirements.txt
   ```

3. Ensure environment variables are configured in `.env` (or copy from `.env.example`):
   ```env
   APP_ENV=development

   # Blockchain Settings
   BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545
   BLOCKCHAIN_CHAIN_ID=31337
   BLOCKCHAIN_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
   BLOCKCHAIN_ABI_PATH=blockchain/deployments/QuorumVerifier.abi.json
   BLOCKCHAIN_DEPLOYMENT_PATH=blockchain/deployments/quorum-verifier.json
   BLOCKCHAIN_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

   # Builder Identity & Keys
   BUILDER_A_WALLET=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
   BUILDER_A_ETH_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

   BUILDER_B_WALLET=0x70997970C51812dc3A010C7d01b50e0d17dc79C8
   BUILDER_B_ETH_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d

   BUILDER_C_WALLET=0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC
   BUILDER_C_ETH_KEY=0x5de4111ffa188d0a0c50f056d7921102223a776d3cdd96c22d05e20d16e6e009

   BUILDER_D_WALLET=0x90F79bf6EB2c4f8090B5E0109d175057225cc8AC
   BUILDER_D_ETH_KEY=0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6

   # Feature Mode Flags
   USE_MOCK_BUILDERS=true
   USE_MOCK_BLOCKCHAIN=true
   ```

---

## 🚀 Running the Server

Start the Uvicorn server:
```bash
python -m uvicorn app.main:app --reload --port 8000
```

Interactive Documentation:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

---

## 📡 API Reference

### 1. Health Check
`GET /health`

**Response (`200 OK`)**:
```json
{
  "status": "ok",
  "service": "quorum-backend"
}
```

---

### 2. Create Release
`POST /api/v1/releases`

Validates repository URL, pinned commit SHA, published SHA-256 hash, and initializes release record directly on the blockchain.

**Request Body**:
```json
{
  "repository_url": "https://github.com/appstiwari/py-calculator",
  "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
  "build_config_id": "python-package-v1",
  "published_hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3ff9700ed99059ce090b84124",
  "artifact_name": "py-calculator.tar.gz",
  "builder_count": 3,
  "quorum_required": 2
}
```

**Response (`201 Created`)**:
```json
{
  "release_id": "1",
  "repository_url": "https://github.com/appstiwari/py-calculator",
  "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
  "build_config_id": "python-package-v1",
  "published_hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3ff9700ed99059ce090b84124",
  "artifact_name": "py-calculator.tar.gz",
  "builder_count": 3,
  "quorum_required": 2,
  "status": "CREATED",
  "created_at": "2026-10-04T01:30:00Z"
}
```

---

### 3. Get Release Details
`GET /api/v1/releases/{release_id}`

Fetches release state directly from the smart contract.

**Response (`200 OK`)**:
```json
{
  "release_id": "1",
  "repository_url": "https://github.com/appstiwari/py-calculator",
  "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
  "build_config_id": "python-package-v1",
  "published_hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3ff9700ed99059ce090b84124",
  "artifact_name": "py-calculator.tar.gz",
  "builder_count": 3,
  "quorum_required": 2,
  "status": "CREATED"
}
```

---

### 4. Execute Full Verification Flow
`POST /api/v1/releases/{release_id}/verify`

Executes complete verification flow:
1. Loads release from smart contract state.
2. Dispatches `BuildRequest` to Builder Manager.
3. Verifies builder identity and Ed25519 signatures.
4. Submits valid builder attestations to blockchain with builder wallets.
5. Finalizes release on-chain and reads authoritative decision.

**Query Parameters**:
- `scenario=NORMAL` (All 3 builders agree on published hash -> `VERIFIED`)
- `scenario=ONE_DISAGREE` (2 agree on published, 1 produces alternate -> `VERIFIED`)
- `scenario=STRICT_DISAGREE` (Policy 3-of-3, 1 disagrees -> `DISPUTED`)
- `scenario=WRONG_QUORUM` (Majority produce alternate hash -> `REJECTED`)

**Response (`200 OK`)**:
```json
{
  "release_id": "1",
  "local_quorum": {
    "quorum_hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3ff9700ed99059ce090b84124",
    "decision": "VERIFIED"
  },
  "blockchain": {
    "release_id": "1",
    "published_hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3ff9700ed99059ce090b84124",
    "quorum_hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3ff9700ed99059ce090b84124",
    "decision": "VERIFIED",
    "is_finalized": true,
    "create_release_tx": "0x4b9585...",
    "attestation_txs": [
      "0x1a2b...",
      "0x3c4d...",
      "0x5e6f..."
    ],
    "finalize_tx": "0xbad514..."
  },
  "decision": "VERIFIED",
  "decision_source": "BLOCKCHAIN",
  "blockchain_consistent": true
}
```

---

### 5. Get Stored Verification Result
`GET /api/v1/releases/{release_id}/result`

Retrieves finalized audit record directly from blockchain state.

---

### 6. Get Submitted Attestations
`GET /api/v1/releases/{release_id}/attestations`

Retrieves all builder attestations submitted on-chain for a release.

---

## ⚖️ Quorum Consensus Logic

| Decision | Condition |
| :--- | :--- |
| **`VERIFIED`** | Valid builder agreement $\ge$ `quorum_required`, AND Quorum Artifact Hash == Author's Published Hash. |
| **`REJECTED`** | Valid builder agreement $\ge$ `quorum_required`, BUT Quorum Artifact Hash $\neq$ Author's Published Hash. |
| **`DISPUTED`** | Valid builder agreement $<$ `quorum_required` (insufficient matching builder evidence). |

---

## 🧪 Running Tests

Execute the complete unit and integration test suite:

```bash
python -m pytest -v
```

Expected output:
```text
======================== 38 passed in 4.53s ========================
```

---

## 📄 Postman Collection

Use [`Quorum_Backend_API.postman_collection.json`](../Quorum_Backend_API.postman_collection.json) in Postman:
1. Import `Quorum_Backend_API.postman_collection.json`.
2. Execute **1. Health Check**.
3. Execute **2. Create Release**.
4. Execute **3. Verify Release (NORMAL)**.
5. Inspect `decision`, `decision_source: "BLOCKCHAIN"`, and `attestation_txs`.
