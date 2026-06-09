"""Unit tests for forensic metrics. All values are deterministic."""

import pytest
from src.metrics.beneish import BeneishInputs, calculate as beneish_score
from src.metrics.altman import AltmanInputs, calculate as altman_score
from src.metrics.sloan import SloanInputs, calculate as sloan_score
from src.metrics.piotroski import PiotroskiInputs, calculate as piotroski_score


# ── Beneish M-Score ──────────────────────────────────────────────────────────

def _enron_like_inputs() -> BeneishInputs:
    """
    Stylized inputs representing a company with manipulation signals:
    rising receivables, declining margins, high accruals.
    """
    return BeneishInputs(
        net_receivables_t=500, sales_t=3000, cogs_t=2400,
        current_assets_t=800, ppe_net_t=1200, total_assets_t=3500,
        depreciation_t=120, sga_expense_t=400, long_term_debt_t=1800,
        current_liabilities_t=600, net_income_t=200, operating_cash_flow_t=-50,
        net_receivables_t1=300, sales_t1=2500, cogs_t1=1900,
        current_assets_t1=700, ppe_net_t1=1100, total_assets_t1=3000,
        depreciation_t1=100, sga_expense_t1=300, long_term_debt_t1=1400,
        current_liabilities_t1=500,
    )


def _clean_inputs() -> BeneishInputs:
    """Inputs representing a stable, clean company."""
    return BeneishInputs(
        net_receivables_t=300, sales_t=3000, cogs_t=1800,
        current_assets_t=900, ppe_net_t=1100, total_assets_t=3500,
        depreciation_t=110, sga_expense_t=300, long_term_debt_t=1000,
        current_liabilities_t=500, net_income_t=400, operating_cash_flow_t=450,
        net_receivables_t1=295, sales_t1=2900, cogs_t1=1750,
        current_assets_t1=880, ppe_net_t1=1080, total_assets_t1=3400,
        depreciation_t1=105, sga_expense_t1=290, long_term_debt_t1=1000,
        current_liabilities_t1=490,
    )


def test_beneish_manipulation_risk():
    result = beneish_score(_enron_like_inputs())
    # High accruals (negative operating cash vs positive net income) should push M > -2.22
    assert result.flag == "MANIPULATION_RISK", f"Expected MANIPULATION_RISK, got {result.flag} (M={result.m_score:.4f})"


def test_beneish_clean():
    result = beneish_score(_clean_inputs())
    assert result.flag in ("CLEAN", "BORDERLINE"), f"Expected CLEAN or BORDERLINE, got {result.flag}"


def test_beneish_tata_effect():
    """TATA is the heaviest weighted variable (4.679). Verify it dominates."""
    base = _clean_inputs()
    # Simulate large accruals: net income much higher than operating cash flow
    base.net_income_t = 1000
    base.operating_cash_flow_t = -500
    result = beneish_score(base)
    assert result.tata > 0.4, "Expected high TATA from large accruals"
    assert result.m_score > -2.22, "High TATA should push M above threshold"


def test_beneish_deterministic():
    r1 = beneish_score(_enron_like_inputs())
    r2 = beneish_score(_enron_like_inputs())
    assert r1.m_score == r2.m_score


def test_beneish_components_exist():
    result = beneish_score(_clean_inputs())
    for attr in ("dsri", "gmi", "aqi", "sgi", "depi", "sgai", "tata", "lvgi"):
        assert hasattr(result, attr)


# ── Altman Z-Score ──────────────────────────────────────────────────────────

def _safe_zone_inputs() -> AltmanInputs:
    return AltmanInputs(
        working_capital=500, total_assets=2000, retained_earnings=800,
        ebit=300, market_cap=3000, total_liabilities=800, sales=2500,
    )


def _distress_inputs() -> AltmanInputs:
    return AltmanInputs(
        working_capital=-200, total_assets=1000, retained_earnings=-300,
        ebit=-100, market_cap=100, total_liabilities=900, sales=400,
    )


def test_altman_safe_zone():
    result = altman_score(_safe_zone_inputs())
    assert result.zone == "SAFE"
    assert result.z_score > 2.99


def test_altman_distress_zone():
    result = altman_score(_distress_inputs())
    assert result.zone == "DISTRESS"
    assert result.z_score < 1.81


