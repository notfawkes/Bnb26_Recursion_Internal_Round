# Single-builder demo (Steps 2–4)

Run these commands from the repository root with Docker Desktop running:

```powershell
docker build -f builders/runner/Dockerfile -t quorum-python-package-v1:local builders/runner
.venv/Scripts/python.exe -m builders.manager.cli keygen --builder-id builder-a
.venv/Scripts/python.exe -m builders.manager.cli build-one --request builders/runner/demo-request.json --builder-id builder-a --private-key builders/keys/builder-a-key-v1.pem
```

The demo request pins the public [PyPA sampleproject](https://github.com/pypa/sampleproject) at one full commit. The manager fetches that commit and checks `HEAD`, passes its commit timestamp as `SOURCE_DATE_EPOCH`, builds one wheel in Docker, saves the wheel and logs under ignored `builders/output/`, hashes the exact wheel bytes, and writes a signed attestation. The signing key stays under ignored `builders/keys/` and is **not** mounted into the container. Re-running `keygen` refuses to overwrite an existing key.

One completed job has this shape:

```text
builders/output/<release-id>/<builder-id>/<job-id>/
├── source/                    exact pinned Git checkout
├── dist/                      build output only
│   └── sampleproject-4.0.0-py3-none-any.whl
├── fetch.log                  Git fetch/checkout log
├── build.log                  container build log
├── artifact-manifest.json     selected artifact plus SHA-256
└── signed-attestation.json    complete signed build evidence
```

For V1, the Artifact Collector accepts exactly one non-empty regular wheel matching `dist/*.whl`. The Hash Generator reads that file in chunks and produces SHA-256. See `shared/specs/artifact-comparison.md` for the exact contract the Quorum Engineer should implement. In the real demo, Builder A and Builder B each produced a 4,660-byte wheel with digest `4209e70ec0bc11900d4bf453f156d14789a517febb51118b80c1a5fc584da175`.

The Docker image must be built before running the request. Its Python base image is pinned by digest and all installed Python build tools are version-pinned. At runtime the source repository has no network access, only the source checkout (read-only) and artifact output folder (read-write) are mounted, and CPU, memory, process count and time are limited. The configuration and image are builder-owned; the request cannot supply a shell command or loosen limits.

This is a hackathon prototype, not a production sandbox or three independent trust authorities. The image itself has not been independently attested, package hashes are not locked, and Docker containers on one host share that host's trust boundary. Do not run untrusted repositories on a sensitive machine. Backend transport, a trusted public-key registry and quorum decisions are future integration work.
