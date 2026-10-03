def test_e2e_normal_verified(client):
    payload = {
        "repository_url": "https://github.com/example/safecalc",
        "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "build_config_id": "python-package-v1",
        "published_hash": "a" * 64,
        "artifact_name": "safecalc.tar.gz",
        "builder_count": 3,
        "quorum_required": 2
    }
    create_res = client.post("/api/v1/releases", json=payload)
    assert create_res.status_code == 201
    release_id = create_res.json()["release_id"]

    verify_res = client.post(f"/api/v1/releases/{release_id}/verify?scenario=NORMAL")
    assert verify_res.status_code == 200
    data = verify_res.json()

    assert data["release_id"] == release_id
    assert data["decision"] == "VERIFIED"
    assert data["decision_source"] == "BLOCKCHAIN"
    assert data["blockchain_consistent"] is True
    assert data["local_quorum"]["achieved"] is True
    assert data["local_quorum"]["agreement"] == "3/3"
    assert data["blockchain"]["is_finalized"] is True
    assert data["blockchain"]["create_release_tx"] is not None


def test_e2e_one_compromised_builder_verified(client):
    payload = {
        "repository_url": "https://github.com/example/safecalc",
        "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "build_config_id": "python-package-v1",
        "published_hash": "a" * 64,
        "artifact_name": "safecalc.tar.gz",
        "builder_count": 3,
        "quorum_required": 2
    }
    create_res = client.post("/api/v1/releases", json=payload)
    release_id = create_res.json()["release_id"]

    verify_res = client.post(f"/api/v1/releases/{release_id}/verify?scenario=ONE_DISAGREE")
    assert verify_res.status_code == 200
    data = verify_res.json()

    assert data["decision"] == "VERIFIED"
    assert data["decision_source"] == "BLOCKCHAIN"
    assert data["blockchain_consistent"] is True
    assert data["local_quorum"]["achieved"] is True

    builders = data["builders"]
    assert len(builders) == 3
    assert builders[0]["status_detail"] == "AGREE"
    assert builders[1]["status_detail"] == "AGREE"
    assert builders[2]["status_detail"] == "DISAGREE"


def test_e2e_strict_policy_disputed(client):
    payload = {
        "repository_url": "https://github.com/example/safecalc",
        "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "build_config_id": "python-package-v1",
        "published_hash": "a" * 64,
        "artifact_name": "safecalc.tar.gz",
        "builder_count": 3,
        "quorum_required": 3
    }
    create_res = client.post("/api/v1/releases", json=payload)
    release_id = create_res.json()["release_id"]

    verify_res = client.post(f"/api/v1/releases/{release_id}/verify?scenario=STRICT_DISAGREE")
    assert verify_res.status_code == 200
    data = verify_res.json()

    assert data["decision"] == "DISPUTED"
    assert data["decision_source"] == "BLOCKCHAIN"
    assert data["local_quorum"]["achieved"] is False


def test_e2e_wrong_quorum_artifact_rejected(client):
    payload = {
        "repository_url": "https://github.com/example/safecalc",
        "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "build_config_id": "python-package-v1",
        "published_hash": "a" * 64,
        "artifact_name": "safecalc.tar.gz",
        "builder_count": 3,
        "quorum_required": 2
    }
    create_res = client.post("/api/v1/releases", json=payload)
    release_id = create_res.json()["release_id"]

    verify_res = client.post(f"/api/v1/releases/{release_id}/verify?scenario=WRONG_QUORUM")
    assert verify_res.status_code == 200
    data = verify_res.json()

    assert data["decision"] == "REJECTED"
    assert data["decision_source"] == "BLOCKCHAIN"
    assert data["blockchain"]["quorum_hash"] == "b" * 64
