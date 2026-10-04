import re
from urllib.parse import urlparse
from app.core.exceptions import InvalidRepositoryError, InvalidCommitError


class RepositoryService:
    """
    Validates Git repository URLs and pinned commit SHAs.
    Ensures requested commit is explicitly pinned and never silently replaced with HEAD.
    """

    # Regex for standard 40-character hex Git commit SHA (or 7-40 char short/full SHA)
    GIT_COMMIT_HEX_REGEX = re.compile(r"^[0-9a-fA-F]{7,40}$")

    @classmethod
    def validate_repository(cls, repository_url: str) -> bool:
        """
        Validates Git repository URL structure.
        Supports https://, http://, and git@ URLs.
        """
        if not repository_url or not isinstance(repository_url, str):
            raise InvalidRepositoryError("Repository URL must be a non-empty string.")

        url_str = repository_url.strip()

        # Handle SSH style git@github.com:user/repo.git
        if url_str.startswith("git@"):
            if ":" not in url_str:
                raise InvalidRepositoryError(f"Invalid SSH repository URL format: '{repository_url}'")
            return True

        # Handle HTTP/HTTPS URLs
        try:
            parsed = urlparse(url_str)
            if parsed.scheme not in ("http", "https"):
                raise InvalidRepositoryError(f"Invalid repository scheme '{parsed.scheme}'. Must be http or https.")
            if not parsed.netloc:
                raise InvalidRepositoryError(f"Invalid repository domain: '{repository_url}'")
            return True
        except InvalidRepositoryError:
            raise
        except Exception as e:
            raise InvalidRepositoryError(f"Malformed repository URL '{repository_url}': {str(e)}")

    @classmethod
    def validate_commit(cls, repository_url: str, commit_sha: str) -> str:
        """
        Validates commit SHA string format and returns normalized commit SHA.
        Ensures commit is explicitly provided and pinned.
        """
        if not commit_sha or not isinstance(commit_sha, str):
            raise InvalidCommitError("Commit SHA must be a non-empty string.")

        commit_clean = commit_sha.strip()

        # Disallow pseudo-refs like "HEAD", "main", "master", "latest" for pinned release verification
        if commit_clean.upper() in ("HEAD", "MAIN", "MASTER", "DEVELOP", "LATEST"):
            raise InvalidCommitError(
                f"Commit must be a pinned git commit hash (e.g. 40 hex chars). '{commit_sha}' branch ref is not pinned."
            )

        if not cls.GIT_COMMIT_HEX_REGEX.match(commit_clean):
            raise InvalidCommitError(
                f"Commit '{commit_sha}' is not a valid hex Git commit hash."
            )

        return commit_clean.lower()
