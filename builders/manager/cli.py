"""Local demonstration commands for one builder (not an HTTP service)."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from builders.manager.pipeline import run_single_builder
from builders.manager.request_validator import RequestValidationError
from builders.manager.signing import generate_development_keypair


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Quorum single-builder prototype")
    commands = parser.add_subparsers(dest="command", required=True)

    keygen = commands.add_parser("keygen", help="create a local development keypair")
    keygen.add_argument("--builder-id", required=True)
    keygen.add_argument("--key-dir", type=Path, default=Path("builders/keys"))

    build_one = commands.add_parser("build-one", help="run one pinned build")
    build_one.add_argument("--request", required=True, type=Path)
    build_one.add_argument("--builder-id", required=True)
    build_one.add_argument("--private-key", required=True, type=Path)
    build_one.add_argument("--output-root", type=Path, default=Path("builders/output"))

    args = parser.parse_args(argv)
    try:
        if args.command == "keygen":
            keys = generate_development_keypair(args.builder_id, args.key_dir)
            print(f"Private key (keep local): {keys.private_path}")
            print(f"Public key (share with verifier): {keys.public_path}")
            print(f"Public key ID: {keys.public_key_id}")
            return 0

        payload = json.loads(args.request.read_text(encoding="utf-8"))
        outcome = run_single_builder(
            payload, args.builder_id, args.output_root, args.private_key
        )
        print(json.dumps(asdict(outcome), indent=2, ensure_ascii=False))
        return 0 if outcome.status == "SUCCESS" else 1
    except (OSError, ValueError, RequestValidationError) as exc:
        print(f"Builder request failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
