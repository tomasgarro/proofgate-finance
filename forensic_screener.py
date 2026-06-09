#!/usr/bin/env python3
"""
ProofGate Finance — forensic screener.

Screen any US public company or DeFi protocol with one command.

Setup:
    pip install -r requirements.txt
    export SEC_IDENTITY="Your Name your@email.com"   # required by SEC
    export ANTHROPIC_API_KEY="sk-..."                # optional, only for --diff
    export FMP_API_KEY="..."                         # optional, FinanceToolkit data

Run:
    python forensic_screener.py AAPL
    python forensic_screener.py TSLA NVDA SMCI
    python forensic_screener.py SMCI --diff
    python forensic_screener.py --crypto aave uniswap
    python forensic_screener.py AAPL --diff --save-report

Not financial advice. Forensic scores are probability flags, not proof.
A bad score means open the filing, never act on the number alone.
"""

import argparse
import os
import sys
from datetime import date
from typing import Optional

# ── Thresholds — tune to taste ────────────────────────────────────────────────
M_FLAG       = -2.22   # Beneish above this → manipulation risk (academic cutoff)
M_STRICT     = -1.78   # stricter version used in article's script
Z_DISTRESS   =  1.81
Z_SAFE       =  2.99
ACCRUAL_FLAG =  0.05   # |ratio| above 5% → earnings quality flag
F_STRONG     =  6
CLIFF_FLAG   =  5.0    # unlock > 5% of circulating → flag


def screen_equity(ticker: str, do_diff: bool = False, strict_m: bool = False) -> dict:
    """Run full forensic screen on a US equity ticker."""
    print(f"\n{'='*62}")
    print(f"  {ticker.upper()}")
    print(f"{'='*62}")

    # ── Load real data ─────────────────────────────────────────────
    try:
        from src.ingestion.edgar import (
            load_company_years,
            year_data_to_beneish_inputs,
            year_data_to_altman_inputs,
            year_data_to_sloan_inputs,
            year_data_to_piotroski_inputs,
        )
        print("  Fetching EDGAR filings...", end=" ", flush=True)
        current, prior = load_company_years(ticker)
        print(f"OK  ({current.period} vs {prior.period})")
        beneish_inputs = year_data_to_beneish_inputs(current, prior)
        altman_inputs = year_data_to_altman_inputs(current)
        sloan_inputs = year_data_to_sloan_inputs(current, prior)
        piotroski_inputs = year_data_to_piotroski_inputs(current, prior)
        data_source = "SEC EDGAR via edgartools"
    except Exception as e:
        print(f"FAILED — {e}")
        print("  Tip: set SEC_IDENTITY='Your Name email@example.com' and re-run.")
        return {"ticker": ticker, "error": str(e)}

    # ── Compute scores ─────────────────────────────────────────────
    from src.metrics.beneish import calculate as beneish_score
    from src.metrics.altman import calculate as altman_score
    from src.metrics.sloan import calculate as sloan_score
    from src.metrics.piotroski import calculate as piotroski_score

    beneish = beneish_score(beneish_inputs)
    altman = altman_score(altman_inputs)
    sloan = sloan_score(sloan_inputs)
    piotroski = piotroski_score(piotroski_inputs)

    # ── Print scores ───────────────────────────────────────────────
    m_threshold = M_STRICT if strict_m else M_FLAG
    m_flag = "⚠ INVESTIGATE" if beneish.m_score > m_threshold else "✓ clean"
    z_flag = "⚠ DISTRESS" if altman.z_score < Z_DISTRESS else ("⚠ GREY" if altman.z_score < Z_SAFE else "✓ safe")
    a_flag = "⚠ ELEVATED" if abs(sloan.accruals_ratio) > ACCRUAL_FLAG else "✓ clean"
    f_flag = "✓ strong" if piotroski.f_score >= F_STRONG else "⚠ weak"

    print(f"\n  Beneish M-Score : {beneish.m_score:+.2f}   (> {m_threshold:.2f} = investigate)  {m_flag}")
    print(f"  Altman Z-Score  : {altman.z_score:.2f}    (< {Z_DISTRESS} distress, > {Z_SAFE} safe)   {z_flag}")
    print(f"  Piotroski F     : {piotroski.f_score}/9        (>= {F_STRONG} = strengthening)     {f_flag}")
    print(f"  Sloan Accruals  : {sloan.accruals_ratio:+.1%}    (|x| > {ACCRUAL_FLAG:.0%} = quality flag)  {a_flag}")

    # ── Verdict ────────────────────────────────────────────────────
    red_flags = []
    if beneish.m_score > m_threshold:
        red_flags.append(f"M-Score {beneish.m_score:+.2f} — earnings manipulation signal")
    if altman.z_score < Z_DISTRESS:
        red_flags.append(f"Z-Score {altman.z_score:.2f} — financial distress zone")
    if abs(sloan.accruals_ratio) > ACCRUAL_FLAG:
        red_flags.append(f"Sloan {sloan.accruals_ratio:+.1%} — earnings quality concern")
    if piotroski.f_score < F_STRONG:
        red_flags.append(f"Piotroski {piotroski.f_score}/9 — fundamentals weakening")

    print(f"\n  VERDICT: {'INVESTIGATE' if red_flags else 'CLEAN'}")
    for f in red_flags:
        print(f"    - {f}")

    # ── Risk Factors + MD&A diff (optional) ───────────────────────
    diff_result = None
    if do_diff:
        print("\n  Running year-over-year filing diff...")
        try:
            from src.agents.risk_diff import diff_10k_sections
            diff_result = diff_10k_sections(ticker)
            if diff_result.error:
                print(f"  Diff skipped: {diff_result.error}")
            else:
                if diff_result.keyword_flags:
                    print(f"\n  KEYWORD FLAGS in Risk Factors:")
                    for kw in diff_result.keyword_flags:
                        print(f"    ! '{kw}'")
                if diff_result.risk_factors_diff:
                    print(f"\n  RISK FACTORS DIFF:")
                    for line in diff_result.risk_factors_diff.splitlines():
                        print(f"    {line}")
                if diff_result.mda_diff:
                    print(f"\n  MD&A DIFF:")
                    for line in diff_result.mda_diff.splitlines():
                        print(f"    {line}")
        except Exception as e:
            print(f"  Diff failed: {e}")

    return {
        "ticker": ticker,
        "period": current.period,
        "beneish_m": beneish.m_score,
        "altman_z": altman.z_score,
        "piotroski_f": piotroski.f_score,
        "sloan_accruals": sloan.accruals_ratio,
        "red_flags": red_flags,
        "verdict": "INVESTIGATE" if red_flags else "CLEAN",
        "data_source": data_source,
        "beneish": beneish,
        "altman": altman,
        "sloan": sloan,
        "piotroski": piotroski,
        "diff_result": diff_result,
    }


