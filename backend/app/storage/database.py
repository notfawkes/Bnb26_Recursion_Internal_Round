import json
import sqlite3
from typing import Dict, Any, List, Optional
from app.schemas.release import ReleaseResponse
from app.core.enums import ReleaseStatus


class Database:
    """
    SQLite persistence layer for storing releases, attestations, verification results, and audit logs.
    """

    def __init__(self, db_path: str = "./quorum.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize SQLite database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Releases Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS releases (
                release_id TEXT PRIMARY KEY,
                repository_url TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                build_config_id TEXT NOT NULL DEFAULT 'python-package-v1',
                published_hash TEXT NOT NULL,
                artifact_name TEXT NOT NULL,
                builder_count INTEGER NOT NULL,
                quorum_required INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """)

            # Attestations Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS attestations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                release_id TEXT NOT NULL,
                builder_id TEXT NOT NULL,
                attestation_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (release_id) REFERENCES releases (release_id)
            );
            """)

            # Verification Results & Audit History Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS verification_audits (
                verification_id TEXT PRIMARY KEY,
                release_id TEXT NOT NULL,
                repository TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                published_hash TEXT NOT NULL,
                builder_results_json TEXT NOT NULL,
                local_quorum_json TEXT NOT NULL,
                blockchain_json TEXT NOT NULL,
                decision TEXT NOT NULL,
                decision_source TEXT NOT NULL,
                blockchain_consistent INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (release_id) REFERENCES releases (release_id)
            );
            """)

            conn.commit()

    def save_release(self, release: ReleaseResponse) -> None:
        """Saves a new release to database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO releases 
                (release_id, repository_url, commit_sha, build_config_id, published_hash, artifact_name, builder_count, quorum_required, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    release.release_id,
                    release.repository_url,
                    release.commit_sha,
                    release.build_config_id,
                    release.published_hash,
                    release.artifact_name,
                    release.builder_count,
                    release.quorum_required,
                    release.status.value if hasattr(release.status, "value") else str(release.status),
                    release.created_at
                )
            )
            conn.commit()

    def update_release_status(self, release_id: str, status: ReleaseStatus) -> None:
        """Updates release status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            status_str = status.value if hasattr(status, "value") else str(status)
            cursor.execute(
                "UPDATE releases SET status = ? WHERE release_id = ?",
                (status_str, release_id)
            )
            conn.commit()

    def get_release(self, release_id: str) -> Optional[ReleaseResponse]:
        """Retrieves a release by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM releases WHERE release_id = ?", (release_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return ReleaseResponse(
                release_id=row["release_id"],
                repository_url=row["repository_url"],
                repository=row["repository_url"],
                commit_sha=row["commit_sha"],
                commit=row["commit_sha"],
                build_config_id=row["build_config_id"],
                published_hash=row["published_hash"],
                artifact_name=row["artifact_name"],
                builder_count=row["builder_count"],
                quorum_required=row["quorum_required"],
                status=ReleaseStatus(row["status"]),
                created_at=row["created_at"]
            )

    def save_attestations(self, release_id: str, attestations: List[Dict[str, Any]], created_at: str) -> None:
        """Saves builder attestations for a release."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for att in attestations:
                builder_id = att.get("builder", {}).get("id", "unknown")
                cursor.execute(
                    """
                    INSERT INTO attestations (release_id, builder_id, attestation_json, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (release_id, builder_id, json.dumps(att), created_at)
                )
            conn.commit()

    def get_attestations(self, release_id: str) -> List[Dict[str, Any]]:
        """Retrieves stored attestations for a release."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT attestation_json FROM attestations WHERE release_id = ?", (release_id,))
            rows = cursor.fetchall()
            return [json.loads(row["attestation_json"]) for row in rows]

    def save_verification_audit(self, audit_record: Dict[str, Any]) -> None:
        """Saves a verification audit record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO verification_audits
                (verification_id, release_id, repository, commit_sha, published_hash, 
                 builder_results_json, local_quorum_json, blockchain_json, decision, decision_source, blockchain_consistent, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_record["verification_id"],
                    audit_record["release_id"],
                    audit_record["repository_url"],
                    audit_record["commit_sha"],
                    audit_record["published_hash"],
                    json.dumps(audit_record["builders"]),
                    json.dumps(audit_record["local_quorum"]),
                    json.dumps(audit_record["blockchain"]),
                    audit_record["decision"],
                    audit_record["decision_source"],
                    1 if audit_record.get("blockchain_consistent", True) else 0,
                    audit_record["timestamp"]
                )
            )
            conn.commit()

    def get_verification_audit(self, release_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves latest verification audit record for a release."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM verification_audits WHERE release_id = ? ORDER BY timestamp DESC LIMIT 1",
                (release_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "verification_id": row["verification_id"],
                "release_id": row["release_id"],
                "repository_url": row["repository"],
                "commit_sha": row["commit_sha"],
                "published_hash": row["published_hash"],
                "builders": json.loads(row["builder_results_json"]),
                "local_quorum": json.loads(row["local_quorum_json"]),
                "blockchain": json.loads(row["blockchain_json"]),
                "decision": row["decision"],
                "decision_source": row["decision_source"],
                "blockchain_consistent": bool(row["blockchain_consistent"]),
                "timestamp": row["timestamp"]
            }


# Default singleton instance
db = Database()
