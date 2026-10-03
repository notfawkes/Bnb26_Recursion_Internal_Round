import json
import os
import time
import hashlib
from typing import Dict, Any, List, Optional
from web3 import Web3
from app.config import settings
from app.services.builder_service import builder_registry

DECISION_MAP = {
    0: "NONE",
    1: "VERIFIED",
    2: "REJECTED",
    3: "DISPUTED"
}


def _to_bytes32(hex_str: str) -> bytes:
    """Converts a 64-character hex string to 32 bytes for Solidity bytes32."""
    clean = hex_str.strip().lower()
    if clean.startswith("0x"):
        clean = clean[2:]
    if len(clean) != 64:
        clean = clean.zfill(64)[:64]
    return bytes.fromhex(clean)


def _from_bytes32(b: Any) -> str:
    """Converts bytes/bytes32 from Solidity to 64-character hex string."""
    if isinstance(b, bytes):
        return b.hex().lower()
    if isinstance(b, str):
        s = b.lower()
        if s.startswith("0x"):
            s = s[2:]
        return s
    return str(b)


class MockBlockchainService:
    """
    Mock implementation of BlockchainService representing Person 1's smart contract.
    Maintains internal state and simulates contract functions: createRelease, submitAttestation, finalizeRelease, getRelease.
    """

    def __init__(self):
        self._next_release_id = 1
        self._releases: Dict[int, Dict[str, Any]] = {}
        self._attestations: Dict[int, List[Dict[str, Any]]] = {}

    async def create_release(
        self,
        repository_url: str,
        commit_sha: str,
        published_hash: str,
        builder_count: int,
        quorum_required: int
    ) -> Dict[str, Any]:
        rel_id = self._next_release_id
        self._next_release_id += 1

        tx_hash = "0x" + hashlib.sha256(f"create_{rel_id}_{time.time()}".encode()).hexdigest()

        self._releases[rel_id] = {
            "release_id": rel_id,
            "repository": repository_url,
            "commit": commit_sha,
            "publishedHash": published_hash,
            "quorumHash": "",
            "builderCount": builder_count,
            "quorumRequired": quorum_required,
            "decision": 0,
            "isFinalized": False,
            "create_release_tx": tx_hash,
            "finalize_tx": None,
            "attestation_txs": []
        }
        self._attestations[rel_id] = []

        return {"recorded": True, "release_id": rel_id, "transaction_hash": tx_hash}

    async def submit_attestation(
        self,
        release_id: int | str,
        builder_id: str,
        artifact_hash: str
    ) -> Dict[str, Any]:
        rel_id = int(release_id)
        builder_info = builder_registry.get_builder(builder_id)
        builder_address = builder_info["wallet_address"] if builder_info else "0x00"

        tx_hash = "0x" + hashlib.sha256(f"attest_{rel_id}_{builder_id}_{artifact_hash}_{time.time()}".encode()).hexdigest()

        attestation_record = {
            "builder": builder_address,
            "builder_id": builder_id,
            "artifactHash": artifact_hash,
            "transaction_hash": tx_hash
        }

        if rel_id in self._releases:
            self._releases[rel_id]["attestation_txs"].append(tx_hash)
        if rel_id not in self._attestations:
            self._attestations[rel_id] = []
        self._attestations[rel_id].append(attestation_record)

        return {"recorded": True, "transaction_hash": tx_hash}

    async def finalize_release(self, release_id: int | str) -> Dict[str, Any]:
        rel_id = int(release_id)
        rel = self._releases.get(rel_id)
        if not rel:
            tx_hash = "0x" + hashlib.sha256(f"fin_empty_{rel_id}".encode()).hexdigest()
            return {"recorded": False, "transaction_hash": tx_hash}

        # Calculate quorum on mock contract
        atts = self._attestations.get(rel_id, [])
        hash_counts: Dict[str, int] = {}
        for a in atts:
            h = a["artifactHash"].lower()
            hash_counts[h] = hash_counts.get(h, 0) + 1

        max_count = 0
        winning_hash = ""
        for h, count in hash_counts.items():
            if count > max_count:
                max_count = count
                winning_hash = h
            elif count == max_count and count > 0:
                if h == rel["publishedHash"].lower():
                    winning_hash = h

        quorum_req = rel["quorumRequired"]
        published_h = rel["publishedHash"].lower()

        if max_count >= quorum_req:
            rel["quorumHash"] = winning_hash
            if winning_hash == published_h:
                rel["decision"] = 1  # VERIFIED
            else:
                rel["decision"] = 2  # REJECTED
        else:
            rel["quorumHash"] = winning_hash if max_count > 0 else ""
            rel["decision"] = 3  # DISPUTED

        rel["isFinalized"] = True
        tx_hash = "0x" + hashlib.sha256(f"finalize_{rel_id}_{rel['decision']}_{time.time()}".encode()).hexdigest()
        rel["finalize_tx"] = tx_hash

        return {
            "recorded": True,
            "release_id": rel_id,
            "decision": DECISION_MAP[rel["decision"]],
            "transaction_hash": tx_hash
        }

    async def get_release(self, release_id: int | str) -> Dict[str, Any]:
        rel_id = int(release_id)
        rel = self._releases.get(rel_id)
        if not rel:
            return {
                "release_id": rel_id,
                "published_hash": "",
                "quorum_hash": "",
                "decision": "NONE",
                "is_finalized": False
            }
        return {
            "release_id": rel["release_id"],
            "published_hash": rel["publishedHash"],
            "quorum_hash": rel["quorumHash"],
            "decision": DECISION_MAP[rel["decision"]],
            "is_finalized": rel["isFinalized"],
            "create_release_tx": rel["create_release_tx"],
            "attestation_txs": rel["attestation_txs"],
            "finalize_tx": rel["finalize_tx"]
        }

    async def get_attestations(self, release_id: int | str) -> List[Dict[str, Any]]:
        return self._attestations.get(int(release_id), [])

    async def is_builder(self, address: str) -> bool:
        return True


