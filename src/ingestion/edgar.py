"""
EDGAR ingestion via edgartools 5.x.

Fetches two consecutive 10-K fiscal years for a company and maps their financial
statement line items to the input dataclasses used by our metrics engine.
"""

import os
import re
from dataclasses import dataclass
from typing import Optional


# Only columns that start with a 4-digit year are actual period columns.
# All other columns (concept, label, dimension, is_breakdown, etc.) are metadata.
_DATE_COL = re.compile(r"^\d{4}-\d{2}-\d{2}")


@dataclass
class YearData:
    """Financial line items for a single fiscal year, normalized for metric inputs."""
    ticker: str
    period: str
    sales: float
    cogs: float
    sga: float
    net_income: float
    ebit: float
    operating_cash_flow: float
    investing_cash_flow: float
    depreciation: float
    receivables: float
    current_assets: float
    current_liabilities: float
    ppe_net: float
    total_assets: float
    total_liabilities: float
    long_term_debt: float
    retained_earnings: float
    market_cap: float
    shares_outstanding: float


def set_edgar_identity(identity: str) -> None:
    try:
        from edgar import set_identity
        set_identity(identity)
    except ImportError:
        raise ImportError("edgartools is required: pip install edgartools")


def load_company_years(ticker: str) -> tuple[YearData, YearData]:
    """
    Load the two most recent fiscal years for a ticker from SEC EDGAR.
    Returns (current_year, prior_year) as YearData objects.
    """
    identity = os.environ.get("SEC_IDENTITY")
    if not identity:
        raise EnvironmentError("User-Agent identity is not set. Add SEC_IDENTITY to your .env file.")
    set_edgar_identity(identity)

    try:
        from edgar import Company
    except ImportError:
        raise ImportError("edgartools is required: pip install edgartools")

    company = Company(ticker)
    fin = company.get_financials()

    inc_df, inc_periods = _stmt_df(fin, "income_statement")
    bal_df, bal_periods = _stmt_df(fin, "balance_sheet")
    cfs_df, cfs_periods = _stmt_df(fin, "cash_flow_statement")

    current = _extract_year(ticker, inc_df, bal_df, cfs_df,
                            inc_periods, bal_periods, cfs_periods, period=0)
    prior = _extract_year(ticker, inc_df, bal_df, cfs_df,
                          inc_periods, bal_periods, cfs_periods, period=1)
    return current, prior


# ── Statement helpers ─────────────────────────────────────────────────────────

def _stmt_df(fin, method_name: str):
    """Call a Statement method and return (DataFrame, [period_col_names])."""
    method = getattr(fin, method_name, None)
    if not callable(method):
        return None, []
    try:
        stmt = method()
        if hasattr(stmt, "to_dataframe"):
            df = stmt.to_dataframe()
            # Only columns matching YYYY-MM-DD... are real period columns
            period_cols = [c for c in df.columns if _DATE_COL.match(str(c))]
            return df, period_cols
    except Exception:
        pass
    return None, []


def _extract_year(ticker, inc_df, bal_df, cfs_df,
                  inc_periods, bal_periods, cfs_periods, period: int) -> YearData:

    def gi(*aliases): return _get(inc_df, inc_periods, period, *aliases)
    def gb(*aliases): return _get(bal_df, bal_periods, period, *aliases)
    def gc(*aliases): return _get(cfs_df, cfs_periods, period, *aliases)

    label = _year_label(inc_periods, period)

    sales = gi(
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomer",
        "Net sales", "Total net revenue", "Revenue",
    )
    cogs = gi(
        "CostOfGoodsAndServicesSold", "CostOfRevenue",
        "CostOfGoodsSold", "CostOfSales",
        "Cost of sales", "Cost of revenue",
    )
    sga = gi(
        "SellingGeneralAndAdministrativeExpense",
        "SellingAndMarketingExpense", "GeneralAndAdministrativeExpense",
        "Selling, general and administrative",
    )
    net_income = gi(
        "NetIncomeLoss", "NetIncome", "ProfitLoss",
        "Net income",
    )
    ebit = gi(
        "OperatingIncomeLoss",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "Operating income",
    )
    operating_cash_flow = gc(
        "NetCashProvidedByUsedInOperatingActivities",
        "CashGeneratedFromOperations",
        "Operating activities",
    )
    investing_cash_flow = gc(
        "NetCashProvidedByUsedInInvestingActivities",
        "CashUsedInInvestingActivities",
        "Investing activities",
    )
    depreciation = gc(
        "DepreciationDepletionAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "Depreciation and amortization", "Depreciation",
    )
    receivables = gb(
        "AccountsReceivableNetCurrent", "ReceivablesNetCurrent",
        "Accounts receivable, net", "Accounts receivable",
    )
    current_assets = gb(
        "AssetsCurrent", "Total current assets",
    )
    current_liabilities = gb(
        "LiabilitiesCurrent", "Total current liabilities",
    )
    ppe_net = gb(
        "PropertyPlantAndEquipmentNet", "PropertyAndEquipmentNet",
        "Property, plant and equipment, net",
        "Property and equipment, net",
    )
    total_assets = gb(
        "Assets", "Total assets",
    )
    total_liabilities = gb(
        "Liabilities", "Total liabilities",
    )
    long_term_debt = gb(
        "LongTermDebtNoncurrent", "LongTermDebt",
        "LongTermDebtAndCapitalLeaseObligations",
        "Term debt, non-current", "Long-term debt",
    )
    retained_earnings = gb(
        "RetainedEarningsAccumulatedDeficit", "RetainedEarnings",
        "Retained earnings",
    )
    shares = gb(
        "CommonStockSharesOutstanding", "SharesOutstanding",
        "Common shares outstanding",
    )

    return YearData(
        ticker=ticker,
        period=label,
        sales=sales, cogs=cogs, sga=sga,
        net_income=net_income, ebit=ebit,
        operating_cash_flow=operating_cash_flow,
        investing_cash_flow=investing_cash_flow,
        depreciation=depreciation,
        receivables=receivables,
        current_assets=current_assets,
        current_liabilities=current_liabilities,
        ppe_net=ppe_net,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        long_term_debt=long_term_debt,
        retained_earnings=retained_earnings,
        market_cap=0.0,
        shares_outstanding=shares,
    )


