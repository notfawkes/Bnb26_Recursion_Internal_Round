# Builder Engineer handoff: Steps 1–9

This report explains the complete Builder Engineer prototype in plain language. It is intended for the Builder, Quorum and Blockchain engineers to use as the shared handoff document.

## 1. What the Builder component does

The Builder component answers a narrow question:

> When three named builders independently build the same repository commit with the same approved configuration, what artifact did each builder actually produce?

It validates a five-field request, fetches one exact Git commit, builds it in a restricted Docker container, selects one wheel, hashes its bytes, signs the evidence with that builder's key and collects all three terminal results in one JSON file.

It deliberately does **not** compare the three hashes, vote, mark a release verified, write to a blockchain or expose an HTTP endpoint. Those decisions belong to the Quorum and Blockchain components.

## 2. Architecture at a glance

```text
Quorum request (five fields)
            |
            v
  Request Validator (once)
            |
            v
 Multi-Builder Orchestrator ---- one shared job_id
       |        |        |
       v        v        v
  builder-a builder-b builder-c       (sequential in V1)
       |        |        |
       +--------+--------+
                |
   Each single-builder pipeline:
   fetch exact commit -> isolated Docker build -> collect one wheel
   -> SHA-256 -> attestation -> Ed25519 signature
                |
                v
       combined-result.json
                |
                v
 Quorum Engineer verifies signatures, compares hashes and applies policy
```

The current three builder identities run on one host and use the same Docker image. They model three independent builders for a hackathon demo; they are not three production trust authorities.

## 3. Repository map

| Path | Responsibility |
| --- | --- |
| `builders/manager/request_validator.py` | Rejects unsafe or malformed requests before work begins. |
| `builders/manager/config.py` | Owns the approved image, command, artifact rule and limits. The caller cannot override them. |
| `builders/manager/repository.py` | Fetches only the requested commit and verifies the checked-out `HEAD`. |
| `builders/manager/executor.py` | Runs the approved command in a restricted temporary Docker container. |
| `builders/manager/artifact.py` | Selects exactly one safe, non-empty wheel up to 100 MiB. |
| `builders/manager/hashing.py` | Streams that wheel through SHA-256 and creates its manifest. |
| `builders/manager/attestation.py` | Describes the source, environment and artifact that one builder observed. |
| `builders/manager/signing.py` | Canonicalizes, signs and verifies attestations with Ed25519. |
| `builders/manager/pipeline.py` | Connects fetch, build, collect, hash and sign for one builder. |
| `builders/manager/orchestrator.py` | Runs A, B and C, preserves failures and saves their combined result. |
| `builders/manager/cli.py` | Provides local `keygen`, `build-one` and `build-all` commands. |
| `builders/runner/Dockerfile` | Defines the pinned Python build-tool image. |
| `builders/tests/` | Unit and workflow tests, including the Step 9 failure matrix. |
| `shared/specs/` | Contracts that the Builder and Quorum engineers must share. |

`builders/output/` and `builders/keys/` are intentionally ignored by Git. Generated builds were deleted after the final verification run. Each teammate should generate their own keys and outputs by following this report.

## 4. Input contract

The caller supplies exactly these five fields:

```json
{
  "release_id": "d4f2496e-5c5a-4c82-9fd5-f3c3012a524e",
  "repository_url": "https://github.com/pypa/sampleproject",
  "commit_sha": "621e4974ca25ce531773def586ba3ed8e736b3fc",
  "build_config_id": "python-package-v1",
  "builders": ["builder-a", "builder-b", "builder-c"]
}
```

The Builder Manager owns all commands, artifact paths and resource limits. They are not accepted from a frontend because user-supplied shell commands would turn the service into a remote command runner.

The validator enforces:

- `release_id` is a canonical lowercase UUID.
- `repository_url` is exactly an HTTPS `github.com/<owner>/<repo>` URL with no credentials, port, query or fragment.
- `commit_sha` is a full 40-character lowercase hexadecimal Git commit ID.
- `build_config_id` exists in the builder-owned allowlist.
- `builders` contains A, B and C exactly once each.
- The selected internal configuration has a safe artifact glob and positive timeout, CPU and memory limits.
- Missing and extra JSON fields are rejected.

The full contract is in `shared/specs/builder-request.md`.

## 5. Steps 1–9, one by one

