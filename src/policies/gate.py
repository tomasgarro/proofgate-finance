"""Deterministic policy gate: check trade proposals against user-defined constraints."""

import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Policy:
    version: str = "1.0"
    allowed_assets: list[str] = field(default_factory=list)
    blocked_assets: list[str] = field(default_factory=list)
    max_position_pct: float = 100.0
    max_daily_loss_pct: float = 100.0
    max_drawdown_pct: float = 100.0
    allow_leverage: bool = True
    max_leverage: float = 1.0
    allowed_venues: list[str] = field(default_factory=lambda: ["simulated"])
    blocked_venues: list[str] = field(default_factory=list)
    requires_user_approval: bool = False
    strategy_license_required: bool = False

    @classmethod
    def from_json(cls, path: str) -> "Policy":
        with open(path) as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_dict(cls, data: dict) -> "Policy":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "allowed_assets": self.allowed_assets,
            "blocked_assets": self.blocked_assets,
            "max_position_pct": self.max_position_pct,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "allow_leverage": self.allow_leverage,
            "max_leverage": self.max_leverage,
            "allowed_venues": self.allowed_venues,
            "blocked_venues": self.blocked_venues,
            "requires_user_approval": self.requires_user_approval,
            "strategy_license_required": self.strategy_license_required,
        }


@dataclass
class Proposal:
    asset: str
    action: str            # "buy" | "sell" | "hold"
    position_pct: float
    venue: str
    leverage: float = 1.0
    rationale: str = ""
    strategy_license_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Proposal":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_dict(self) -> dict:
        return {
            "asset": self.asset,
            "action": self.action,
            "position_pct": self.position_pct,
            "venue": self.venue,
            "leverage": self.leverage,
            "rationale": self.rationale,
            "strategy_license_id": self.strategy_license_id,
        }


@dataclass
class GateResult:
    decision: str                    # "allow" | "reject"
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def is_allowed(self) -> bool:
        return self.decision == "allow"

    def summary(self) -> str:
        lines = [f"Decision: {self.decision.upper()}"]
        if self.passed:
            lines.append("  Passed constraints:")
            for c in self.passed:
                lines.append(f"    + {c}")
        if self.failed:
            lines.append("  Failed constraints:")
            for c in self.failed:
                lines.append(f"    - {c}")
        return "\n".join(lines)


def check(policy: Policy, proposal: Proposal) -> GateResult:
    """
    Run a trade proposal through the policy gate.

    All checks are deterministic. No LLM or probabilistic logic inside this function.
    Returns a GateResult with every constraint labeled as passed or failed.
    """
    passed = []
    failed = []

    # Asset checks
    if policy.allowed_assets:
        if proposal.asset in policy.allowed_assets:
            passed.append(f"asset_in_allowed_list ({proposal.asset})")
        else:
            failed.append(f"asset_not_in_allowed_list ({proposal.asset})")

    if proposal.asset in policy.blocked_assets:
        failed.append(f"asset_in_blocked_list ({proposal.asset})")
    else:
        passed.append(f"asset_not_blocked ({proposal.asset})")

    # Position size
    if proposal.position_pct <= policy.max_position_pct:
        passed.append(f"position_size_within_limit ({proposal.position_pct}% <= {policy.max_position_pct}%)")
    else:
        failed.append(f"position_size_exceeds_limit ({proposal.position_pct}% > {policy.max_position_pct}%)")

    # Venue checks
    if policy.allowed_venues:
        if proposal.venue in policy.allowed_venues:
            passed.append(f"venue_allowed ({proposal.venue})")
        else:
            failed.append(f"venue_not_allowed ({proposal.venue})")

    if proposal.venue in policy.blocked_venues:
        failed.append(f"venue_blocked ({proposal.venue})")

    # Leverage
    if not policy.allow_leverage and proposal.leverage > 1.0:
        failed.append(f"leverage_not_allowed ({proposal.leverage}x)")
    elif proposal.leverage > policy.max_leverage:
        failed.append(f"leverage_exceeds_max ({proposal.leverage}x > {policy.max_leverage}x)")
    else:
        passed.append(f"leverage_within_limit ({proposal.leverage}x)")

    # Strategy license
    if policy.strategy_license_required and not proposal.strategy_license_id:
        failed.append("strategy_license_required_but_not_provided")
    elif policy.strategy_license_required:
        passed.append(f"strategy_license_present ({proposal.strategy_license_id})")

    # User approval flag (recorded, not enforced by gate itself)
    if policy.requires_user_approval:
        passed.append("user_approval_required_noted")

    decision = "allow" if not failed else "reject"
    return GateResult(decision=decision, passed=passed, failed=failed)
