"""Beneish M-Score: earnings manipulation probability model."""

from dataclasses import dataclass


@dataclass
class BeneishInputs:
    # Current period (t)
    net_receivables_t: float
    sales_t: float
    cogs_t: float
    current_assets_t: float
    ppe_net_t: float
    total_assets_t: float
    depreciation_t: float
    sga_expense_t: float
    long_term_debt_t: float
    current_liabilities_t: float
    net_income_t: float
    operating_cash_flow_t: float

    # Prior period (t-1)
    net_receivables_t1: float
    sales_t1: float
    cogs_t1: float
    current_assets_t1: float
    ppe_net_t1: float
    total_assets_t1: float
    depreciation_t1: float
    sga_expense_t1: float
    long_term_debt_t1: float
    current_liabilities_t1: float


@dataclass
class BeneishResult:
    m_score: float
    dsri: float   # Days Sales Receivable Index
    gmi: float    # Gross Margin Index
    aqi: float    # Asset Quality Index
    sgi: float    # Sales Growth Index
    depi: float   # Depreciation Index
    sgai: float   # SGA Expense Index
    tata: float   # Total Accruals to Total Assets
    lvgi: float   # Leverage Index
    flag: str     # "MANIPULATION_RISK" | "CLEAN" | "BORDERLINE"

    def summary(self) -> str:
        lines = [
            f"Beneish M-Score: {self.m_score:.4f}  [{self.flag}]",
            f"  DSRI  (receivables vs sales trend):   {self.dsri:.4f}",
            f"  GMI   (gross margin deterioration):   {self.gmi:.4f}",
            f"  AQI   (asset quality decline):         {self.aqi:.4f}",
            f"  SGI   (sales growth):                  {self.sgi:.4f}",
            f"  DEPI  (depreciation slowdown):         {self.depi:.4f}",
            f"  SGAI  (SGA expense growth):            {self.sgai:.4f}",
            f"  TATA  (accruals vs cash income):       {self.tata:.4f}",
            f"  LVGI  (leverage increase):             {self.lvgi:.4f}",
        ]
        return "\n".join(lines)


_THRESHOLD = -2.22
_BORDERLINE_LOW = -2.49


def calculate(inputs: BeneishInputs) -> BeneishResult:
    """
    Calculate Beneish M-Score from two consecutive periods of financial data.

    M > -2.22: likely manipulation (flag MANIPULATION_RISK)
    -2.49 <= M <= -2.22: borderline (flag BORDERLINE)
    M < -2.49: likely clean (flag CLEAN)

    Reference: Beneish, M.D. (1999). The Detection of Earnings Manipulation.
    """
    # DSRI: rising receivables relative to sales is a manipulation signal
    dsri = _safe_div(
        inputs.net_receivables_t / inputs.sales_t,
        inputs.net_receivables_t1 / inputs.sales_t1,
    )

    # GMI: declining gross margin may pressure manipulation
    gross_margin_t = (inputs.sales_t - inputs.cogs_t) / inputs.sales_t
    gross_margin_t1 = (inputs.sales_t1 - inputs.cogs_t1) / inputs.sales_t1
    gmi = _safe_div(gross_margin_t1, gross_margin_t)

    # AQI: growth in long-term non-productive assets relative to total assets
    quality_t = 1 - (inputs.current_assets_t + inputs.ppe_net_t) / inputs.total_assets_t
    quality_t1 = 1 - (inputs.current_assets_t1 + inputs.ppe_net_t1) / inputs.total_assets_t1
    aqi = _safe_div(quality_t, quality_t1)

    # SGI: fast sales growth creates pressure that may drive manipulation
    sgi = _safe_div(inputs.sales_t, inputs.sales_t1)

    # DEPI: declining depreciation rate may signal upward manipulation of assets
    dep_rate_t = inputs.depreciation_t / (inputs.depreciation_t + inputs.ppe_net_t)
    dep_rate_t1 = inputs.depreciation_t1 / (inputs.depreciation_t1 + inputs.ppe_net_t1)
    depi = _safe_div(dep_rate_t1, dep_rate_t)

    # SGAI: rising SGA as fraction of sales
    sgai = _safe_div(
        inputs.sga_expense_t / inputs.sales_t,
        inputs.sga_expense_t1 / inputs.sales_t1,
    )

    # TATA: high total accruals relative to assets indicate earnings exceeding cash
    tata = (inputs.net_income_t - inputs.operating_cash_flow_t) / inputs.total_assets_t

    # LVGI: increasing leverage may create pressure to manipulate
    leverage_t = (inputs.long_term_debt_t + inputs.current_liabilities_t) / inputs.total_assets_t
    leverage_t1 = (inputs.long_term_debt_t1 + inputs.current_liabilities_t1) / inputs.total_assets_t1
    lvgi = _safe_div(leverage_t, leverage_t1)

    m_score = (
        -4.84
        + 0.920 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )

    if m_score > _THRESHOLD:
        flag = "MANIPULATION_RISK"
    elif m_score >= _BORDERLINE_LOW:
        flag = "BORDERLINE"
    else:
        flag = "CLEAN"

    return BeneishResult(
        m_score=m_score,
        dsri=dsri,
        gmi=gmi,
        aqi=aqi,
        sgi=sgi,
        depi=depi,
        sgai=sgai,
        tata=tata,
        lvgi=lvgi,
        flag=flag,
    )


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