def screen_crypto(slug: str) -> dict:
    """Run basic crypto protocol screen via DefiLlama."""
    print(f"\n{'='*62}")
    print(f"  CRYPTO: {slug.upper()}")
    print(f"{'='*62}")

    try:
        from src.ingestion.defillama import get_protocol_metrics
        print("  Fetching DefiLlama data...", end=" ", flush=True)
        metrics = get_protocol_metrics(slug)
        print("OK")
        print(f"\n{metrics.summary()}")
    except Exception as e:
        print(f"FAILED — {e}")
        return {"slug": slug, "error": str(e)}

    return {"slug": slug, "metrics": metrics}


def save_report(results: list[dict], path: Optional[str] = None) -> str:
    """Save a Markdown report for all screened tickers."""
    from src.reports.memo import build_memo
    today = date.today().isoformat()
    path = path or f"examples/reports/screen_{today}.md"

    lines = [f"# Forensic Screen Report — {today}", ""]
    for r in results:
        if "error" in r:
            continue
        ticker = r.get("ticker", r.get("slug", "UNKNOWN"))
        memo = build_memo(
            ticker=ticker,
            beneish=r.get("beneish"),
            altman=r.get("altman"),
            sloan=r.get("sloan"),
            piotroski=r.get("piotroski"),
            agent_summary="",
            data_sources=[r.get("data_source", "SEC EDGAR")],
        )
        lines.append(memo)
        lines.append("\n---\n")

    content = "\n".join(lines)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def main():
    ap = argparse.ArgumentParser(
        description="ProofGate Finance — forensic screener for equities and DeFi protocols",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python forensic_screener.py AAPL
  python forensic_screener.py TSLA NVDA SMCI
  python forensic_screener.py SMCI --diff
  python forensic_screener.py --crypto aave uniswap compound
  python forensic_screener.py AAPL --diff --save-report
  python forensic_screener.py ENRNQ --strict-m   # stricter M-Score threshold

Not financial advice. Probability flags only.
        """,
    )
    ap.add_argument("tickers", nargs="*", help="Ticker symbols (e.g. AAPL TSLA)")
    ap.add_argument("--diff", action="store_true", help="Run year-over-year Risk Factors + MD&A diff (requires ANTHROPIC_API_KEY)")
    ap.add_argument("--crypto", nargs="+", metavar="SLUG", help="Screen DeFi protocols by DefiLlama slug (e.g. aave uniswap)")
    ap.add_argument("--save-report", action="store_true", help="Save Markdown report to examples/reports/")
    ap.add_argument("--strict-m", action="store_true", help="Use stricter M-Score threshold (-1.78 instead of -2.22)")
    args = ap.parse_args()

    if not args.tickers and not args.crypto:
        ap.print_help()
        sys.exit(1)

    results = []

    for ticker in args.tickers:
        r = screen_equity(ticker, do_diff=args.diff, strict_m=args.strict_m)
        results.append(r)

    if args.crypto:
        for slug in args.crypto:
            r = screen_crypto(slug)
            results.append(r)

    print(f"\n{'='*62}")
    print("  SUMMARY")
    print(f"{'='*62}")
    for r in results:
        ticker = r.get("ticker", r.get("slug", "?"))
        if "error" in r:
            print(f"  {ticker:10} ERROR: {r['error']}")
        elif "verdict" in r:
            flag_count = len(r.get("red_flags", []))
            print(f"  {ticker:10} {r['verdict']:12}  ({flag_count} flag{'s' if flag_count != 1 else ''})")
        else:
            print(f"  {ticker:10} CRYPTO screened")

    if args.save_report:
        path = save_report(results)
        print(f"\n  Report saved → {path}")

    print(f"\nReminder: probability flags, not proof. A bad score means open the filing.")
    print("Not financial advice. Do your own research.\n")


if __name__ == "__main__":
    main()