def _get(df, period_cols: list, period: int, *aliases) -> float:
    """
    Look up a value in a statement DataFrame by concept/label aliases.

    Concepts are stored with namespace prefixes like 'us-gaap_NetIncomeLoss'.
    We strip the prefix before matching so callers can use bare XBRL names.
    We also iterate through ALL matching rows (not just the first) to skip NaN
    header/abstract rows and find the first row with an actual value.
    """
    if df is None or not period_cols or period >= len(period_cols):
        return 0.0
    col = period_cols[period]

    # Pre-compute a prefix-stripped version of the concept column once
    stripped_concept = None
    if "concept" in df.columns:
        stripped_concept = df["concept"].str.replace(r"^[^_]+_", "", regex=True)

    for alias in aliases:
        # 1. Exact match on stripped concept (e.g. "NetCashProvidedByUsedInOperatingActivities")
        if stripped_concept is not None:
            mask = stripped_concept == alias
            if mask.any():
                for idx in mask[mask].index:
                    val = _coerce(df.loc[idx, col])
                    if val != 0.0:
                        return val

        # 2. Substring match on original concept / standard_concept / label
        for search_col in ("concept", "standard_concept", "label"):
            if search_col not in df.columns:
                continue
            try:
                mask = df[search_col].str.contains(alias, case=False, na=False, regex=False)
                if mask.any():
                    for idx in mask[mask].index:
                        val = _coerce(df.loc[idx, col])
                        if val != 0.0:
                            return val
            except Exception:
                pass

    return 0.0


def _coerce(val) -> float:
    """Convert a raw cell value to float, returning 0.0 on failure or NaN."""
    if val is None:
        return 0.0
    try:
        if isinstance(val, (int, float)):
            f = float(val)
            return 0.0 if f != f else f  # NaN → 0
        s = str(val).replace(",", "").replace("$", "").strip()
        return 0.0 if s in ("", "nan", "None", "NaN", "-", "—") else float(s)
    except Exception:
        return 0.0


def _year_label(period_cols: list, period: int) -> str:
    """Extract 4-digit year from a column name like '2024-09-28 (FY)'."""
    if not period_cols or period >= len(period_cols):
        return str(period)
    m = re.search(r"(\d{4})", period_cols[period])
    return m.group(1) if m else period_cols[period]


# ── Adapter functions — convert YearData to metric input objects ───────────────

def year_data_to_beneish_inputs(current: YearData, prior: YearData):
    from src.metrics.beneish import BeneishInputs
    return BeneishInputs(
        net_receivables_t=current.receivables, sales_t=current.sales, cogs_t=current.cogs,
        current_assets_t=current.current_assets, ppe_net_t=current.ppe_net,
        total_assets_t=current.total_assets, depreciation_t=current.depreciation,
        sga_expense_t=current.sga, long_term_debt_t=current.long_term_debt,
        current_liabilities_t=current.current_liabilities, net_income_t=current.net_income,
        operating_cash_flow_t=current.operating_cash_flow,
        net_receivables_t1=prior.receivables, sales_t1=prior.sales, cogs_t1=prior.cogs,
        current_assets_t1=prior.current_assets, ppe_net_t1=prior.ppe_net,
        total_assets_t1=prior.total_assets, depreciation_t1=prior.depreciation,
        sga_expense_t1=prior.sga, long_term_debt_t1=prior.long_term_debt,
        current_liabilities_t1=prior.current_liabilities,
    )


def year_data_to_altman_inputs(current: YearData):
    from src.metrics.altman import AltmanInputs
    return AltmanInputs(
        working_capital=current.current_assets - current.current_liabilities,
        total_assets=current.total_assets,
        retained_earnings=current.retained_earnings,
        ebit=current.ebit,
        market_cap=current.market_cap,
        total_liabilities=current.total_liabilities,
        sales=current.sales,
    )


def year_data_to_sloan_inputs(current: YearData, prior: YearData):
    from src.metrics.sloan import SloanInputs
    return SloanInputs(
        net_income=current.net_income,
        cash_flow_from_operations=current.operating_cash_flow,
        cash_flow_from_investing=current.investing_cash_flow,
        total_assets_current=current.total_assets,
        total_assets_prior=prior.total_assets,
    )


def year_data_to_piotroski_inputs(current: YearData, prior: YearData):
    from src.metrics.piotroski import PiotroskiInputs
    return PiotroskiInputs(
        net_income=current.net_income,
        operating_cash_flow=current.operating_cash_flow,
        total_assets=current.total_assets,
        total_assets_prior=prior.total_assets,
        total_debt=current.long_term_debt,
        total_debt_prior=prior.long_term_debt,
        current_assets=current.current_assets,
        current_liabilities=current.current_liabilities,
        current_assets_prior=prior.current_assets,
        current_liabilities_prior=prior.current_liabilities,
        common_stock_issued=max(0.0, current.shares_outstanding - prior.shares_outstanding),
        revenue=current.sales,
        revenue_prior=prior.sales,
        cogs=current.cogs,
        cogs_prior=prior.cogs,
    )
