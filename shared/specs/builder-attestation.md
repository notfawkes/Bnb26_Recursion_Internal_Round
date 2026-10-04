# Single-builder signed attestation (v1)

After a successful build, the Builder Manager returns an envelope with `attestation`, `public_key_id`, `signature_algorithm`, `canonicalization` and `signature`. Failed builds return a failure status and **no** signed success attestation. The Builder Manager never declares a release verified.

The signed `attestation` contains `schema_version`, `release_id`, `builder_id`, `public_key_id`, `source` (`repository_url`, full `commit_sha`), `build` (`config_id`, Docker `image_id`, `source_date_epoch`, `status`), and `artifact` (`path`, `algorithm`, `digest`, `size_bytes`). The artifact digest is SHA-256 of the exact wheel file bytes.

`signature_algorithm` is `ed25519`. `signature` is standard Base64 of the 64-byte Ed25519 signature. `public_key_id` is `<builder-id>-key-v1`; the backend must resolve it from a **trusted registry** and confirm that the key is assigned to the signed `builder_id`. Do not trust a public key supplied by the build result itself.

`canonicalization` is `quorum-json-v1`: serialize the `attestation` object with recursively sorted keys, no spaces (`separators=(",", ":")`), UTF-8, unescaped non-ASCII, and no NaN/Infinity, then sign those exact bytes. V1 attestation values are strings and integers, so the format can be reproduced across implementations. This is an explicit project format, **not** a claim of full RFC 8785 conformance. The Quorum Engineer should confirm this byte format before backend integration.

The development private key is stored only under ignored `builders/keys/` and never mounted into the Docker build container. The public PEM may be shared out of band for local verification. Local development keys are unencrypted and must not be reused in production.
