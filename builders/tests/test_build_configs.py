from builders.manager.config import APPROVED_BUILD_CONFIGS
from builders.manager.request_validator import validate_builder_request


def _payload(profile: str) -> dict[str, object]:
    return {
        "release_id": "d4f2496e-5c5a-4c82-9fd5-f3c3012a524e",
        "repository_url": "https://github.com/example/project",
        "commit_sha": "a" * 40,
        "build_config_id": profile,
        "builders": ["builder-a", "builder-b", "builder-c"],
    }


def test_python_node_and_java_profiles_are_approved() -> None:
    assert set(APPROVED_BUILD_CONFIGS) == {
        "python-package-v1",
        "node-package-v1",
        "node-disputed-demo-v1",
        "java-maven-v1",
    }

    for profile in APPROVED_BUILD_CONFIGS:
        validated = validate_builder_request(_payload(profile))
        assert validated.build_config_id == profile
        assert validated.build_config.command
        assert validated.build_config.artifact_glob.startswith("dist/")


def test_node_and_java_commands_are_fixed_and_offline() -> None:
    assert APPROVED_BUILD_CONFIGS["node-package-v1"].image == "quorum-node-package-v1:local"
    assert "npm pack" in APPROVED_BUILD_CONFIGS["node-package-v1"].command[-1]
    disputed_command = APPROVED_BUILD_CONFIGS["node-disputed-demo-v1"].command[-1]
    assert APPROVED_BUILD_CONFIGS["node-disputed-demo-v1"].image == "quorum-node-package-v1:local"
    assert "quorum-build-nonce.txt" in disputed_command
    assert "--ignore-scripts" in disputed_command
    assert APPROVED_BUILD_CONFIGS["java-maven-v1"].image == "quorum-java-maven-v1:local"
    assert "mvn" in APPROVED_BUILD_CONFIGS["java-maven-v1"].command[-1]
    assert " -o " in APPROVED_BUILD_CONFIGS["java-maven-v1"].command[-1]
