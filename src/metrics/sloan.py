"""Sloan Accruals Ratio: earnings quality metric."""

from dataclasses import dataclass


@dataclass
class SloanInputs:
    net_income: float
    cash_flow_from_operations: float
    cash_flow_from_investing: float
    total_assets_current: float
    total_assets_prior: float


@dataclass
class SloanResult:
    accruals_ratio: float
    accruals_amount: float
    average_total_assets: float
    flag: str  # "ELEVATED" | "MODERATE" | "CLEAN"

    def summary(self) -> str:
        return (
            f"Sloan Accruals Ratio: {self.accruals_ratio * 100:.2f}%  [{self.flag}]\n"
            f"  Accruals amount: {self.accruals_amount:,.0f}\n"
            f"  Average total assets: {self.average_total_assets:,.0f}"
        )


_ELEVATED_THRESHOLD = 0.05   # above 5% is elevated
_MODERATE_THRESHOLD = 0.02   # above 2% is moderate


def calculate(inputs: SloanInputs) -> SloanResult:
    """
    Calculate the Sloan Accruals Ratio.

    Formula: (Net Income - Cash Flow from Operations - Cash Flow from Investing)
             / Average Total Assets

    High positive values indicate that reported earnings exceed cash-based earnings,
    which historically predicts lower future returns (Sloan, 1996).

    Reference: Sloan, R.G. (1996). Do Stock Prices Fully Reflect Information in
    Accruals and Cash Flows About Future Earnings? The Accounting Review, 71(3).
    """
    average_total_assets = (inputs.total_assets_current + inputs.total_assets_prior) / 2

    if average_total_assets == 0:
        return SloanResult(
            accruals_ratio=0.0,
            accruals_amount=0.0,
            average_total_assets=0.0,
            flag="CLEAN",
        )

    accruals = inputs.net_income - inputs.cash_flow_from_operations - inputs.cash_flow_from_investing
    ratio = accruals / average_total_assets

    if ratio > _ELEVATED_THRESHOLD:
        flag = "ELEVATED"
    elif ratio > _MODERATE_THRESHOLD:
        flag = "MODERATE"
    else:
        flag = "CLEAN"

    return SloanResult(
        accruals_ratio=ratio,
        accruals_amount=accruals,
        average_total_assets=average_total_assets,
        flag=flag,
    )
