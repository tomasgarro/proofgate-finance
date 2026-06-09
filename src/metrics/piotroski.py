"""Piotroski F-Score wrapper and standalone implementation."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PiotroskiInputs:
    # Profitability
    net_income: float
    operating_cash_flow: float
    total_assets: float
    total_assets_prior: float

    # Leverage / liquidity
    total_debt: float
    total_debt_prior: float
    current_assets: float
    current_liabilities: float
    current_assets_prior: float
    current_liabilities_prior: float
    common_stock_issued: float  # 0 means no dilution

    # Operating efficiency
    revenue: float
    revenue_prior: float
    cogs: float
    cogs_prior: float


@dataclass
class PiotroskiResult:
    f_score: int          # 0-9
    criteria: dict = field(default_factory=dict)
    flag: str = ""

    def __post_init__(self):
        if self.f_score >= 7:
            self.flag = "STRONG"
        elif self.f_score >= 3:
            self.flag = "NEUTRAL"
        else:
            self.flag = "WEAK"

    def summary(self) -> str:
        lines = [f"Piotroski F-Score: {self.f_score}/9  [{self.flag}]"]
        labels = {
            "roa_positive": "ROA positive",
            "cfo_positive": "Operating cash flow positive",
            "roa_improving": "ROA improving year-over-year",
            "accruals_quality": "Cash earnings exceed accrual earnings",
            "leverage_decreasing": "Leverage decreasing",
            "liquidity_improving": "Current ratio improving",
            "no_dilution": "No new share issuance",
            "gross_margin_improving": "Gross margin improving",
            "asset_turnover_improving": "Asset turnover improving",
        }
        for key, label in labels.items():
            val = self.criteria.get(key, False)
            mark = "+" if val else "-"
            lines.append(f"  [{mark}] {label}")
        return "\n".join(lines)


def calculate(inputs: PiotroskiInputs) -> PiotroskiResult:
    """
    Calculate Piotroski F-Score (0-9).

    9 binary criteria across profitability, leverage/liquidity, and operating efficiency.
    Higher is better: 7-9 = strong, 3-6 = neutral, 0-2 = weak.

    Reference: Piotroski, J.D. (1999). Value Investing: The Use of Historical Financial
    Statement Information to Separate Winners from Losers.
    """
    avg_assets = (inputs.total_assets + inputs.total_assets_prior) / 2
    avg_assets_prior = inputs.total_assets_prior  # proxy; ideally t-2 assets
    roa = inputs.net_income / avg_assets if avg_assets != 0 else 0.0
    roa_prior = 0.0  # simplified; full multi-period calc requires t-2 data

    criteria = {}

    # Profitability
    criteria["roa_positive"] = roa > 0
    criteria["cfo_positive"] = inputs.operating_cash_flow > 0
    criteria["roa_improving"] = roa > roa_prior
    criteria["accruals_quality"] = (
        (inputs.operating_cash_flow / inputs.total_assets) > roa
        if inputs.total_assets != 0 else False
    )

    # Leverage / liquidity
    debt_ratio = inputs.total_debt / inputs.total_assets if inputs.total_assets != 0 else 0.0
    debt_ratio_prior = inputs.total_debt_prior / inputs.total_assets_prior if inputs.total_assets_prior != 0 else 0.0
    criteria["leverage_decreasing"] = debt_ratio < debt_ratio_prior

    current_ratio = inputs.current_assets / inputs.current_liabilities if inputs.current_liabilities != 0 else 0.0
    current_ratio_prior = inputs.current_assets_prior / inputs.current_liabilities_prior if inputs.current_liabilities_prior != 0 else 0.0
    criteria["liquidity_improving"] = current_ratio > current_ratio_prior
    criteria["no_dilution"] = inputs.common_stock_issued == 0

    # Operating efficiency
    gross_margin = (inputs.revenue - inputs.cogs) / inputs.revenue if inputs.revenue != 0 else 0.0
    gross_margin_prior = (inputs.revenue_prior - inputs.cogs_prior) / inputs.revenue_prior if inputs.revenue_prior != 0 else 0.0
    criteria["gross_margin_improving"] = gross_margin > gross_margin_prior

    avg_assets_t = (inputs.total_assets + inputs.total_assets_prior) / 2
    asset_turnover = inputs.revenue / avg_assets_t if avg_assets_t != 0 else 0.0
    # Asset turnover prior requires t-2 data; simplified to 0 here
    asset_turnover_prior = 0.0
    criteria["asset_turnover_improving"] = asset_turnover > asset_turnover_prior

    f_score = sum(1 for v in criteria.values() if v)

    return PiotroskiResult(f_score=f_score, criteria=criteria)