### Step 1 — Request Validator

`validate_builder_request()` checks untrusted JSON and returns an immutable `ValidatedBuilderRequest`. No Git or Docker work happens for an invalid request. The output also contains the resolved builder-owned configuration, including limits.

### Step 2 — Repository Fetcher

`fetch_repository()` creates a fresh source directory, initializes Git, allows only the HTTPS transport, disables credential prompts, LFS downloads, replacement objects and redirects, and performs a depth-one fetch of the exact commit. It checks `git rev-parse HEAD` against the request and removes the remote afterward.

It also reads the commit timestamp. That timestamp becomes `SOURCE_DATE_EPOCH`, giving repeated builders the same stable time input.

### Step 3 — Controlled Build Configuration

`APPROVED_BUILD_CONFIGS` currently contains only `python-package-v1`:

- image: `quorum-python-package-v1:local`
- action: build one Python wheel with `python -m build --wheel --no-isolation`
- artifact selector: `dist/*.whl`
- timeout: 300 seconds
- CPU: 1
- memory: 512 MiB

The Dockerfile pins the Python base image by digest and pins `build`, `packaging`, `pyproject-hooks`, `setuptools` and `wheel` versions.

### Step 4 — Isolated Build Executor

`execute_build()` creates one temporary Docker container per builder. The source checkout is mounted read-only and the output folder read-write. The container has:

- no network;
- a read-only root filesystem;
- all Linux capabilities dropped;
- `no-new-privileges` enabled;
- a non-root user;
- fixed CPU, memory, process and time limits;
- a bounded temporary filesystem;
- deterministic environment inputs such as UTC, `PYTHONHASHSEED=0` and `SOURCE_DATE_EPOCH`.

The signing key is never mounted into the build container. A `finally` block force-removes the container whether the build succeeds, fails or raises a Docker error. Build logs are capped before being stored.

### Step 5 — Artifact Collector

For V1, the expected software output is exactly one wheel matching `dist/*.whl`. The collector rejects zero wheels, multiple wheels, symbolic links, files outside the job directory, empty files and files larger than 100 MiB.

It does not hash the source tree, logs or filename. It selects the one actual package that would be released.

### Step 6 — Hash Generator

`sha256_file()` reads the selected wheel in 1 MiB chunks, so a large allowed artifact is not loaded into memory all at once. It records:

```json
{
  "artifact": {
    "path": "dist/sampleproject-4.0.0-py3-none-any.whl",
    "size_bytes": 4660
  },
  "hash": {
    "algorithm": "sha256",
    "digest": "4209e70ec0bc11900d4bf453f156d14789a517febb51118b80c1a5fc584da175"
  }
}
```

The digest represents the exact artifact bytes. Changing one byte changes the digest.

### Step 7 — Attestation Generator

The attestation records what one builder observed:

- schema version, release ID and builder ID;
- public key ID;
- repository URL and exact commit;
- configuration ID, actual Docker image ID and source timestamp;
- successful status;
- artifact path, algorithm, digest and size.

An attestation is evidence, not a verdict. Failed builders never receive a fake successful attestation.

### Step 8 — Attestation Signer

The signer serializes the attestation using the project-defined `quorum-json-v1` format: recursively sorted JSON object keys, no insignificant spaces, UTF-8 and no NaN/Infinity. It signs those exact bytes with Ed25519 and stores a Base64 signature in an envelope.

Each builder uses a different key and `public_key_id`:

```text
builder-a -> builder-a-key-v1
builder-b -> builder-b-key-v1
builder-c -> builder-c-key-v1
```

The development private PEM files stay local and ignored. The Quorum Engineer receives only public PEM files through a trusted out-of-band channel and owns the mapping between builder identity and public key.

### Step 9 — Multi-Builder Orchestration and Result Collection

`run_all_builders(payload, output_root, key_directory)` validates the request once, creates one 32-character lowercase hexadecimal job ID and executes A, B and C sequentially in canonical order. All three receive the same request and shared job ID, but use separate directories and keys.

One builder failure does not stop later builders. Expected failures retain their precise status. An unexpected Python exception is converted to `INTERNAL_ERROR` / `UNHANDLED_BUILDER_ERROR`, without exposing exception details or manufacturing evidence.

The final status is `COMPLETED` once all builders have a terminal result. `COMPLETED` means orchestration finished; it does not mean the release passed quorum.

