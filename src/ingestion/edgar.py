"""
EDGAR ingestion via edgartools.

Fetches two consecutive 10-K filings for a company and maps their financial
statement line items to the input dataclasses used by our metrics engine.

Usage:
    from src.ingestion.edgar import load_company_years, set_edgar_identity
    set_edgar_identity("Your Name your@email.com")
    current, prior = load_company_years("AAPL")
    # current and prior are YearData instances ready for metric calculations
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class YearData:
    """Financial line items for a single fiscal year, normalized for metric inputs."""
    ticker: str
    period: str  # e.g. "2024"
    # Income statement
    sales: float
    cogs: float
    sga: float
    net_income: float
    ebit: float
    # Cash flows
    operating_cash_flow: float
    investing_cash_flow: float
    depreciation: float
    # Balance sheet
    receivables: float
    current_assets: float
    current_liabilities: float
    ppe_net: float
    total_assets: float
    total_liabilities: float
    long_term_debt: float
    retained_earnings: float
    # Market data (may be 0 if unavailable)
    market_cap: float
    shares_outstanding: float


def set_edgar_identity(identity: str) -> None:
    """
    Set the SEC identity string required by EDGAR.
    Format: "Your Name your@email.com"
    The SEC requires this in the User-Agent header.
    """
    try:
        from edgar import set_identity
        set_identity(identity)
    except ImportError:
        raise ImportError("edgartools is required: pip install edgartools")


def load_company_years(ticker: str) -> tuple[YearData, YearData]:
    """
    Load the two most recent fiscal year data for a ticker from SEC EDGAR.

    Returns (current_year, prior_year) as YearData objects.
    Requires SEC_IDENTITY env var or prior call to set_edgar_identity().
    """
    identity = os.environ.get("SEC_IDENTITY")
    if identity:
        set_edgar_identity(identity)

    try:
        from edgar import Company
    except ImportError:
        raise ImportError("edgartools is required: pip install edgartools")

    company = Company(ticker)
    financials = company.get_financials()

    current = _extract_year(ticker, financials, period=0)
    prior = _extract_year(ticker, financials, period=1)
    return current, prior


def _extract_year(ticker: str, financials, period: int) -> YearData:
    """
    Extract a single year's data from a Financials object.

    period=0 means most recent, period=1 means prior year.
    Uses fuzzy label matching with common XBRL tag aliases.
    """
    inc = _get_statement(financials, "income")
    bal = _get_statement(financials, "balance")
    cfs = _get_statement(financials, "cashflow")

    period_label = _get_period_label(inc, period)

    def g(stmt, *aliases) -> float:
        return _get_value(stmt, period, *aliases)

    sales = g(inc,
        "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet", "RevenueFromContractWithCustomer", "Revenue")

    cogs = g(inc,
        "CostOfGoodsAndServicesSold", "CostOfRevenue",
        "CostOfGoodsSold", "CostOfSales")

    sga = g(inc,
        "SellingGeneralAndAdministrativeExpense",
        "SellingAndMarketingExpense", "GeneralAndAdministrativeExpense")

    net_income = g(inc,
        "NetIncomeLoss", "NetIncome", "ProfitLoss")

    ebit = g(inc,
        "OperatingIncomeLoss", "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest")

    operating_cash_flow = g(cfs,
        "NetCashProvidedByUsedInOperatingActivities",
        "CashGeneratedFromOperations")

    investing_cash_flow = g(cfs,
        "NetCashProvidedByUsedInInvestingActivities",
        "CashUsedInInvestingActivities")

    depreciation = g(cfs,
        "DepreciationDepletionAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "Depreciation")

    receivables = g(bal,
        "AccountsReceivableNetCurrent", "ReceivablesNetCurrent",
        "AccountsReceivable")

    current_assets = g(bal,
        "AssetsCurrent", "TotalCurrentAssets")

    current_liabilities = g(bal,
        "LiabilitiesCurrent", "TotalCurrentLiabilities")

    ppe_net = g(bal,
        "PropertyPlantAndEquipmentNet", "PropertyAndEquipmentNet")

    total_assets = g(bal,
        "Assets", "TotalAssets")

    total_liabilities = g(bal,
        "Liabilities", "TotalLiabilities")

    long_term_debt = g(bal,
        "LongTermDebtNoncurrent", "LongTermDebt",
        "LongTermDebtAndCapitalLeaseObligations")

    retained_earnings = g(bal,
        "RetainedEarningsAccumulatedDeficit", "RetainedEarnings")

    shares = g(bal,
        "CommonStockSharesOutstanding", "SharesOutstanding")

    # Market cap: not in filings, would need real-time price × shares
    # Pass 0 — caller can override with live data if needed
    market_cap = 0.0

    return YearData(
        ticker=ticker,
        period=period_label or str(period),
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
        market_cap=market_cap,
        shares_outstanding=shares,
    )


def _get_statement(financials, kind: str):
    """Try multiple attribute names for different edgartools versions."""
    candidates = {
        "income": ["income_statement", "income", "income_statements"],
        "balance": ["balance_sheet", "balance", "balance_sheets"],
        "cashflow": ["cash_flow_statement", "cashflow", "cash_flow", "cash_flow_statements"],
    }
    for name in candidates.get(kind, []):
        stmt = getattr(financials, name, None)
        if stmt is not None:
            return stmt
    return None


def _get_period_label(stmt, period: int) -> Optional[str]:
    """Try to get a human-readable period label (year string) for a column."""
    if stmt is None:
        return None
    try:
        import pandas as pd
        if hasattr(stmt, "columns"):
            cols = list(stmt.columns)
            if period < len(cols):
                return str(cols[period])
    except Exception:
        pass
    return None


def _get_value(stmt, period: int, *aliases) -> float:
    """
    Try each alias against the statement until one returns a non-zero value.
    Handles both pandas DataFrame and dict-like statement objects.
    """
    if stmt is None:
        return 0.0

    for alias in aliases:
        try:
            # pandas DataFrame: rows are line items
            import pandas as pd
            if isinstance(stmt, pd.DataFrame):
                # Try exact index match
                if alias in stmt.index:
                    val = stmt.loc[alias].iloc[period] if hasattr(stmt.loc[alias], 'iloc') else stmt.loc[alias, stmt.columns[period]]
                    if val is not None and str(val) not in ("nan", "None", ""):
                        return float(val)
                # Try case-insensitive partial match
                matches = stmt.index[stmt.index.str.contains(alias, case=False, na=False, regex=False)]
                if len(matches) > 0:
                    val = stmt.loc[matches[0]].iloc[period] if hasattr(stmt.loc[matches[0]], 'iloc') else stmt.loc[matches[0], stmt.columns[period]]
                    if val is not None and str(val) not in ("nan", "None", ""):
                        return float(val)
        except Exception:
            pass

        try:
            # Dict-like or custom Statement object
            val = stmt[alias]
            if hasattr(val, '__iter__') and not isinstance(val, (str, bytes)):
                items = list(val)
                if period < len(items):
                    v = items[period]
                    if v is not None:
                        return float(v)
            elif val is not None:
                return float(val)
        except Exception:
            pass

    return 0.0


def year_data_to_beneish_inputs(current: YearData, prior: YearData):
    """Convert two YearData objects into BeneishInputs."""
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
    """Convert a YearData object into AltmanInputs."""
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
    """Convert two YearData objects into SloanInputs."""
    from src.metrics.sloan import SloanInputs
    return SloanInputs(
        net_income=current.net_income,
        cash_flow_from_operations=current.operating_cash_flow,
        cash_flow_from_investing=current.investing_cash_flow,
        total_assets_current=current.total_assets,
        total_assets_prior=prior.total_assets,
    )


def year_data_to_piotroski_inputs(current: YearData, prior: YearData):
    """Convert two YearData objects into PiotroskiInputs."""
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
