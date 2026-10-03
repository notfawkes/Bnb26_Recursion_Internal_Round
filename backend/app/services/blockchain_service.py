import json
import os
import time
import hashlib
from typing import Dict, Any, List, Optional
from web3 import Web3
from app.config import settings
from app.services.builder_service import builder_registry
from app.core.exceptions import (
    BlockchainServiceError,
    BlockchainUnavailableError,
    ReleaseNotFoundError,
)

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
        h = b.hex().lower()
        if h == "00" * 32:
            return ""
        return h
    if isinstance(b, str):
        s = b.lower()
        if s.startswith("0x"):
            s = s[2:]
        if s == "0" * 64:
            return ""
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
        quorum_required: int,
        build_config_id: str = "python-package-v1",
        artifact_name: str = "safecalc.tar.gz"
    ) -> Dict[str, Any]:
        rel_id = self._next_release_id
        self._next_release_id += 1

        tx_hash = "0x" + hashlib.sha256(f"create_{rel_id}_{time.time()}".encode()).hexdigest()

        self._releases[rel_id] = {
            "release_id": str(rel_id),
            "repository_url": repository_url,
            "commit_sha": commit_sha,
            "build_config_id": build_config_id,
            "artifact_name": artifact_name,
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

        return {"recorded": True, "release_id": str(rel_id), "transaction_hash": tx_hash}

    async def submit_attestation(
        self,
        release_id: int | str,
        builder_id: str,
        artifact_hash: str
    ) -> Dict[str, Any]:
        rel_id = int(str(release_id).replace("REL-", ""))
        builder_info = builder_registry.get_builder(builder_id)
        builder_address = builder_info["wallet_address"] if builder_info else "0x00"

        tx_hash = "0x" + hashlib.sha256(f"attest_{rel_id}_{builder_id}_{artifact_hash}_{time.time()}".encode()).hexdigest()

        attestation_record = {
            "builder": builder_address,
            "builder_id": builder_id,
            "artifactHash": artifact_hash,
            "timestamp": int(time.time()),
            "transaction_hash": tx_hash
        }

        if rel_id in self._attestations:
            self._attestations[rel_id].append(attestation_record)
        else:
            self._attestations[rel_id] = [attestation_record]

        if rel_id in self._releases:
            self._releases[rel_id]["attestation_txs"].append(tx_hash)

        return {"recorded": True, "transaction_hash": tx_hash}

    async def finalize_release(self, release_id: int | str) -> Dict[str, Any]:
        rel_id = int(str(release_id).replace("REL-", ""))
        rel = self._releases.get(rel_id)
        if not rel:
            return {"recorded": False, "release_id": str(rel_id), "decision": "DISPUTED", "transaction_hash": None}

        atts = self._attestations.get(rel_id, [])
        hash_counts: Dict[str, int] = {}
        for a in atts:
            h = a["artifactHash"].lower().strip()
            hash_counts[h] = hash_counts.get(h, 0) + 1

        quorum_hash = None
        for h, count in hash_counts.items():
            if count >= rel["quorumRequired"]:
                quorum_hash = h
                break

        if quorum_hash:
            rel["quorumHash"] = quorum_hash
            pub_clean = rel["publishedHash"].lower().strip()
            if quorum_hash == pub_clean:
                rel["decision"] = 1  # VERIFIED
            else:
                rel["decision"] = 2  # REJECTED
        else:
            rel["decision"] = 3  # DISPUTED
            rel["quorumHash"] = ""

        rel["isFinalized"] = True
        tx_hash = "0x" + hashlib.sha256(f"finalize_{rel_id}_{rel['decision']}_{time.time()}".encode()).hexdigest()
        rel["finalize_tx"] = tx_hash

        return {
            "recorded": True,
            "release_id": str(rel_id),
            "decision": DECISION_MAP[rel["decision"]],
            "transaction_hash": tx_hash
        }

    async def get_release(self, release_id: int | str) -> Dict[str, Any]:
        try:
            rel_id = int(str(release_id).replace("REL-", ""))
        except ValueError:
            rel_id = -1

        rel = self._releases.get(rel_id)
        if not rel:
            return {
                "release_id": str(release_id),
                "repository_url": "",
                "commit_sha": "",
                "build_config_id": "python-package-v1",
                "artifact_name": "safecalc.tar.gz",
                "published_hash": "",
                "quorum_hash": "",
                "builder_count": 3,
                "quorum_required": 2,
                "decision": "NONE",
                "is_finalized": False
            }
        return {
            "release_id": str(rel["release_id"]),
            "repository_url": rel["repository_url"],
            "commit_sha": rel["commit_sha"],
            "build_config_id": rel.get("build_config_id", "python-package-v1"),
            "artifact_name": rel.get("artifact_name", "safecalc.tar.gz"),
            "published_hash": rel["publishedHash"],
            "quorum_hash": rel["quorumHash"],
            "builder_count": rel["builderCount"],
            "quorum_required": rel["quorumRequired"],
            "decision": DECISION_MAP[rel["decision"]],
            "is_finalized": rel["isFinalized"],
            "create_release_tx": rel["create_release_tx"],
            "attestation_txs": rel["attestation_txs"],
            "finalize_tx": rel["finalize_tx"]
        }

    async def get_attestations(self, release_id: int | str) -> List[Dict[str, Any]]:
        try:
            rel_id = int(str(release_id).replace("REL-", ""))
        except ValueError:
            rel_id = 1
        return self._attestations.get(rel_id, [])

    async def is_builder(self, address: str) -> bool:
        return True


class AnvilBlockchainService:
    """
    Authoritative Web3.py adapter connecting to Person 1's deployed QuorumVerifier contract on Anvil.
    - Loads contract ABI from settings.BLOCKCHAIN_ABI_PATH or deployment metadata.
    - Submits builder attestations using each builder's specific Ethereum wallet (msg.sender).
    - Calls finalizeRelease on-chain and reads authoritative on-chain verification decisions.
    - Preserves transaction receipts (create release, attestations, finalize) for auditability.
    """

    def __init__(self):
        self.mock_fallback = MockBlockchainService()
        self.w3: Optional[Web3] = None
        self.contract = None
        self._release_metadata: Dict[str, Dict[str, Any]] = {}
        self._initialize_connection()

    def _initialize_connection(self) -> None:
        if not settings.BLOCKCHAIN_RPC_URL:
            return

        try:
            self.w3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_RPC_URL))
            if not self.w3.is_connected():
                self.contract = None
                return

            contract_address = self._resolve_contract_address()
            abi = self._load_abi()

            if contract_address and abi:
                self.contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(contract_address),
                    abi=abi
                )
        except Exception:
            self.contract = None

    def _resolve_contract_address(self) -> str:
        if settings.BLOCKCHAIN_CONTRACT_ADDRESS:
            return settings.BLOCKCHAIN_CONTRACT_ADDRESS

        # Check deployment metadata file
        deploy_path = settings.BLOCKCHAIN_DEPLOYMENT_PATH
        if os.path.exists(deploy_path):
            try:
                with open(deploy_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    addr = data.get("contractAddress")
                    if addr:
                        return addr
            except Exception:
                pass
        return ""

    def _load_abi(self) -> Optional[list]:
        # Try standalone ABI path
        abi_path = settings.BLOCKCHAIN_ABI_PATH
        if os.path.exists(abi_path):
            try:
                with open(abi_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    if isinstance(content, dict) and "abi" in content:
                        return content["abi"]
                    if isinstance(content, list):
                        return content
            except Exception:
                pass

        # Try deployment metadata
        deploy_path = settings.BLOCKCHAIN_DEPLOYMENT_PATH
        if os.path.exists(deploy_path):
            try:
                with open(deploy_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("abi")
            except Exception:
                pass

        return None

    def is_connected(self) -> bool:
        if not self.w3 or not self.contract:
            self._initialize_connection()
        try:
            return bool(self.w3 and self.w3.is_connected() and self.contract)
        except Exception:
            return False

    def _check_blockchain_availability(self) -> None:
        if not self.is_connected():
            if settings.USE_MOCK_BLOCKCHAIN:
                return
            raise BlockchainUnavailableError(
                f"Blockchain RPC at '{settings.BLOCKCHAIN_RPC_URL}' is unavailable or contract is not deployed."
            )

    async def create_release(
        self,
        repository_url: str,
        commit_sha: str,
        published_hash: str,
        builder_count: int,
        quorum_required: int,
        build_config_id: str = "python-package-v1",
        artifact_name: str = "safecalc.tar.gz"
    ) -> Dict[str, Any]:
        self._check_blockchain_availability()

        if not self.is_connected():
            return await self.mock_fallback.create_release(
                repository_url, commit_sha, published_hash, builder_count, quorum_required, build_config_id, artifact_name
            )

        try:
            pub_bytes32 = _to_bytes32(published_hash)

            # Use configured deployer private key, or first local Anvil account
            deployer_key = settings.BLOCKCHAIN_PRIVATE_KEY or "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
            if deployer_key:
                account = self.w3.eth.account.from_key(deployer_key)
                tx_data = self.contract.functions.createRelease(
                    repository_url,
                    commit_sha,
                    pub_bytes32,
                    int(builder_count),
                    int(quorum_required)
                ).build_transaction({
                    'from': account.address,
                    'nonce': self.w3.eth.get_transaction_count(account.address),
                    'gas': 400000,
                    'gasPrice': self.w3.eth.gas_price
                })
                signed_tx = self.w3.eth.account.sign_transaction(tx_data, deployer_key)
                tx_hash_bytes = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash_bytes)
            else:
                acct = self.w3.eth.accounts[0]
                tx = self.contract.functions.createRelease(
                    repository_url,
                    commit_sha,
                    pub_bytes32,
                    int(builder_count),
                    int(quorum_required)
                ).transact({'from': acct})
                receipt = self.w3.eth.wait_for_transaction_receipt(tx)

            # Determine release ID from logs or count
            events = self.contract.events.ReleaseCreated().process_receipt(receipt)
            if events:
                rel_id = events[0].args.releaseId
            else:
                rel_id = self.contract.functions.releaseCount().call()

            tx_hash_str = receipt.transactionHash.hex()

            # Record metadata in memory
            self._release_metadata[str(rel_id)] = {
                "create_release_tx": tx_hash_str,
                "attestation_txs": [],
                "finalize_tx": None,
                "build_config_id": build_config_id,
                "artifact_name": artifact_name
            }

            return {"recorded": True, "release_id": str(rel_id), "transaction_hash": tx_hash_str}
        except Exception as e:
            if settings.USE_MOCK_BLOCKCHAIN:
                return await self.mock_fallback.create_release(
                    repository_url, commit_sha, published_hash, builder_count, quorum_required, build_config_id, artifact_name
                )
            raise BlockchainServiceError(f"Failed to create release on-chain: {str(e)}")

    async def submit_attestation(
        self,
        release_id: int | str,
        builder_id: str,
        artifact_hash: str
    ) -> Dict[str, Any]:
        self._check_blockchain_availability()

        if not self.is_connected():
            return await self.mock_fallback.submit_attestation(release_id, builder_id, artifact_hash)

        try:
            builder_info = builder_registry.get_builder(builder_id)
            eth_priv = builder_registry.get_ethereum_private_key(builder_id)
            wallet = builder_info["wallet_address"] if builder_info else None
            art_bytes32 = _to_bytes32(artifact_hash)
            rel_int = int(str(release_id).replace("REL-", ""))

            if eth_priv:
                account = self.w3.eth.account.from_key(eth_priv)
                tx_data = self.contract.functions.submitAttestation(
                    rel_int,
                    art_bytes32
                ).build_transaction({
                    'from': account.address,
                    'nonce': self.w3.eth.get_transaction_count(account.address),
                    'gas': 300000,
                    'gasPrice': self.w3.eth.gas_price
                })
                signed_tx = self.w3.eth.account.sign_transaction(tx_data, eth_priv)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                tx_hash_str = tx_hash.hex()
            elif wallet:
                tx = self.contract.functions.submitAttestation(
                    rel_int,
                    art_bytes32
                ).transact({'from': Web3.to_checksum_address(wallet)})
                receipt = self.w3.eth.wait_for_transaction_receipt(tx)
                tx_hash_str = receipt.transactionHash.hex()
            else:
                raise ValueError(f"No wallet or private key configured for builder '{builder_id}'")

            # Track attestation tx
            if str(release_id) in self._release_metadata:
                self._release_metadata[str(release_id)]["attestation_txs"].append(tx_hash_str)

            return {"recorded": True, "transaction_hash": tx_hash_str}
        except Exception as e:
            if settings.USE_MOCK_BLOCKCHAIN:
                return await self.mock_fallback.submit_attestation(release_id, builder_id, artifact_hash)
            raise BlockchainServiceError(f"Failed to submit attestation for {builder_id} on-chain: {str(e)}")

    async def finalize_release(self, release_id: int | str) -> Dict[str, Any]:
        self._check_blockchain_availability()

        if not self.is_connected():
            return await self.mock_fallback.finalize_release(release_id)

        try:
            rel_int = int(str(release_id).replace("REL-", ""))
            deployer_key = settings.BLOCKCHAIN_PRIVATE_KEY or "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

            if deployer_key:
                account = self.w3.eth.account.from_key(deployer_key)
                tx_data = self.contract.functions.finalizeRelease(rel_int).build_transaction({
                    'from': account.address,
                    'nonce': self.w3.eth.get_transaction_count(account.address),
                    'gas': 300000,
                    'gasPrice': self.w3.eth.gas_price
                })
                signed_tx = self.w3.eth.account.sign_transaction(tx_data, deployer_key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                tx_hash_str = tx_hash.hex()
            else:
                acct = self.w3.eth.accounts[0] if self.w3.eth.accounts else self.w3.eth.coinbase
                tx = self.contract.functions.finalizeRelease(rel_int).transact({'from': acct})
                receipt = self.w3.eth.wait_for_transaction_receipt(tx)
                tx_hash_str = receipt.transactionHash.hex()

            if str(release_id) in self._release_metadata:
                self._release_metadata[str(release_id)]["finalize_tx"] = tx_hash_str

            rel_data = await self.get_release(release_id)
            return {
                "recorded": True,
                "release_id": str(release_id),
                "decision": rel_data.get("decision", "VERIFIED"),
                "transaction_hash": tx_hash_str
            }
        except Exception as e:
            if settings.USE_MOCK_BLOCKCHAIN:
                return await self.mock_fallback.finalize_release(release_id)
            raise BlockchainServiceError(f"Failed to finalize release on-chain: {str(e)}")

    async def get_release(self, release_id: int | str) -> Dict[str, Any]:
        self._check_blockchain_availability()

        if not self.is_connected():
            return await self.mock_fallback.get_release(release_id)

        try:
            rel_int = int(str(release_id).replace("REL-", ""))
            res = self.contract.functions.getRelease(rel_int).call()

            # res struct: (id, repository, commit, publishedHash, builderCount, quorumRequired, quorumHash, decision, isFinalized)
            repo_url = res[1]
            commit_s = res[2]
            pub_h = _from_bytes32(res[3])
            b_count = res[4]
            q_req = res[5]
            q_h = _from_bytes32(res[6])
            dec_int = res[7]
            is_fin = res[8]
            dec_str = DECISION_MAP.get(dec_int, "NONE")

            meta = self._release_metadata.get(str(rel_int), {})

            return {
                "release_id": str(res[0]),
                "repository_url": repo_url,
                "commit_sha": commit_s,
                "build_config_id": meta.get("build_config_id", "python-package-v1"),
                "artifact_name": meta.get("artifact_name", "safecalc.tar.gz"),
                "published_hash": pub_h,
                "quorum_hash": q_h,
                "builder_count": b_count,
                "quorum_required": q_req,
                "decision": dec_str,
                "is_finalized": is_fin,
                "create_release_tx": meta.get("create_release_tx"),
                "attestation_txs": meta.get("attestation_txs", []),
                "finalize_tx": meta.get("finalize_tx")
            }
        except Exception as e:
            if settings.USE_MOCK_BLOCKCHAIN:
                return await self.mock_fallback.get_release(release_id)
            raise ReleaseNotFoundError(str(release_id))

    async def get_attestations(self, release_id: int | str) -> List[Dict[str, Any]]:
        self._check_blockchain_availability()

        if not self.is_connected():
            return await self.mock_fallback.get_attestations(release_id)

        try:
            rel_int = int(str(release_id).replace("REL-", ""))
            atts = self.contract.functions.getAttestations(rel_int).call()
            return [{"builder": a[0], "artifactHash": _from_bytes32(a[1]), "timestamp": a[2]} for a in atts]
        except Exception as e:
            if settings.USE_MOCK_BLOCKCHAIN:
                return await self.mock_fallback.get_attestations(release_id)
            raise BlockchainServiceError(f"Failed to retrieve attestations on-chain: {str(e)}")

    async def is_builder(self, address: str) -> bool:
        if not self.is_connected():
            return True
        try:
            return self.contract.functions.isBuilder(Web3.to_checksum_address(address)).call()
        except Exception:
            return True