## 6. Output layout

One orchestration produces:

```text
builders/output/<release-id>/
├── builder-a/<job-id>/
│   ├── source/
│   ├── dist/<wheel>
│   ├── fetch.log
│   ├── build.log
│   ├── artifact-manifest.json
│   └── signed-attestation.json
├── builder-b/<job-id>/...
├── builder-c/<job-id>/...
└── orchestrations/<job-id>/combined-result.json
```

Each item in `builder_results` contains the builder identity and terminal status. Successful items contain the artifact evidence, key ID and signed attestation. Failed items contain an `error_code` and leave artifact/signature fields null.

See `shared/specs/builder-results.md`, `shared/specs/builder-attestation.md` and `shared/specs/artifact-comparison.md` for the machine-to-machine rules.

## 7. Set up and run it yourself

Run all commands from the repository root in PowerShell. Do not copy another developer's private keys.

### 7.1 Create the environment

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start Docker Desktop, then build the approved local image:

```powershell
docker build -f builders/runner/Dockerfile -t quorum-python-package-v1:local builders/runner
```

### 7.2 Generate three local development keypairs

```powershell
.venv\Scripts\python.exe -m builders.manager.cli keygen --builder-id builder-a
.venv\Scripts\python.exe -m builders.manager.cli keygen --builder-id builder-b
.venv\Scripts\python.exe -m builders.manager.cli keygen --builder-id builder-c
```

Key generation refuses to overwrite an existing key. Keep `*.pem` private keys local. Share only `*.pub.pem` with the Quorum Engineer through a trusted channel.

### 7.3 Run quality checks

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.venv\Scripts\python.exe -m ruff check --no-cache builders
.venv\Scripts\python.exe -m ruff format --check --no-cache builders
```

### 7.4 Run all three builders

```powershell
.venv\Scripts\python.exe -m builders.manager.cli build-all `
  --request builders/runner/demo-request.json `
  --key-dir builders/keys `
  --output-root builders/output
```

Exit code `0` means every builder succeeded. Exit code `1` means orchestration completed but one or more builders failed. Exit code `2` means the command/request itself was invalid. Always inspect `summary`, every builder result and the signed evidence; do not treat the process exit code as a quorum verdict.

To confirm no build containers remain:

```powershell
docker ps -a --filter "ancestor=quorum-python-package-v1:local"
```

## 8. Verified integration evidence

On 2026-10-04, the complete command was run against the public PyPA sample project at commit `621e4974ca25ce531773def586ba3ed8e736b3fc`.

| Check | Observed result |
| --- | --- |
| Shared job ID | `4c2bee3cea0c4cbc85f2912f65c033fa` |
| Orchestration status | `COMPLETED` |
| Summary | 3 total, 3 successful, 0 failed |
| Artifact | `sampleproject-4.0.0-py3-none-any.whl` |
| Artifact size | 4,660 bytes for A, B and C |
| Builder A SHA-256 | `4209e70ec0bc11900d4bf453f156d14789a517febb51118b80c1a5fc584da175` |
| Builder B SHA-256 | same digest |
| Builder C SHA-256 | same digest |
| Signature checks | A `true`, B `true`, C `true` with their matching public keys |
| Remaining build containers | none |
| Automated tests | 53 passed |
| Ruff lint | passed |
| Ruff formatting | passed |

This proves the prototype can produce matching, individually signed evidence in one real local run. It does not prove production-grade independence or make a quorum decision. The generated `builders/output/` directory was removed after recording these results so every teammate must reproduce the run themselves.

## 9. What the Quorum Engineer must do

The Quorum component should:

1. Send the exact five-field request defined in `shared/specs/builder-request.md`.
2. Maintain a trusted registry mapping `builder-a`, `builder-b` and `builder-c` to their expected public keys and key IDs.
3. For each successful result, verify the Ed25519 signature over the documented canonical bytes.
4. Confirm the signed release ID, builder ID, repository URL, commit SHA and build configuration match the original request.
5. Confirm the public key ID belongs to that builder; never trust a public key supplied inside a result.
6. Confirm the artifact algorithm is `sha256` and sanity-check its path and size.
7. Compare only valid, successful evidence and apply the agreed quorum rule, such as two matching digests out of three.
8. Treat failed, missing, invalidly signed or mismatched evidence according to explicit policy.
9. Produce the final `VERIFIED`, `REJECTED` or other business decision. The Builder never produces it.

