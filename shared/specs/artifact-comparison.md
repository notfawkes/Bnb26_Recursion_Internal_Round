# Artifact selection and hash comparison (v1)

This contract covers Builder Steps 5 and 6. It answers one exact question: **which output is compared, and how?**

## V1 decision

For `python-package-v1`, each builder must produce exactly one non-empty Python wheel matching `dist/*.whl`. The file must be a regular file inside that builder's job directory, may not be a symbolic link, and may not exceed 100 MiB. Zero matches, two or more matches, an empty file or an unsafe file produces `ARTIFACT_ERROR`; the builder must not choose one arbitrarily.

The selected wheel is hashed with SHA-256 by reading its bytes in 1 MiB chunks. The filename is recorded for evidence but is not itself hashed. Builders use the same selection rule and algorithm. The Builder Manager reports evidence only; the Quorum Engine compares the `hash.digest` strings and decides what agreement means.

The Builder Manager writes `artifact-manifest.json` with this structure:

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

Two successful builders agree in V1 when they built the same requested repository/commit/config and their `hash.algorithm` is `sha256` and `hash.digest` values are identical. A different digest is reported as disagreement, not automatically labeled malicious. Artifact paths and sizes remain evidence and should also be sanity-checked by the Quorum Engineer, but the byte digest is the comparison value.

V1 deliberately supports one wheel rather than a multi-file manifest. If the demo later requires both a wheel and source archive, define a V2 contract before changing the collector. Do not silently add files or switch to archive hashing because that would make builders compare different byte sets.