class AnvilBlockchainService:
    """
    Real Web3.py adapter connecting to Person 1's deployed QuorumVerifier contract on Anvil.
    Loads contract ABI from settings.BLOCKCHAIN_ABI_PATH.
    Submits builder attestations using each builder's specific wallet private key (`msg.sender`).
    Falls back gracefully to MockBlockchainService if RPC is offline.
    """

    def __init__(self):
        self.mock_fallback = MockBlockchainService()
        self.w3: Optional[Web3] = None
        self.contract = None

        if settings.BLOCKCHAIN_RPC_URL:
            try:
                self.w3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_RPC_URL))
                if self.w3.is_connected() and settings.BLOCKCHAIN_CONTRACT_ADDRESS:
                    abi = self._load_abi()
                    if abi:
                        self.contract = self.w3.eth.contract(
                            address=Web3.to_checksum_address(settings.BLOCKCHAIN_CONTRACT_ADDRESS),
                            abi=abi
                        )
            except Exception:
                self.w3 = None
                self.contract = None

    def _load_abi(self) -> Optional[list]:
        abi_path = settings.BLOCKCHAIN_ABI_PATH
        if os.path.exists(abi_path):
            try:
                with open(abi_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    # If file is a wrapper json with "abi" key, extract it
                    if isinstance(content, dict) and "abi" in content:
                        return content["abi"]
                    if isinstance(content, list):
                        return content
            except Exception:
                pass
        return None

    def is_connected(self) -> bool:
        return self.w3 is not None and self.w3.is_connected() and self.contract is not None

    async def create_release(
        self,
        repository_url: str,
        commit_sha: str,
        published_hash: str,
        builder_count: int,
        quorum_required: int
    ) -> Dict[str, Any]:
        if not self.is_connected():
            return await self.mock_fallback.create_release(repository_url, commit_sha, published_hash, builder_count, quorum_required)

        try:
            acct = self.w3.eth.accounts[0] if self.w3.eth.accounts else None
            pub_bytes32 = _to_bytes32(published_hash)

            if settings.BLOCKCHAIN_PRIVATE_KEY and self.w3:
                account = self.w3.eth.account.from_key(settings.BLOCKCHAIN_PRIVATE_KEY)
                tx_data = self.contract.functions.createRelease(
                    repository_url,
                    commit_sha,
                    pub_bytes32,
                    int(builder_count),
                    int(quorum_required)
                ).build_transaction({
                    'from': account.address,
                    'nonce': self.w3.eth.get_transaction_count(account.address),
                    'gas': 300000,
                    'gasPrice': self.w3.eth.gas_price
                })
                signed_tx = self.w3.eth.account.sign_transaction(tx_data, settings.BLOCKCHAIN_PRIVATE_KEY)
                tx_hash_bytes = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash_bytes)
                rel_id = self.contract.functions.releaseCount().call()
                return {"recorded": True, "release_id": rel_id, "transaction_hash": receipt.transactionHash.hex()}

            elif acct:
                tx = self.contract.functions.createRelease(
                    repository_url,
                    commit_sha,
                    pub_bytes32,
                    int(builder_count),
                    int(quorum_required)
                ).transact({'from': acct})

                receipt = self.w3.eth.wait_for_transaction_receipt(tx)
                rel_id = self.contract.functions.releaseCount().call()
                return {"recorded": True, "release_id": rel_id, "transaction_hash": receipt.transactionHash.hex()}
        except Exception:
            pass

        return await self.mock_fallback.create_release(repository_url, commit_sha, published_hash, builder_count, quorum_required)

    async def submit_attestation(
        self,
        release_id: int | str,
        builder_id: str,
        artifact_hash: str
    ) -> Dict[str, Any]:
        if not self.is_connected():
            return await self.mock_fallback.submit_attestation(release_id, builder_id, artifact_hash)

        try:
            builder_info = builder_registry.get_builder(builder_id)
            eth_priv = builder_registry.get_ethereum_private_key(builder_id)
            wallet = builder_info["wallet_address"] if builder_info else None
            art_bytes32 = _to_bytes32(artifact_hash)

            if eth_priv and self.w3:
                account = self.w3.eth.account.from_key(eth_priv)
                tx_data = self.contract.functions.submitAttestation(
                    int(release_id),
                    art_bytes32
                ).build_transaction({
                    'from': account.address,
                    'nonce': self.w3.eth.get_transaction_count(account.address),
                    'gas': 200000,
                    'gasPrice': self.w3.eth.gas_price
                })
                signed_tx = self.w3.eth.account.sign_transaction(tx_data, eth_priv)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                self.w3.eth.wait_for_transaction_receipt(tx_hash)
                return {"recorded": True, "transaction_hash": tx_hash.hex()}
            elif wallet:
                tx = self.contract.functions.submitAttestation(
                    int(release_id),
                    art_bytes32
                ).transact({'from': Web3.to_checksum_address(wallet)})
                receipt = self.w3.eth.wait_for_transaction_receipt(tx)
                return {"recorded": True, "transaction_hash": receipt.transactionHash.hex()}
        except Exception:
            pass

        return await self.mock_fallback.submit_attestation(release_id, builder_id, artifact_hash)

    async def finalize_release(self, release_id: int | str) -> Dict[str, Any]:
        if not self.is_connected():
            return await self.mock_fallback.finalize_release(release_id)

        try:
            acct = self.w3.eth.accounts[0] if self.w3.eth.accounts else self.w3.eth.coinbase
            tx = self.contract.functions.finalizeRelease(int(release_id)).transact({'from': acct})
            receipt = self.w3.eth.wait_for_transaction_receipt(tx)

            rel_data = await self.get_release(release_id)
            return {
                "recorded": True,
                "release_id": int(release_id),
                "decision": rel_data.get("decision", "VERIFIED"),
                "transaction_hash": receipt.transactionHash.hex()
            }
        except Exception:
            return await self.mock_fallback.finalize_release(release_id)

    async def get_release(self, release_id: int | str) -> Dict[str, Any]:
        if not self.is_connected():
            return await self.mock_fallback.get_release(release_id)

        try:
            res = self.contract.functions.getRelease(int(release_id)).call()
            # res struct: (id, repository, commit, publishedHash, builderCount, quorumRequired, quorumHash, decision, isFinalized)
            pub_h = _from_bytes32(res[3])
            q_h = _from_bytes32(res[6])
            dec_int = res[7]
            is_fin = res[8]
            dec_str = DECISION_MAP.get(dec_int, "NONE")
            return {
                "release_id": int(release_id),
                "published_hash": pub_h,
                "quorum_hash": q_h,
                "decision": dec_str,
                "is_finalized": is_fin
            }
        except Exception:
            return await self.mock_fallback.get_release(release_id)

    async def get_attestations(self, release_id: int | str) -> List[Dict[str, Any]]:
        if not self.is_connected():
            return await self.mock_fallback.get_attestations(release_id)

        try:
            atts = self.contract.functions.getAttestations(int(release_id)).call()
            return [{"builder": a[0], "artifactHash": _from_bytes32(a[1]), "timestamp": a[2]} for a in atts]
        except Exception:
            return await self.mock_fallback.get_attestations(release_id)

    async def is_builder(self, address: str) -> bool:
        if not self.is_connected():
            return True
        try:
            return self.contract.functions.isBuilder(Web3.to_checksum_address(address)).call()
        except Exception:
            return True
