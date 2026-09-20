"""
Cryptographic Tamper-Evident Audit Ledger.
Implements a hash-chain log of all cross-hospital queries, role declarations,
purpose statements, participating nodes, and privacy budget expenditures.
Any retroactive tampering with previous log entries invalidates the cryptographic chain.
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

def compute_sha256(data_string: str) -> str:
    return hashlib.sha256(data_string.encode("utf-8")).hexdigest()

class AuditBlock:
    def __init__(
        self,
        index: int,
        timestamp: str,
        researcher: str,
        role: str,
        purpose: str,
        query_type: str,
        query_parameters: Dict[str, Any],
        participating_nodes: List[str],
        epsilon_spent: float,
        previous_hash: str,
        block_hash: Optional[str] = None
    ):
        self.index = index
        self.timestamp = timestamp
        self.researcher = researcher
        self.role = role
        self.purpose = purpose
        self.query_type = query_type
        self.query_parameters = query_parameters
        self.participating_nodes = participating_nodes
        self.epsilon_spent = epsilon_spent
        self.previous_hash = previous_hash
        self.block_hash = block_hash or self.calculate_hash()

    def calculate_hash(self) -> str:
        payload = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "researcher": self.researcher,
            "role": self.role,
            "purpose": self.purpose,
            "query_type": self.query_type,
            "query_parameters": self.query_parameters,
            "participating_nodes": self.participating_nodes,
            "epsilon_spent": self.epsilon_spent,
            "previous_hash": self.previous_hash
        }, sort_keys=True)
        return compute_sha256(payload)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "researcher": self.researcher,
            "role": self.role,
            "purpose": self.purpose,
            "query_type": self.query_type,
            "query_parameters": self.query_parameters,
            "participating_nodes": self.participating_nodes,
            "epsilon_spent": self.epsilon_spent,
            "previous_hash": self.previous_hash,
            "block_hash": self.block_hash
        }

class AuditLedger:
    def __init__(self):
        self.chain: List[AuditBlock] = []
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis = AuditBlock(
            index=0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            researcher="SYSTEM_GENESIS",
            role="SYSTEM",
            purpose="FEDERATION_INITIALIZATION",
            query_type="INIT_LEDGER",
            query_parameters={"message": "Healthcare Federation Genesis Block Initialized"},
            participating_nodes=["Hospital A", "Hospital B", "Hospital C"],
            epsilon_spent=0.0,
            previous_hash="0" * 64
        )
        self.chain.append(genesis)

    def log_query(
        self,
        researcher: str,
        role: str,
        purpose: str,
        query_type: str,
        query_parameters: Dict[str, Any],
        participating_nodes: List[str],
        epsilon_spent: float
    ) -> AuditBlock:
        prev_block = self.chain[-1]
        new_block = AuditBlock(
            index=len(self.chain),
            timestamp=datetime.now(timezone.utc).isoformat(),
            researcher=researcher,
            role=role,
            purpose=purpose,
            query_type=query_type,
            query_parameters=query_parameters,
            participating_nodes=participating_nodes,
            epsilon_spent=round(epsilon_spent, 3),
            previous_hash=prev_block.block_hash
        )
        self.chain.append(new_block)
        return new_block

    def verify_integrity(self) -> Dict[str, Any]:
        """
        Validates cryptographic integrity of the entire ledger chain.
        Ensures both hash linkage and block internal content hashes match.
        """
        if not self.chain:
            return {"valid": False, "reason": "Chain is empty"}

        for i in range(len(self.chain)):
            current = self.chain[i]

            # Verify block's own hash matches its contents
            expected_hash = current.calculate_hash()
            if current.block_hash != expected_hash:
                return {
                    "valid": False,
                    "corrupted_block_index": i,
                    "reason": f"Content mismatch in Block #{i}: Stored hash '{current.block_hash[:12]}...' != Expected '{expected_hash[:12]}...'"
                }

            # Verify hash pointer to previous block
            if i > 0:
                prev = self.chain[i - 1]
                if current.previous_hash != prev.block_hash:
                    return {
                        "valid": False,
                        "corrupted_block_index": i,
                        "reason": f"Broken chain pointer between Block #{i-1} and Block #{i}."
                    }

        return {
            "valid": True,
            "total_blocks": len(self.chain),
            "head_hash": self.chain[-1].block_hash,
            "verified_at": datetime.now(timezone.utc).isoformat()
        }

    def simulate_tampering(self, block_index: int, fake_researcher: str = "MALICIOUS_ADVERSARY") -> Dict[str, Any]:
        """
        Demonstration utility: Alters a block's content without recomputing downstream hashes,
        demonstrating that the tamper-evident chain immediately flags the corruption.
        """
        if block_index <= 0 or block_index >= len(self.chain):
            return {"success": False, "error": "Invalid block index for tampering demo."}

        target_block = self.chain[block_index]
        old_researcher = target_block.researcher
        target_block.researcher = fake_researcher  # Secretly modify field without updating hash
        return {
            "success": True,
            "tampered_block_index": block_index,
            "original_field": old_researcher,
            "tampered_field": fake_researcher,
            "message": f"Block #{block_index} researcher field altered to '{fake_researcher}' without cryptographic proof."
        }

    def restore_block(self, block_index: int, original_researcher: str):
        if 0 < block_index < len(self.chain):
            self.chain[block_index].researcher = original_researcher

    def get_blocks(self) -> List[Dict[str, Any]]:
        return [b.to_dict() for b in self.chain]
