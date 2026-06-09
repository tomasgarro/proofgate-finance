"""
DefiLlama ingestion layer.

Free API, no key required. Covers TVL, fees, revenue, and token unlock schedules
for most major DeFi protocols.

Usage:
    from src.ingestion.defillama import get_protocol_metrics, get_token_unlocks
    metrics = get_protocol_metrics("aave")
    unlocks = get_token_unlocks("arbitrum")
"""

import json
from dataclasses import dataclass, field
from typing import Optional
from urllib.request import urlopen, Request

_BASE = "https://api.llama.fi"
_COINS_BASE = "https://coins.llama.fi"
_TIMEOUT = 10


@dataclass
class ProtocolMetrics:
    """Core financial metrics for a DeFi protocol."""
    name: str
    slug: str
    tvl: float                 # total value locked in USD
    tvl_change_1d: float       # % change
    tvl_change_7d: float
    fees_24h: float            # gross fees paid by users (last 24h)
    revenue_24h: float         # fees kept by the protocol
    fees_7d: float
    revenue_7d: float
    fees_30d: float
    revenue_30d: float
    category: str
    chains: list[str] = field(default_factory=list)
    # Derived: earnings quality proxy (like Sloan, but for DeFi)
    # "emissions" = tokens minted to incentivize users (hidden cost)
    emissions_30d: float = 0.0

    def p_s_ratio_proxy(self, market_cap: float) -> Optional[float]:
        """Price-to-sales proxy using 30d fees annualized."""
        if self.fees_30d <= 0:
            return None
        annualized_fees = self.fees_30d * 12
        return market_cap / annualized_fees if annualized_fees > 0 else None

    def summary(self) -> str:
        lines = [
            f"Protocol: {self.name} ({self.slug})",
            f"  TVL: ${self.tvl:,.0f}  [1d: {self.tvl_change_1d:+.1f}%  7d: {self.tvl_change_7d:+.1f}%]",
            f"  Fees 24h: ${self.fees_24h:,.0f}   Revenue 24h: ${self.revenue_24h:,.0f}",
            f"  Fees 30d: ${self.fees_30d:,.0f}   Revenue 30d: ${self.revenue_30d:,.0f}",
        ]
        if self.emissions_30d > 0:
            net = self.revenue_30d - self.emissions_30d
            lines.append(f"  Emissions 30d: ${self.emissions_30d:,.0f}  Net earnings: ${net:,.0f}")
        return "\n".join(lines)


@dataclass
class UnlockEvent:
    date: str       # ISO date
    amount: float   # tokens unlocked
    amount_usd: float
    pct_of_circulating: float  # key flag: > 5% is a red flag
    recipient: str  # "team", "investors", "ecosystem", etc.
    cliff: bool     # True if this is a single large event (not linear)


@dataclass
class TokenUnlockProfile:
    token: str
    upcoming_events: list[UnlockEvent] = field(default_factory=list)
    largest_cliff_pct: float = 0.0   # largest single unlock as % of circulating
    has_cliff_risk: bool = False      # any single unlock > 5% of circulating
    flag: str = "CLEAN"              # "CLIFF_RISK" | "WATCH" | "CLEAN"
    note: str = ""

    def summary(self) -> str:
        lines = [f"Token Unlock Profile: {self.token}  [{self.flag}]"]
        if self.note:
            lines.append(f"  {self.note}")
        for ev in self.upcoming_events[:5]:
            cliff_tag = " [CLIFF]" if ev.cliff else ""
            lines.append(
                f"  {ev.date}  {ev.amount_usd:,.0f} USD  "
                f"({ev.pct_of_circulating:.1f}% of circulating){cliff_tag}  → {ev.recipient}"
            )
        return "\n".join(lines)


