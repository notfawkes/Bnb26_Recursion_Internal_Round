"""Safely inspect committed release artifacts and detect approved build profiles."""

import hashlib
import os
import re
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Iterator

from app.schemas.artifact import (
    ArtifactDetectionResponse,
    ArtifactHashResponse,
    DetectedArtifact,
)


GITHUB_REPOSITORY = re.compile(
    r"https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)
FULL_COMMIT = re.compile(r"[0-9a-fA-F]{40}")
ARTIFACT_EXTENSIONS = (".whl", ".jar", ".tgz")
IGNORED_PARTS = frozenset({".git", ".venv", "node_modules", "__pycache__"})


class ProjectInspectionError(ValueError):
    """Repository inspection could not produce safe, deterministic evidence."""


class ProjectInspectionService:
    PROFILE_MARKERS = {
        "python-package-v1": ("Python", ("pyproject.toml", "setup.py", "setup.cfg")),
        "node-package-v1": ("Node.js", ("package.json",)),
        "node-disputed-demo-v1": (
            "Node.js (Disputed Demo)",
            ("package.json", "quorum-disputed-demo.json"),
        ),
        "java-maven-v1": ("Java", ("pom.xml",)),
    }

    PROFILE_EXTENSIONS = {
        "python-package-v1": ".whl",
        "node-package-v1": ".tgz",
        "node-disputed-demo-v1": ".tgz",
        "java-maven-v1": ".jar",
    }

    ALL_MARKERS_REQUIRED = frozenset({"node-disputed-demo-v1"})

    @classmethod
    def _validate_source(cls, repository_url: str, commit_sha: str) -> tuple[str, str]:
        repository = repository_url.strip()
        commit = commit_sha.strip().lower()
        if GITHUB_REPOSITORY.fullmatch(repository) is None:
            raise ProjectInspectionError("Only public HTTPS GitHub repository URLs are supported.")
        if FULL_COMMIT.fullmatch(commit) is None:
            raise ProjectInspectionError("A full 40-character pinned commit SHA is required.")
        return repository, commit

    @classmethod
    @contextmanager
    def _checkout(cls, repository_url: str, commit_sha: str) -> Iterator[Path]:
        repository, commit = cls._validate_source(repository_url, commit_sha)
        with tempfile.TemporaryDirectory(prefix="quorum-inspect-") as temp_dir:
            destination = Path(temp_dir) / "source"
            destination.mkdir()
            environment = os.environ.copy()
            environment.update(
                {
                    "GIT_TERMINAL_PROMPT": "0",
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_LFS_SKIP_SMUDGE": "1",
                }
            )
            commands = (
                ["git", "init", "--quiet", str(destination)],
                ["git", "-C", str(destination), "remote", "add", "origin", repository],
                [
                    "git",
                    "-C",
                    str(destination),
                    "-c",
                    "http.followRedirects=false",
                    "-c",
                    "protocol.file.allow=never",
                    "fetch",
                    "--quiet",
                    "--depth=1",
                    "origin",
                    commit,
                ],
                ["git", "-C", str(destination), "checkout", "--quiet", "--detach", "FETCH_HEAD"],
            )
            try:
                for command in commands:
                    subprocess.run(
                        command,
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=60,
                        env=environment,
                    )
            except FileNotFoundError as exc:
                raise ProjectInspectionError("Git is not installed on the backend host.") from exc
            except subprocess.TimeoutExpired as exc:
                raise ProjectInspectionError("Repository inspection timed out.") from exc
            except subprocess.CalledProcessError as exc:
                detail = (exc.stderr or exc.stdout or "Git fetch failed").strip()
                raise ProjectInspectionError(f"Could not fetch the pinned commit: {detail[:400]}") from exc
            yield destination

    @classmethod
    def detect_project(cls, source: Path) -> tuple[str, str, list[str]]:
        matches: list[tuple[int, str, str, list[str]]] = []
        for profile, (project_type, markers) in cls.PROFILE_MARKERS.items():
            evidence = [marker for marker in markers if (source / marker).is_file()]
            if profile in cls.ALL_MARKERS_REQUIRED and len(evidence) != len(markers):
                continue
            if evidence:
                matches.append((len(evidence), profile, project_type, evidence))
        if not matches:
            raise ProjectInspectionError(
                "No supported project marker found (pyproject.toml, package.json, or pom.xml)."
            )
        matches.sort(key=lambda item: (-item[0], item[1]))
        best = matches[0]
        if len(matches) > 1 and matches[1][0] == best[0]:
            raise ProjectInspectionError(
                "Multiple project types were detected with equal confidence; choose a single-project repository."
            )
        return best[2], best[1], best[3]

    @classmethod
    def _artifact_candidates(cls, source: Path) -> list[Path]:
        candidates = []
        for path in source.rglob("*"):
            if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
                continue
            if path.name.lower().endswith(ARTIFACT_EXTENSIONS):
                candidates.append(path)
        return candidates

    @classmethod
    def _artifact_sort_key(cls, source: Path, path: Path, profile: str) -> tuple[int, int, str]:
        relative = path.relative_to(source).as_posix()
        preferred_extension = cls.PROFILE_EXTENSIONS[profile]
        preferred_directories = ("dist/", "target/", "build/libs/", "build/")
        extension_rank = 0 if path.name.lower().endswith(preferred_extension) else 1
        directory_rank = next(
            (index for index, prefix in enumerate(preferred_directories) if relative.startswith(prefix)),
            len(preferred_directories),
        )
        return extension_rank, directory_rank, relative

    @classmethod
    def _describe_artifact(cls, source: Path, artifact: Path) -> DetectedArtifact:
        return DetectedArtifact(
            path=artifact.relative_to(source).as_posix(),
            name=artifact.name,
            extension=".tar.gz" if artifact.name.lower().endswith(".tar.gz") else artifact.suffix.lower(),
            size_bytes=artifact.stat().st_size,
        )

    @classmethod
    def inspect_directory(
        cls, source: Path, repository_url: str, commit_sha: str
    ) -> ArtifactDetectionResponse:
        project_type, profile, evidence = cls.detect_project(source)
        candidates = cls._artifact_candidates(source)
        if not candidates:
            raise ProjectInspectionError(
                "No committed .whl, .jar, or .tgz release artifact was found in the repository."
            )
        candidates.sort(key=lambda path: cls._artifact_sort_key(source, path, profile))
        selected = candidates[0]
        return ArtifactDetectionResponse(
            repository_url=repository_url,
            commit_sha=commit_sha.lower(),
            project_type=project_type,
            build_config_id=profile,
            evidence=evidence,
            artifact=cls._describe_artifact(source, selected),
            candidates_found=len(candidates),
        )

    @classmethod
    def detect(cls, repository_url: str, commit_sha: str) -> ArtifactDetectionResponse:
        repository, commit = cls._validate_source(repository_url, commit_sha)
        with cls._checkout(repository, commit) as source:
            return cls.inspect_directory(source, repository, commit)

    @classmethod
    def hash_artifact(
        cls, repository_url: str, commit_sha: str, artifact_path: str
    ) -> ArtifactHashResponse:
        repository, commit = cls._validate_source(repository_url, commit_sha)
        relative = PurePosixPath(artifact_path)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not relative.parts
            or not relative.name.lower().endswith(ARTIFACT_EXTENSIONS)
        ):
            raise ProjectInspectionError("The detected artifact path is not safe or supported.")
        with cls._checkout(repository, commit) as source:
            artifact = source.joinpath(*relative.parts).resolve()
            if source.resolve() not in artifact.parents or not artifact.is_file():
                raise ProjectInspectionError("The detected artifact no longer exists at the pinned commit.")
            digest = hashlib.sha256()
            bytes_hashed = 0
            with artifact.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                    bytes_hashed += len(chunk)
            return ArtifactHashResponse(
                repository_url=repository,
                commit_sha=commit,
                artifact=cls._describe_artifact(source, artifact),
                digest=digest.hexdigest(),
                bytes_hashed=bytes_hashed,
            )
