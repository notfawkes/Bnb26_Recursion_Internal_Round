from pathlib import Path
from unittest.mock import Mock, patch
from uuid import UUID

import pytest

from builders.manager.config import APPROVED_BUILD_CONFIGS
from builders.manager.repository import RepositoryFetchError, fetch_repository
from builders.manager.request_validator import ValidatedBuilderRequest


@pytest.fixture
def builder_request() -> ValidatedBuilderRequest:
    return ValidatedBuilderRequest(
        release_id=UUID("d4f2496e-5c5a-4c82-9fd5-f3c3012a524e"),
        repository_url="https://github.com/example/safecalc",
        commit_sha="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        build_config_id="python-package-v1",
        builders=("builder-a", "builder-b", "builder-c"),
        build_config=APPROVED_BUILD_CONFIGS["python-package-v1"],
    )


def test_fetch_pins_and_verifies_exact_commit(
    builder_request: ValidatedBuilderRequest, tmp_path: Path
) -> None:
    outputs = ["", "", "", "", builder_request.commit_sha, "1700000000", ""]
    with patch("builders.manager.repository.subprocess.run") as run:
        run.side_effect = [
            Mock(returncode=0, stdout=value, stderr="") for value in outputs
        ]
        result = fetch_repository(builder_request, tmp_path / "source")

    assert result.commit_sha == builder_request.commit_sha
    assert result.source_date_epoch == 1700000000
    assert result.directory.is_dir()
    fetch_command = run.call_args_list[2].args[0]
    assert "--depth=1" in fetch_command
    assert builder_request.commit_sha in fetch_command
    assert "http.followRedirects=false" in fetch_command
    assert run.call_args_list[3].args[0][-2:] == ["--detach", "FETCH_HEAD"]


def test_mismatched_checked_out_commit_fails(
    builder_request: ValidatedBuilderRequest, tmp_path: Path
) -> None:
    outputs = ["", "", "", "", "0" * 40]
    with patch("builders.manager.repository.subprocess.run") as run:
        run.side_effect = [
            Mock(returncode=0, stdout=value, stderr="") for value in outputs
        ]
        with pytest.raises(RepositoryFetchError, match="does not match"):
            fetch_repository(builder_request, tmp_path / "source")


def test_git_failure_is_reported(
    builder_request: ValidatedBuilderRequest, tmp_path: Path
) -> None:
    with patch("builders.manager.repository.subprocess.run") as run:
        run.return_value = Mock(returncode=1, stdout="", stderr="fatal: failed")
        with pytest.raises(RepositoryFetchError, match="Git operation failed"):
            fetch_repository(builder_request, tmp_path / "source")


def test_existing_source_directory_is_not_overwritten(
    builder_request: ValidatedBuilderRequest, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(RepositoryFetchError, match="already exists"):
        fetch_repository(builder_request, source)
