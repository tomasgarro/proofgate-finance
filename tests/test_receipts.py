"""Unit tests for the receipt generator."""

import json
import pytest
from src.policies.gate import Policy, Proposal, check
from src.receipts.receipt import generate


def _setup():
    policy = Policy(
        allowed_assets=["BTC", "ETH", "ADA"],
        max_position_pct=5.0,
        allow_leverage=False,
        allowed_venues=["simulated"],
    )
    proposal = Proposal(
        asset="ADA", action="buy", position_pct=3.0, venue="simulated", leverage=1.0,
    )
    result = check(policy, proposal)
    return policy, proposal, result


def test_receipt_generated():
    policy, proposal, result = _setup()
    receipt = generate(policy, proposal, result)
    assert receipt.decision == "allow"
    assert receipt.policy_hash.startswith("sha256:")
    assert receipt.proposal_hash.startswith("sha256:")


def test_receipt_hashes_are_deterministic():
    policy, proposal, result = _setup()
    r1 = generate(policy, proposal, result)
    r2 = generate(policy, proposal, result)
    assert r1.policy_hash == r2.policy_hash
    assert r1.proposal_hash == r2.proposal_hash


def test_receipt_hashes_differ_for_different_policies():
    policy1 = Policy(allowed_assets=["BTC"], max_position_pct=5.0, allowed_venues=["simulated"])
    policy2 = Policy(allowed_assets=["ETH"], max_position_pct=10.0, allowed_venues=["simulated"])
    proposal = Proposal("BTC", "buy", 3.0, "simulated", 1.0)

    r1 = check(policy1, proposal)
    r2 = check(policy2, proposal)
    rec1 = generate(policy1, proposal, r1)
    rec2 = generate(policy2, proposal, r2)

    assert rec1.policy_hash != rec2.policy_hash


def test_receipt_hashes_differ_for_different_proposals():
    policy = Policy(allowed_assets=["BTC", "ETH"], max_position_pct=5.0, allowed_venues=["simulated"])
    p1 = Proposal("BTC", "buy", 3.0, "simulated", 1.0)
    p2 = Proposal("ETH", "buy", 3.0, "simulated", 1.0)

    rec1 = generate(policy, p1, check(policy, p1))
    rec2 = generate(policy, p2, check(policy, p2))

    assert rec1.proposal_hash != rec2.proposal_hash


def test_receipt_serializes_to_json():
    policy, proposal, result = _setup()
    receipt = generate(policy, proposal, result)
    json_str = receipt.to_json()
    data = json.loads(json_str)
    assert "decision" in data
    assert "policy_hash" in data
    assert "proposal_hash" in data
    assert "timestamp_utc" in data
    assert "checked_constraints" in data


def test_receipt_records_failed_constraints():
    policy = Policy(allowed_assets=["BTC"], max_position_pct=5.0, allowed_venues=["simulated"])
    proposal = Proposal("DOGE", "buy", 3.0, "simulated", 1.0)
    result = check(policy, proposal)
    receipt = generate(policy, proposal, result)
    assert receipt.decision == "reject"
    assert len(receipt.failed_constraints) > 0


def test_receipt_proof_type_is_labeled():
    policy, proposal, result = _setup()
    receipt = generate(policy, proposal, result)
    assert receipt.proof_type == "deterministic_rule_check"
    assert receipt.midnight_proof is None
