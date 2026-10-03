import pytest
from app.services.repository_service import RepositoryService
from app.core.exceptions import InvalidRepositoryError, InvalidCommitError


def test_valid_repository_urls():
    assert RepositoryService.validate_repository("https://github.com/example/project") is True
    assert RepositoryService.validate_repository("http://gitlab.com/owner/repo.git") is True
    assert RepositoryService.validate_repository("git@github.com:owner/repo.git") is True


def test_invalid_repository_urls():
    with pytest.raises(InvalidRepositoryError):
        RepositoryService.validate_repository("ftp://github.com/example/project")

    with pytest.raises(InvalidRepositoryError):
        RepositoryService.validate_repository("")


def test_valid_pinned_commit_sha():
    commit = "abc1234567890abcdef1234567890abcdef12345"
    assert RepositoryService.validate_commit("https://github.com/example/project", commit) == commit.lower()


def test_invalid_pseudo_branch_refs_rejected():
    with pytest.raises(InvalidCommitError):
        RepositoryService.validate_commit("https://github.com/example/project", "HEAD")

    with pytest.raises(InvalidCommitError):
        RepositoryService.validate_commit("https://github.com/example/project", "main")

    with pytest.raises(InvalidCommitError):
        RepositoryService.validate_commit("https://github.com/example/project", "latest")


def test_non_hex_commit_sha_rejected():
    with pytest.raises(InvalidCommitError):
        RepositoryService.validate_commit("https://github.com/example/project", "not_a_hex_commit!")