def test_altman_components():
    result = altman_score(_safe_zone_inputs())
    assert result.x1 == pytest.approx(500 / 2000)
    assert result.x2 == pytest.approx(800 / 2000)
    assert result.x3 == pytest.approx(300 / 2000)
    assert result.x4 == pytest.approx(3000 / 800)
    assert result.x5 == pytest.approx(2500 / 2000)


def test_altman_zero_assets():
    inputs = AltmanInputs(0, 0, 0, 0, 0, 0, 0)
    result = altman_score(inputs)
    assert result.zone == "DISTRESS"


# ── Sloan Accruals Ratio ──────────────────────────────────────────────────────

def test_sloan_elevated():
    inputs = SloanInputs(
        net_income=500, cash_flow_from_operations=100, cash_flow_from_investing=-50,
        total_assets_current=5000, total_assets_prior=4800,
    )
    result = sloan_score(inputs)
    # accruals = 500 - 100 - (-50) = 450; avg assets = 4900; ratio = 9.2%
    assert result.flag == "ELEVATED"
    assert result.accruals_ratio > 0.05


def test_sloan_clean():
    inputs = SloanInputs(
        net_income=200, cash_flow_from_operations=220, cash_flow_from_investing=-30,
        total_assets_current=5000, total_assets_prior=4800,
    )
    result = sloan_score(inputs)
    # accruals = 200 - 220 - (-30) = 10; avg assets = 4900; ratio = 0.2%
    assert result.flag == "CLEAN"
    assert result.accruals_ratio < 0.02


def test_sloan_formula():
    inputs = SloanInputs(
        net_income=100, cash_flow_from_operations=80, cash_flow_from_investing=-20,
        total_assets_current=1000, total_assets_prior=1000,
    )
    result = sloan_score(inputs)
    # accruals = 100 - 80 - (-20) = 40; avg assets = 1000; ratio = 4%
    assert result.accruals_amount == pytest.approx(40.0)
    assert result.accruals_ratio == pytest.approx(0.04)
    assert result.flag == "MODERATE"


def test_sloan_zero_assets():
    inputs = SloanInputs(100, 80, -20, 0, 0)
    result = sloan_score(inputs)
    assert result.accruals_ratio == 0.0


# ── Piotroski F-Score ──────────────────────────────────────────────────────

def _strong_inputs() -> PiotroskiInputs:
    return PiotroskiInputs(
        net_income=500, operating_cash_flow=600,
        total_assets=3000, total_assets_prior=2800,
        total_debt=400, total_debt_prior=500,
        current_assets=1200, current_liabilities=400,
        current_assets_prior=1000, current_liabilities_prior=450,
        common_stock_issued=0,
        revenue=4000, revenue_prior=3500, cogs=2200, cogs_prior=2000,
    )


def _weak_inputs() -> PiotroskiInputs:
    return PiotroskiInputs(
        net_income=-200, operating_cash_flow=-100,
        total_assets=3000, total_assets_prior=2800,
        total_debt=1800, total_debt_prior=1500,
        current_assets=400, current_liabilities=600,
        current_assets_prior=500, current_liabilities_prior=400,
        common_stock_issued=100_000,
        revenue=2000, revenue_prior=2200, cogs=1800, cogs_prior=1700,
    )


def test_piotroski_strong():
    result = piotroski_score(_strong_inputs())
    assert result.f_score >= 5
    assert result.flag in ("STRONG", "NEUTRAL")


def test_piotroski_weak():
    result = piotroski_score(_weak_inputs())
    assert result.flag in ("WEAK", "NEUTRAL")


def test_piotroski_max_score_9():
    result = piotroski_score(_strong_inputs())
    assert 0 <= result.f_score <= 9


def test_piotroski_criteria_dict():
    result = piotroski_score(_strong_inputs())
    expected_keys = {
        "roa_positive", "cfo_positive", "roa_improving", "accruals_quality",
        "leverage_decreasing", "liquidity_improving", "no_dilution",
        "gross_margin_improving", "asset_turnover_improving",
    }
    assert set(result.criteria.keys()) == expected_keys


def test_piotroski_score_matches_criteria():
    result = piotroski_score(_strong_inputs())
    assert result.f_score == sum(1 for v in result.criteria.values() if v)
