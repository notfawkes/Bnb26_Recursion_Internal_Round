# Builder Manager input contract (v1)

The Quorum backend sends one JSON object with **exactly five fields**. Copy the shape in [builder-request.example.json](builder-request.example.json) for mock data. The example repository and commit are placeholders, not a runnable build target.

| Field | Required format | Meaning |
| --- | --- | --- |
| `release_id` | Canonical lowercase UUID string | Correlates the build with a release. |
| `repository_url` | `https://github.com/<owner>/<repo>` | Source repository; no credentials, ports, query, fragment or alternate host. |
| `commit_sha` | Full 40-character lowercase hexadecimal Git commit ID | Exact source revision to build. |
| `build_config_id` | Currently `python-package-v1` | Selects a builder-approved configuration. |
| `builders` | Array containing `builder-a`, `builder-b`, `builder-c` exactly once each | Builder identities to run. |

`artifact_path`, build commands and resource limits are **not** request fields. The Builder Manager resolves artifact selection and positive timeout/CPU/memory limits from its own approved configuration. Any missing, extra or invalid request field is rejected before fetching source or executing code.

This specifies the data shape only. The team still needs to agree whether the backend passes it via a Python call or HTTP. URL validation alone does not sandbox untrusted source; the later fetch/build stage must enforce network and redirect restrictions.
