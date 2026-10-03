# Single-builder demo (Steps 2–4)

Run these commands from the repository root with Docker Desktop running:

```powershell
docker build -f builders/runner/Dockerfile -t quorum-python-package-v1:local builders/runner
.venv/Scripts/python.exe -m builders.manager.cli keygen --builder-id builder-a
.venv/Scripts/python.exe -m builders.manager.cli build-one --request builders/runner/demo-request.json --builder-id builder-a --private-key builders/keys/builder-a-key-v1.pem
```

The demo request pins the public [PyPA sampleproject](https://github.com/pypa/sampleproject) at one full commit. The manager fetches that commit and checks `HEAD`, passes its commit timestamp as `SOURCE_DATE_EPOCH`, builds one wheel in Docker, saves the wheel and logs under ignored `builders/output/`, hashes the exact wheel bytes, and writes a signed attestation. The signing key stays under ignored `builders/keys/` and is **not** mounted into the container. Re-running `keygen` refuses to overwrite an existing key.

The Docker image must be built before running the request. At build time it downloads pinned Python build tools. At runtime the source repository has no network access, only the source checkout (read-only) and artifact output folder (read-write) are mounted, and CPU, memory, process count and time are limited. The configuration and image are builder-owned; the request cannot supply a shell command or loosen limits.

This is a hackathon prototype, not a production sandbox or three independent trust authorities. The base-image tag is not digest-pinned yet, the image itself has not been independently attested, and Docker containers on one host share that host's trust boundary. Do not run untrusted repositories on a sensitive machine. Backend transport, a trusted public-key registry and quorum decisions are future integration work.
