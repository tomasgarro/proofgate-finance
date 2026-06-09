"""Altman Z-Score wrapper around FinanceToolkit, with standalone fallback."""

from dataclasses import dataclass


@dataclass
class AltmanInputs:
    working_capital: float        # current assets - current liabilities
    total_assets: float
    retained_earnings: float
    ebit: float                   # earnings before interest and taxes
    market_cap: float             # market value of equity
    total_liabilities: float
    sales: float


@dataclass
class AltmanResult:
    z_score: float
    x1: float  # working capital / total assets
    x2: float  # retained earnings / total assets
    x3: float  # EBIT / total assets
    x4: float  # market cap / total liabilities
    x5: float  # sales / total assets
    zone: str  # "SAFE" | "GREY" | "DISTRESS"

    def summary(self) -> str:
        return (
            f"Altman Z-Score: {self.z_score:.4f}  [{self.zone}]\n"
            f"  X1 (working capital / assets):     {self.x1:.4f}\n"
            f"  X2 (retained earnings / assets):   {self.x2:.4f}\n"
            f"  X3 (EBIT / assets):                {self.x3:.4f}\n"
            f"  X4 (market cap / liabilities):     {self.x4:.4f}\n"
            f"  X5 (sales / assets):               {self.x5:.4f}"
        )


_SAFE_THRESHOLD = 2.99
_DISTRESS_THRESHOLD = 1.81


def calculate(inputs: AltmanInputs) -> AltmanResult:
    """
    Calculate the Altman Z-Score for public manufacturing companies.

    Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5

    Zones:
      Z > 2.99: Safe zone (low bankruptcy risk)
      1.81 <= Z <= 2.99: Grey zone (uncertainty)
      Z < 1.81: Distress zone (elevated bankruptcy risk)

    Reference: Altman, E.I. (1968). Financial Ratios, Discriminant Analysis
    and the Prediction of Corporate Bankruptcy. Journal of Finance, 23(4).
    """
    if inputs.total_assets == 0:
        return AltmanResult(z_score=0.0, x1=0.0, x2=0.0, x3=0.0, x4=0.0, x5=0.0, zone="DISTRESS")

    x1 = inputs.working_capital / inputs.total_assets
    x2 = inputs.retained_earnings / inputs.total_assets
    x3 = inputs.ebit / inputs.total_assets
    x4 = inputs.market_cap / inputs.total_liabilities if inputs.total_liabilities != 0 else 0.0
    x5 = inputs.sales / inputs.total_assets

    z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

    if z_score > _SAFE_THRESHOLD:
        zone = "SAFE"
    elif z_score >= _DISTRESS_THRESHOLD:
        zone = "GREY"
    else:
        zone = "DISTRESS"

    return AltmanResult(z_score=z_score, x1=x1, x2=x2, x3=x3, x4=x4, x5=x5, zone=zone)
