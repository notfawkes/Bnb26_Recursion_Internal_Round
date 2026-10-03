def test_health_check_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "quorum-backend"}


def test_create_release_api_success(client):
    payload = {
        "repository_url": "https://github.com/example/safecalc",
        "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "build_config_id": "python-package-v1",
        "published_hash": "a" * 64,
        "artifact_name": "safecalc.tar.gz",
        "builder_count": 3,
        "quorum_required": 2
    }
    response = client.post("/api/v1/releases", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "release_id" in data
    assert data["repository_url"] == payload["repository_url"]
    assert data["commit_sha"] == payload["commit_sha"].lower()
    assert data["published_hash"] == payload["published_hash"]
    assert data["status"] == "CREATED"


def test_create_release_invalid_quorum_policy(client):
    payload = {
        "repository_url": "https://github.com/example/safecalc",
        "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "published_hash": "a" * 64,
        "artifact_name": "safecalc.tar.gz",
        "builder_count": 2,
        "quorum_required": 3  # invalid: quorum_required > builder_count
    }
    response = client.post("/api/v1/releases", json=payload)
    assert response.status_code == 400
    assert "quorum_required" in response.json()["detail"]


def test_get_nonexistent_release_returns_404(client):
    response = client.get("/api/v1/releases/REL-NONEXISTENT")
    assert response.status_code == 404
