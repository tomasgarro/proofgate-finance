# Midnight / Compact Proof Experiment Design

## Purpose

This document captures the design intent for Phase 4: a minimal Compact smart contract that proves a private risk constraint without revealing the private value.

The goal is not to rebuild the entire policy gate in Compact. The goal is to demonstrate one meaningful proof that connects the ProofGate concept to Midnight's selective disclosure capabilities.

## Candidate proof: private position size constraint

### Problem statement

An AI agent proposes a trade with a given position size (e.g. 3% of portfolio). The user has a private maximum they do not want to reveal (e.g. 5%). The system should be able to prove to an external observer that the proposed position is within the user's limit, without revealing what that limit is.

### Proof structure

```
Private inputs (known only to prover):
  max_position_pct: Field  -- e.g. 500 (representing 5.00%)

Public inputs (visible to verifier):
  proposed_position_pct: Field  -- e.g. 300 (representing 3.00%)

Constraint:
  proposed_position_pct <= max_position_pct

Public output:
  valid: Boolean  -- true if constraint satisfied

ZK guarantee:
  Verifier learns only that the proposal is within limits.
  Verifier does not learn the actual maximum.
```

### Why this matters

This is the simplest possible proof that demonstrates:
- Private user data (risk limit) stays private.
- A public check (proposal is safe) can be verified by any party.
- An AI agent can operate under constraints it cannot inspect or override.

### Compact pseudo-code (to be verified with Midnight Expert tools)

```
// This is illustrative only.
// Actual syntax must be verified using Midnight Expert tools.
// Do not ship this as production Compact code.

ledger max_position_pct: Cell<Uint32>;  // private, set by user

circuit check_position_size(
  proposed_pct: Uint32  // public: proposed position in basis points
): Boolean {
  const max = kernel.currentPrivateState.max_position_pct;
  const within_limit = proposed_pct <= max;
  disclose(within_limit);
  return within_limit;
}
```

## Alternative candidate proofs

These are harder but more commercially meaningful. Attempt after the basic proof works.

### Asset allowlist membership (without revealing full allowlist)
Prove that a proposed asset is in the user's private allowlist without revealing the full list.
Approach: Merkle tree commitment over the allowlist. Prove membership via Merkle proof.

### Strategy license validity
Prove that a valid license exists for a strategy without revealing the license details or strategy content.
Approach: commitment scheme or hash-based validity check.

### Fee calculation correctness
Prove that a fee was calculated according to agreed-upon logic without revealing the underlying trade size or rate.
Approach: arithmetic constraints on committed values.

## Implementation path

1. Verify Compact syntax for basic comparison circuit with Midnight Expert tools.
2. Confirm whether Uint32 or Field arithmetic is appropriate for percentage values.
3. Check how private state is initialized and updated in Compact.
4. Implement smallest working circuit.
5. Write witness TypeScript that provides the private max value.
6. Test with Midnight devnet.
7. Document what is proven, what is public, and what the proof cost is.

## Simulation fallback

If Compact tooling cannot support this circuit cleanly in Phase 4, use a deterministic mock:

```python
import hashlib, json

def simulate_proof(private_max: float, proposed: float) -> dict:
    valid = proposed <= private_max
    # The commitment proves we used a specific max without revealing it
    commitment = hashlib.sha256(f"max:{private_max}:salt:proofgate-v1".encode()).hexdigest()
    return {
        "proof_type": "simulated_mock",  # NOT a real ZK proof
        "valid": valid,
        "public_input_proposed_pct": proposed,
        "commitment_to_private_max": commitment,
        "note": "This is a simulation. A real ZK proof requires Compact/Midnight."
    }
```

The simulation must be clearly labeled. It is a placeholder, not a security guarantee.

## Blockers to document

If the proof experiment cannot proceed, record:

- Compact version and any limitations on comparison operations.
- Whether private state initialization is supported for this use case.
- Whether the devnet is available and functional.
- What the minimum viable proof would require vs what tooling supports.

## Connection to the broader product

Once this proof works, it can replace the policy hash in the receipt system with a real ZK commitment. The receipt then carries:
- The public proposed position.
- A ZK proof that it was within the private limit.
- No exposure of the private limit itself.

That is the bridge from research tool to proof-gated agent.