For integration, call `run_all_builders()` directly in the first version or wrap it in a queue/worker later. Do not add arbitrary shell commands to the request contract.

## 10. What the Blockchain Engineer must do

Agree with the Quorum Engineer on the final chain payload. A sensible minimal payload contains the release ID, source commit, artifact SHA-256, quorum decision and a digest/reference for the verification evidence. The Blockchain component should record the already-decided outcome; it should not rerun builds or infer trust from an unsigned builder hash.

Before integration, decide:

- whether the full evidence stays off-chain with only its digest on-chain;
- which exact JSON canonicalization is used before hashing a combined record;
- how builder keys and rotations are represented;
- how duplicate release submissions and chain failures are handled.

## 11. Tests that protect Step 9

`builders/tests/test_orchestrator.py` proves:

- all three builders receive the same request and shared job ID;
- canonical A/B/C order and separate key paths are maintained;
- all-success summary and combined JSON are correct;
- one normal failure does not prevent Builder C from running;
- an unexpected exception is safely converted to a terminal failure;
- all-three-failure still produces a completed collection;
- failures contain no fake artifact, key or attestation;
- differing hashes are preserved without adding a quorum or verification decision;
- invalid requests and unsafe job IDs are rejected before any builder runs.

The earlier tests cover request validation, safe fetching, Docker limits and cleanup behavior, artifact rules, streamed hashing, attestation creation, signing, signature verification and the single-builder pipeline.

## 12. Known limitations and production work

This is a strong hackathon prototype, not a production build farm:

- All three identities currently share one machine, Docker daemon and image.
- Sequential execution is easier to debug but slower than independent workers.
- Development keys are unencrypted local files; production keys should use a secret manager, KMS or HSM and support rotation.
- The public-key trust registry and authenticated transport are not implemented here.
- There is no API, queue, retry scheduler, database, authentication or authorization layer yet.
- GitHub is the only accepted host. Fetch network policy relies on validation plus Git configuration; production should also enforce infrastructure-level egress rules.
- The build image is pinned, but the image itself is not signed/attested and Python dependency files are version-pinned without package hashes.
- Disk quota, global concurrency, log redaction, observability and retention policies need production design.
- Python packages that require undeclared build dependencies will fail because runtime networking is intentionally disabled.
- V1 accepts exactly one wheel. Supporting multiple artifacts requires a versioned manifest rule before implementation.

## 13. Commit history for the Builder work

The feature branch contains nine focused commits over `master` after the final documentation commit:

1. `feat(builder): validate five-field build requests`
2. `feat(builder): fetch pinned commits and isolate builds`
3. `feat(builder): hash approved wheel artifacts`
4. `feat(builder): sign single-build attestations`
5. `feat(builder): formalize artifact collection and hashing`
6. `build(builder): pin reproducible toolchain image`
7. `feat(builder): orchestrate three-builder executions`
8. `test(builder): cover multi-builder result collection`
9. `docs(builder): add complete engineer handoff runbook`

The work is intentionally split so reviewers can inspect validation, isolation, evidence, reproducibility, orchestration, tests and documentation separately.

## 14. Troubleshooting

- **Docker engine is unavailable:** start Docker Desktop and wait until `docker info` succeeds.
- **Build image is missing:** rerun the `docker build` command in section 7.1.
- **Development key already exists:** reuse it; key generation refuses destructive replacement. Delete/rotate it only as an explicit security decision.
- **`SIGNING_FAILED` / `KEY_ERROR`:** check that the expected builder's private key exists under `builders/keys/`.
- **`FETCH_FAILED` / `GIT_ERROR`:** confirm the GitHub URL and full commit exist and the host can reach GitHub.
- **`BUILD_FAILED`:** inspect that builder's `build.log`; the repository may need dependencies not present in the approved offline image.
- **`ARTIFACT_ERROR`:** the build produced zero, multiple, empty, oversized or unsafe wheel matches.
- **Different hashes:** keep all signed results unchanged and pass them to the Quorum Engine. A difference is evidence, not proof that a builder is malicious.

The key design rule is simple: **the Builder reports signed facts; the Quorum Engine decides what those facts mean.**
