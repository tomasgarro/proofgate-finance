"""Unit tests for the deterministic policy gate."""

import pytest
from src.policies.gate import Policy, Proposal, check


def _default_policy() -> Policy:
    return Policy(
        allowed_assets=["BTC", "ETH", "ADA"],
        max_position_pct=5.0,
        max_daily_loss_pct=2.0,
        allow_leverage=False,
        max_leverage=1.0,
        allowed_venues=["simulated"],
        requires_user_approval=True,
    )


def _valid_proposal() -> Proposal:
    return Proposal(
        asset="ADA",
        action="buy",
        position_pct=3.0,
        venue="simulated",
        leverage=1.0,
        rationale="Piotroski 7/9, Altman safe zone",
    )


def test_valid_proposal_is_allowed():
    result = check(_default_policy(), _valid_proposal())
    assert result.is_allowed()
    assert result.decision == "allow"


def test_blocked_asset_is_rejected():
    proposal = _valid_proposal()
    proposal.asset = "DOGE"
    result = check(_default_policy(), proposal)
    assert not result.is_allowed()
    assert any("not_in_allowed_list" in f for f in result.failed)


def test_position_too_large_is_rejected():
    proposal = _valid_proposal()
    proposal.position_pct = 10.0
    result = check(_default_policy(), proposal)
    assert not result.is_allowed()
    assert any("exceeds_limit" in f for f in result.failed)


def test_leverage_rejected_when_disallowed():
    proposal = _valid_proposal()
    proposal.leverage = 2.0
    result = check(_default_policy(), proposal)
    assert not result.is_allowed()
    assert any("leverage_not_allowed" in f for f in result.failed)


def test_venue_not_in_allowed_list_is_rejected():
    proposal = _valid_proposal()
    proposal.venue = "binance"
    result = check(_default_policy(), proposal)
    assert not result.is_allowed()
    assert any("venue_not_allowed" in f for f in result.failed)


def test_blocked_asset_in_blocked_list():
    policy = _default_policy()
    policy.blocked_assets = ["ADA"]
    result = check(policy, _valid_proposal())
    assert not result.is_allowed()
    assert any("blocked_list" in f for f in result.failed)


def test_multiple_failures_all_reported():
    proposal = Proposal(
        asset="DOGE",
        action="buy",
        position_pct=20.0,
        venue="ftx",
        leverage=3.0,
    )
    result = check(_default_policy(), proposal)
    assert not result.is_allowed()
    assert len(result.failed) >= 3


def test_empty_allowed_assets_skips_asset_check():
    policy = Policy(allowed_assets=[], allowed_venues=["simulated"])
    proposal = _valid_proposal()
    result = check(policy, proposal)
    assert result.is_allowed()


def test_strategy_license_required_but_missing():
    policy = _default_policy()
    policy.strategy_license_required = True
    result = check(policy, _valid_proposal())
    assert not result.is_allowed()
    assert any("license_required" in f for f in result.failed)


def test_strategy_license_provided_passes():
    policy = _default_policy()
    policy.strategy_license_required = True
    proposal = _valid_proposal()
    proposal.strategy_license_id = "license-abc-123"
    result = check(policy, proposal)
    assert result.is_allowed()


def test_gate_is_deterministic():
    policy = _default_policy()
    proposal = _valid_proposal()
    r1 = check(policy, proposal)
    r2 = check(policy, proposal)
    assert r1.decision == r2.decision
    assert r1.passed == r2.passed
    assert r1.failed == r2.failed
