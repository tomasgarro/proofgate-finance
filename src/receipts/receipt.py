"""Receipt generator: hashed audit trail for policy gate decisions."""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.policies.gate import GateResult, Policy, Proposal


@dataclass
class Receipt:
    decision: str
    checked_constraints: list[str]
    failed_constraints: list[str]
    timestamp_utc: str
    policy_hash: str
    proposal_hash: str
    version: str = "1.0"
    proof_type: str = "deterministic_rule_check"
    midnight_proof: Optional[str] = None  # future: ZK proof reference

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "checked_constraints": self.checked_constraints,
            "failed_constraints": self.failed_constraints,
            "timestamp_utc": self.timestamp_utc,
            "policy_hash": self.policy_hash,
            "proposal_hash": self.proposal_hash,
            "version": self.version,
            "proof_type": self.proof_type,
            "midnight_proof": self.midnight_proof,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            f.write(self.to_json())

    def summary(self) -> str:
        lines = [
            f"Receipt [{self.version}] — {self.timestamp_utc}",
            f"  Decision:    {self.decision.upper()}",
            f"  Proof type:  {self.proof_type}",
            f"  Policy hash: {self.policy_hash[:16]}...",
            f"  Proposal hash: {self.proposal_hash[:16]}...",
            f"  Constraints passed: {len(self.checked_constraints)}",
            f"  Constraints failed: {len(self.failed_constraints)}",
        ]
        if self.midnight_proof:
            lines.append(f"  Midnight proof: {self.midnight_proof}")
        return "\n".join(lines)


def generate(policy: Policy, proposal: Proposal, result: GateResult) -> Receipt:
    """
    Generate an audit receipt from a policy gate check.

    The receipt hashes the policy and proposal independently so either can be
    verified in isolation. The hashes are deterministic given the same inputs.
    Hashing uses JSON-serialized canonical form (sorted keys).
    """
    policy_hash = _sha256_dict(policy.to_dict())
    proposal_hash = _sha256_dict(proposal.to_dict())
    timestamp = datetime.now(timezone.utc).isoformat()

    return Receipt(
        decision=result.decision,
        checked_constraints=result.passed,
        failed_constraints=result.failed,
        timestamp_utc=timestamp,
        policy_hash=policy_hash,
        proposal_hash=proposal_hash,
    )


def _sha256_dict(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=True)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
