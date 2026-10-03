from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from builders.manager.config import APPROVED_BUILD_CONFIGS
from builders.manager.executor import execute_build


def test_docker_build_has_isolation_and_no_key_mount(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    container = Mock()
    container.status = "exited"
    container.attrs = {"State": {"ExitCode": 0}}
    container.logs.return_value = b"built successfully"
    client = Mock()
    client.images.get.return_value = SimpleNamespace(id="sha256:test-image")
    client.containers.run.return_value = container

    result = execute_build(
        source,
        tmp_path / "dist",
        APPROVED_BUILD_CONFIGS["python-package-v1"],
        source_date_epoch=1700000000,
        client=client,
    )

    assert result.status == "SUCCESS"
    assert result.image_id == "sha256:test-image"
    options = client.containers.run.call_args.kwargs
    assert options["network_mode"] == "none"
    assert options["read_only"] is True
    assert options["cap_drop"] == ["ALL"]
    assert options["mem_limit"] == "512m"
    assert options["environment"]["SOURCE_DATE_EPOCH"] == "1700000000"
    assert options["volumes"][str(source.resolve())]["mode"] == "ro"
    assert len(options["volumes"]) == 2
    container.remove.assert_called_once_with(force=True)


def test_failed_build_returns_failure(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    container = Mock()
    container.status = "exited"
    container.attrs = {"State": {"ExitCode": 2}}
    container.logs.return_value = b"build failed"
    client = Mock()
    client.images.get.return_value = SimpleNamespace(id="sha256:test-image")
    client.containers.run.return_value = container

    result = execute_build(
        source,
        tmp_path / "dist",
        APPROVED_BUILD_CONFIGS["python-package-v1"],
        source_date_epoch=1700000000,
        client=client,
    )

    assert result.status == "BUILD_FAILED"
    assert result.exit_code == 2
    assert "build failed" in result.log
