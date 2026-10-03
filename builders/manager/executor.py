"""Run the approved build command inside a constrained Docker container."""

import time
from dataclasses import dataclass
from pathlib import Path

import docker
from docker.errors import DockerException, ImageNotFound

from builders.manager.config import BuildConfiguration


class BuildExecutionError(RuntimeError):
    """The build runtime could not start or complete normally."""


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    exit_code: int | None
    log: str
    image_id: str


def _limited_logs(container: object) -> str:
    raw = container.logs(stdout=True, stderr=True, tail=1000)
    return raw[-1_000_000:].decode("utf-8", "replace")


def execute_build(
    source_dir: Path,
    output_dir: Path,
    config: BuildConfiguration,
    *,
    source_date_epoch: int,
    client: docker.DockerClient | None = None,
) -> ExecutionResult:
    """Build one wheel; the source has no network or signing-key access."""
    output_dir.mkdir(parents=True, exist_ok=False)
    own_client = client is None
    if client is None:
        try:
            client = docker.from_env()
            client.ping()
        except DockerException as exc:
            raise BuildExecutionError("Docker engine is unavailable") from exc

    container = None
    try:
        try:
            image = client.images.get(config.image)
        except ImageNotFound as exc:
            raise BuildExecutionError(
                f"build image {config.image} is missing; build builders/runner/Dockerfile"
            ) from exc

        limits = config.limits
        container = client.containers.run(
            config.image,
            command=list(config.command),
            detach=True,
            network_mode="none",
            read_only=True,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            user="65532:65532",
            mem_limit=f"{limits.memory_mb}m",
            memswap_limit=f"{limits.memory_mb}m",
            nano_cpus=limits.cpu_count * 1_000_000_000,
            pids_limit=64,
            tmpfs={"/tmp": "rw,nosuid,nodev,size=256m"},
            environment={
                "HOME": "/tmp",
                "PIP_NO_INDEX": "1",
                "PYTHONHASHSEED": "0",
                "SOURCE_DATE_EPOCH": str(source_date_epoch),
                "TZ": "UTC",
            },
            use_config_proxy=False,
            volumes={
                str(source_dir.resolve()): {"bind": "/src", "mode": "ro"},
                str(output_dir.resolve()): {"bind": "/out", "mode": "rw"},
            },
        )

        deadline = time.monotonic() + limits.timeout_seconds
        while time.monotonic() < deadline:
            container.reload()
            if container.status in {"exited", "dead"}:
                break
            time.sleep(0.2)
        else:
            container.kill()
            return ExecutionResult(
                status="BUILD_TIMEOUT",
                exit_code=None,
                log=_limited_logs(container),
                image_id=image.id,
            )

        exit_code = container.attrs["State"]["ExitCode"]
        return ExecutionResult(
            status="SUCCESS" if exit_code == 0 else "BUILD_FAILED",
            exit_code=exit_code,
            log=_limited_logs(container),
            image_id=image.id,
        )
    except DockerException as exc:
        raise BuildExecutionError("Docker build operation failed") from exc
    finally:
        if container is not None:
            container.remove(force=True)
        if own_client and client is not None:
            client.close()
