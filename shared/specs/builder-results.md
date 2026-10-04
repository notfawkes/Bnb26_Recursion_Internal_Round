# Multi-builder result contract (v1)

The Builder Manager accepts the existing five-field request and executes its three builder identities sequentially. `status: "COMPLETED"` means all requested builders reached terminal outcomes; it is **not** a quorum verdict and never means `VERIFIED` or `REJECTED`.

```json
{
  "release_id": "d4f2496e-5c5a-4c82-9fd5-f3c3012a524e",
  "job_id": "0123456789abcdef0123456789abcdef",
  "status": "COMPLETED",
  "request": {
    "release_id": "d4f2496e-5c5a-4c82-9fd5-f3c3012a524e",
    "repository_url": "https://github.com/pypa/sampleproject",
    "commit_sha": "621e4974ca25ce531773def586ba3ed8e736b3fc",
    "build_config_id": "python-package-v1",
    "builders": ["builder-a", "builder-b", "builder-c"]
  },
  "summary": {
    "total_builders": 3,
    "successful_builds": 3,
    "failed_builds": 0
  },
  "builder_results": [],
  "result_path": ".../combined-result.json"
}
```

`builder_results` preserves the existing `BuilderOutcome` fields: `release_id`, `builder_id`, terminal `status`, `job_directory`, optional `artifact_hash`, `artifact_path`, `artifact_manifest`, `public_key_id`, complete `signed_attestation`, and optional `error_code`. A failed result has no fake successful artifact evidence or attestation.

The Quorum Engineer must independently verify every signed attestation with a trusted key, confirm request/source/build fields, compare valid artifact digests and apply quorum policy. The Builder Manager deliberately does none of those operations.
