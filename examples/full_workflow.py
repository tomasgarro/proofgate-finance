"""
Full workflow example: forensic research + policy gate + receipt.

Run from the project root:
  python examples/full_workflow.py
"""

from src.metrics.beneish import BeneishInputs, calculate as beneish_score
from src.metrics.altman import AltmanInputs, calculate as altman_score
from src.metrics.sloan import SloanInputs, calculate as sloan_score
from src.metrics.piotroski import PiotroskiInputs, calculate as piotroski_score
from src.policies.gate import Policy, Proposal, check
from src.receipts.receipt import generate
from src.reports.memo import build_memo
from src.proof_experiments.mock_proof import simulate_position_size_proof


# ── 1. Forensic scores (sample data — replace with real fetched financials) ──

beneish = beneish_score(BeneishInputs(
    net_receivables_t=350, sales_t=3200, cogs_t=2000,
    current_assets_t=1000, ppe_net_t=1200, total_assets_t=4000,
    depreciation_t=130, sga_expense_t=380, long_term_debt_t=1200,
    current_liabilities_t=550, net_income_t=320, operating_cash_flow_t=380,
    net_receivables_t1=330, sales_t1=3000, cogs_t1=1900,
    current_assets_t1=950, ppe_net_t1=1150, total_assets_t1=3800,
    depreciation_t1=120, sga_expense_t1=360, long_term_debt_t1=1200,
    current_liabilities_t1=530,
))

altman = altman_score(AltmanInputs(
    working_capital=450, total_assets=4000, retained_earnings=900,
    ebit=420, market_cap=5000, total_liabilities=1750, sales=3200,
))

sloan = sloan_score(SloanInputs(
    net_income=320, cash_flow_from_operations=380, cash_flow_from_investing=-80,
    total_assets_current=4000, total_assets_prior=3800,
))

piotroski = piotroski_score(PiotroskiInputs(
    net_income=320, operating_cash_flow=380,
    total_assets=4000, total_assets_prior=3800,
    total_debt=600, total_debt_prior=700,
    current_assets=1000, current_liabilities=550,
    current_assets_prior=950, current_liabilities_prior=580,
    common_stock_issued=0,
    revenue=3200, revenue_prior=3000, cogs=2000, cogs_prior=1900,
))

print("=== FORENSIC SCORES ===\n")
print(beneish.summary()); print()
print(altman.summary()); print()
print(sloan.summary()); print()
print(piotroski.summary()); print()

# ── 2. Policy gate ────────────────────────────────────────────────────────────

policy = Policy(
    allowed_assets=["BTC", "ETH", "ADA"],
    max_position_pct=5.0,
    allow_leverage=False,
    allowed_venues=["simulated"],
)
proposal = Proposal(
    asset="ADA",
    action="buy",
    position_pct=3.0,
    venue="simulated",
    leverage=1.0,
    rationale="Forensic screens clean. Piotroski strong. Altman safe zone.",
)

gate_result = check(policy, proposal)
print("=== POLICY GATE ===\n")
print(gate_result.summary()); print()

# ── 3. Receipt ────────────────────────────────────────────────────────────────

receipt = generate(policy, proposal, gate_result)
print("=== RECEIPT ===\n")
print(receipt.summary()); print()
print(receipt.to_json()); print()

# ── 4. Simulated proof (Phase 4 placeholder) ──────────────────────────────────

proof = simulate_position_size_proof(private_max_pct=5.0, proposed_pct=3.0)
print("=== PROOF EXPERIMENT (SIMULATED) ===\n")
print(proof.summary()); print()

# ── 5. Research memo ─────────────────────────────────────────────────────────

memo = build_memo(
    ticker="ADA",
    beneish=beneish,
    altman=altman,
    sloan=sloan,
    piotroski=piotroski,
    agent_summary="[Agent interpretation would go here after LLM summarization step.]",
    data_sources=["SEC EDGAR (simulated)", "FinancialModelingPrep (simulated)"],
    uncertainty_notes=["Sample data used — replace with real fetched financials"],
)

print("=== RESEARCH MEMO ===\n")
print(memo)
