"""
Crypto token risk flags: unlock schedule and holder concentration screening.

These are the on-chain equivalents of forensic accounting scores:
- Unlock cliff risk = like a Sloan accruals flag (hidden future supply pressure)
- Holder concentration = like insider ownership risk in equities

These are probability flags, not proof of manipulation or bad outcomes.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CryptoRiskInputs:
    token: str
    # Unlock data
    largest_cliff_pct: float        # largest single unlock as % of circulating supply
    upcoming_cliff_usd: float       # USD value of largest upcoming cliff unlock
    circulating_supply: float
    total_supply: float
    # Holder data
    top10_holder_pct: float         # % of supply held by top 10 wallets
    team_investor_pct: float        # % held by team/investor wallets (labeled)
    # Protocol health (from DefiLlama)
    fees_30d: float
    revenue_30d: float
    emissions_30d: float            # token incentives printed to users
    tvl: float


@dataclass
class CryptoRiskResult:
    token: str
    flags: list[str] = field(default_factory=list)
    green_flags: list[str] = field(default_factory=list)
    overall_flag: str = "CLEAN"  # "HIGH_RISK" | "ELEVATED" | "WATCH" | "CLEAN"

    def summary(self) -> str:
        lines = [f"Crypto Risk: {self.token}  [{self.overall_flag}]"]
        if self.flags:
            lines.append("  Red flags:")
            for f in self.flags:
                lines.append(f"    - {f}")
        if self.green_flags:
            lines.append("  Green flags:")
            for g in self.green_flags:
                lines.append(f"    + {g}")
        return "\n".join(lines)


def calculate(inputs: CryptoRiskInputs) -> CryptoRiskResult:
    """
    Run crypto risk screening across unlock, concentration, and protocol health dimensions.

    Rules of thumb from the article:
    - Any single unlock > 5% of circulating supply is a red flag
    - Cliff unlock into team/VC wallet is highest risk
    - Top-10 holder concentration > 50% warrants scrutiny
    - Protocol burning emissions (revenue > fees × 0.5) shows real demand vs incentives
    """
    flags = []
    green_flags = []

    # Unlock risk
    if inputs.largest_cliff_pct > 10.0:
        flags.append(
            f"Cliff unlock {inputs.largest_cliff_pct:.1f}% of circulating supply — "
            f"${inputs.upcoming_cliff_usd:,.0f} USD — HIGH risk of sell pressure"
        )
    elif inputs.largest_cliff_pct > 5.0:
        flags.append(
            f"Cliff unlock {inputs.largest_cliff_pct:.1f}% of circulating supply — "
            f"watch the unlock date, known early holders can exit into retail"
        )
    else:
        green_flags.append(f"No single unlock exceeds 5% of circulating supply")

    # Supply concentration
    float_ratio = inputs.circulating_supply / inputs.total_supply if inputs.total_supply > 0 else 1.0
    if float_ratio < 0.15:
        flags.append(
            f"Only {float_ratio * 100:.0f}% of total supply is circulating — "
            f"massive future dilution potential"
        )
    elif float_ratio > 0.8:
        green_flags.append(f"{float_ratio * 100:.0f}% of supply is already circulating — low dilution risk")

    # Holder concentration
    if inputs.top10_holder_pct > 80.0:
        flags.append(
            f"Top 10 wallets hold {inputs.top10_holder_pct:.0f}% of supply — "
            f"extreme concentration, retail is exit liquidity"
        )
    elif inputs.top10_holder_pct > 50.0:
        flags.append(
            f"Top 10 wallets hold {inputs.top10_holder_pct:.0f}% of supply — elevated concentration"
        )
    else:
        green_flags.append(f"Top 10 holder concentration is {inputs.top10_holder_pct:.0f}% — reasonable distribution")

    if inputs.team_investor_pct > 40.0:
        flags.append(
            f"Team/investor wallets hold {inputs.team_investor_pct:.0f}% of supply — "
            f"significant insider concentration"
        )

    # Protocol earnings quality (crypto version of Sloan)
    if inputs.fees_30d > 0 and inputs.emissions_30d > inputs.revenue_30d:
        flags.append(
            f"Emissions (${inputs.emissions_30d:,.0f}/30d) exceed protocol revenue "
            f"(${inputs.revenue_30d:,.0f}/30d) — paying users with printed tokens, "
            f"not organic demand"
        )
    elif inputs.revenue_30d > 0 and inputs.emissions_30d == 0:
        green_flags.append(
            f"Protocol revenue ${inputs.revenue_30d:,.0f}/30d with zero token emissions — "
            f"organic demand indicator"
        )

    # TVL sanity
    if inputs.tvl > 0 and inputs.fees_30d > 0:
        fee_tvl_ratio = inputs.fees_30d / inputs.tvl
        if fee_tvl_ratio < 0.0001:
            flags.append(
                f"Fee/TVL ratio is very low ({fee_tvl_ratio * 100:.3f}%) — "
                f"TVL may be inflated by emissions or is not being utilized"
            )

    flag_count = len(flags)
    if flag_count >= 3:
        overall = "HIGH_RISK"
    elif flag_count >= 2:
        overall = "ELEVATED"
    elif flag_count >= 1:
        overall = "WATCH"
    else:
        overall = "CLEAN"

    return CryptoRiskResult(
        token=inputs.token,
        flags=flags,
        green_flags=green_flags,
        overall_flag=overall,
    )