def get_protocol_metrics(slug: str) -> ProtocolMetrics:
    """
    Fetch TVL, fees, and revenue for a DeFi protocol by its DeFiLlama slug.

    Find slugs at https://defillama.com/docs/api
    Examples: "aave", "uniswap", "compound", "maker", "lido"
    """
    protocol_data = _fetch(f"{_BASE}/protocol/{slug}")
    fees_data = _fetch_safe(f"{_BASE}/summary/fees/{slug}?dataType=dailyFees")
    revenue_data = _fetch_safe(f"{_BASE}/summary/fees/{slug}?dataType=dailyRevenue")

    name = protocol_data.get("name", slug)
    tvl = protocol_data.get("tvl", 0.0) or 0.0
    tvl_change_1d = protocol_data.get("change_1d", 0.0) or 0.0
    tvl_change_7d = protocol_data.get("change_7d", 0.0) or 0.0
    chains = list(protocol_data.get("chains", []))
    category = protocol_data.get("category", "")

    fees_24h = _extract_metric(fees_data, "total24h")
    fees_7d = _extract_metric(fees_data, "total7d")
    fees_30d = _extract_metric(fees_data, "total30d")
    revenue_24h = _extract_metric(revenue_data, "total24h")
    revenue_7d = _extract_metric(revenue_data, "total7d")
    revenue_30d = _extract_metric(revenue_data, "total30d")

    return ProtocolMetrics(
        name=name, slug=slug,
        tvl=tvl, tvl_change_1d=tvl_change_1d, tvl_change_7d=tvl_change_7d,
        fees_24h=fees_24h, fees_7d=fees_7d, fees_30d=fees_30d,
        revenue_24h=revenue_24h, revenue_7d=revenue_7d, revenue_30d=revenue_30d,
        category=category, chains=chains,
    )


def get_protocol_list(limit: int = 100) -> list[dict]:
    """
    Return top DeFi protocols by TVL with basic metrics.
    Useful for building a universe to screen.
    """
    data = _fetch(f"{_BASE}/protocols")
    protocols = []
    for p in data[:limit]:
        protocols.append({
            "name": p.get("name"),
            "slug": p.get("slug"),
            "tvl": p.get("tvl", 0),
            "category": p.get("category"),
            "chains": p.get("chains", []),
        })
    return protocols


def get_token_unlocks(token_slug: str) -> TokenUnlockProfile:
    """
    Fetch token unlock schedule from DefiLlama's tokenomist data.

    Note: DefiLlama acquired Tokenomist. Unlock data availability varies by token.
    For tokens not covered, returns a profile with flag=UNKNOWN.

    token_slug examples: "arbitrum", "optimism", "aptos", "sui"
    """
    data = _fetch_safe(f"{_BASE}/unlocks/{token_slug}")
    if not data or "error" in data:
        return TokenUnlockProfile(
            token=token_slug,
            flag="UNKNOWN",
            note="Unlock data not available for this token via DefiLlama.",
        )

    events = []
    max_pct = 0.0

    for event in data.get("events", []):
        pct = float(event.get("noOfTokens", [0, 0])[1] or 0)  # rough proxy
        amount_usd = float(event.get("dollarValue", 0) or 0)
        amount = float(event.get("noOfTokens", [0])[0] or 0)
        cliff = event.get("type", "").lower() in ("cliff", "unlock")
        recipient = event.get("description", "unknown")
        date = event.get("timestamp", "")

        ev = UnlockEvent(
            date=date, amount=amount, amount_usd=amount_usd,
            pct_of_circulating=pct, recipient=recipient, cliff=cliff,
        )
        events.append(ev)
        max_pct = max(max_pct, pct)

    has_cliff_risk = max_pct > 5.0
    flag = "CLIFF_RISK" if max_pct > 10.0 else ("WATCH" if max_pct > 5.0 else "CLEAN")
    note = (
        f"Largest upcoming unlock: {max_pct:.1f}% of circulating supply."
        if events else "No upcoming unlock events found."
    )

    return TokenUnlockProfile(
        token=token_slug,
        upcoming_events=sorted(events, key=lambda e: e.date)[:10],
        largest_cliff_pct=max_pct,
        has_cliff_risk=has_cliff_risk,
        flag=flag,
        note=note,
    )


def _fetch(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "ProofGate Finance research@proofgatefinance.com"})
    with urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read())


def _fetch_safe(url: str) -> dict:
    try:
        return _fetch(url)
    except Exception:
        return {}


def _extract_metric(data: dict, key: str) -> float:
    if not data:
        return 0.0
    val = data.get(key) or data.get("data", {}).get(key, 0)
    return float(val) if val is not None else 0.0
