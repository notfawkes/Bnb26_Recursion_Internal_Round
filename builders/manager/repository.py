"""Fetch an approved repository at an exact commit without running its code."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from builders.manager.request_validator import ValidatedBuilderRequest


class RepositoryFetchError(RuntimeError):
    """A source checkout could not be fetched or verified."""


@dataclass(frozen=True)
class FetchedSource:
    directory: Path
    commit_sha: str
    source_date_epoch: int
    log: str


def fetch_repository(
    request: ValidatedBuilderRequest,
    destination: Path,
    *,
    timeout_seconds: int = 120,
) -> FetchedSource:
    """Fetch only the pinned commit into a new directory and verify HEAD."""
    if destination.exists():
        raise RepositoryFetchError("source destination already exists")
    destination.mkdir(parents=True)

    log_lines: list[str] = []

    def git(*args: str) -> str:
        command = ["git", "-C", str(destination), *args]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RepositoryFetchError("Git operation timed out") from exc
        log_lines.append(f"$ git {' '.join(args)}\n{result.stdout}{result.stderr}")
        if result.returncode != 0:
            raise RepositoryFetchError(f"Git operation failed: {args[0]}")
        return result.stdout.strip()

    git("init", "--quiet")
    git("remote", "add", "origin", request.repository_url)
    git(
        "-c",
        "http.followRedirects=false",
        "-c",
        "protocol.file.allow=never",
        "fetch",
        "--no-tags",
        "--depth=1",
        "origin",
        request.commit_sha,
    )
    git("checkout", "--quiet", "--detach", "FETCH_HEAD")
    actual_sha = git("rev-parse", "HEAD")
    if actual_sha != request.commit_sha:
        raise RepositoryFetchError("checked-out commit does not match request")
    source_date_epoch = int(git("show", "-s", "--format=%ct", "HEAD"))
    git("remote", "remove", "origin")
    return FetchedSource(
        destination, actual_sha, source_date_epoch, "\n".join(log_lines)
    )
