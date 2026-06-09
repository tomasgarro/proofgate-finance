"""
Simulated proof: private position size constraint.

THIS IS A SIMULATION — NOT A REAL ZK PROOF.

This module mocks the behavior of a Midnight/Compact circuit that would prove
a proposed position size is within a private maximum, without revealing the maximum.

Use this as a placeholder until the actual Compact circuit is implemented.
See docs/midnight-proof-experiments.md for the real implementation design.
"""

import hashlib
from dataclasses import dataclass


_SALT = "proofgate-v1-private-max"


@dataclass
class MockProofResult:
    valid: bool
    public_input_proposed_pct: float
    commitment_to_private_max: str
    proof_type: str
    note: str

    def summary(self) -> str:
        status = "VALID" if self.valid else "INVALID"
        return (
            f"[{self.proof_type}] {status}\n"
            f"  Proposed: {self.public_input_proposed_pct}%\n"
            f"  Private max commitment: {self.commitment_to_private_max[:24]}...\n"
            f"  Note: {self.note}"
        )


def simulate_position_size_proof(
    private_max_pct: float,
    proposed_pct: float,
) -> MockProofResult:
    """
    Simulate a ZK proof that proposed_pct <= private_max_pct.

    The verifier receives:
    - proposed_pct (public)
    - commitment_to_private_max (a hash binding the prover to a specific max)
    - valid (whether the constraint was satisfied)

    The verifier does NOT learn private_max_pct.

    This is a cryptographic commitment, not a ZK proof. A real implementation
    would use Compact on the Midnight network.
    """
    valid = proposed_pct <= private_max_pct

    commitment = hashlib.sha256(
        f"{_SALT}:{private_max_pct:.6f}".encode("utf-8")
    ).hexdigest()

    return MockProofResult(
        valid=valid,
        public_input_proposed_pct=proposed_pct,
        commitment_to_private_max="sha256:" + commitment,
        proof_type="simulated_commitment_mock",
        note=(
            "NOT a real ZK proof. This simulation uses a hash commitment to bind "
            "the prover to a specific private maximum. A real proof requires "
            "Compact on Midnight. See docs/midnight-proof-experiments.md."
        ),
    )
