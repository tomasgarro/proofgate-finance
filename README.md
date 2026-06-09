# ProofGate Finance

An AI forensic finance research agent with deterministic risk-policy gates.

## Thesis

AI agents can already research markets, compare filings, and generate trade ideas. The missing layer is not intelligence. It is proof: proof that an agent had permission, respected constraints, and used private strategy logic without exposing it.

ProofGate Finance explores what that looks like from the ground up, starting with research and working toward provable constraints.

## What this is

- A non-custodial AI agent that reads public financial data and produces research memos.
- A deterministic risk-policy gate that checks proposed actions against explicit user-defined constraints.
- A receipt system that hashes the policy and proposal and records what was checked.
- A design exploration for Midnight/Compact proof experiments on private constraints.

## What this is not

- Not a trading bot.
- Not investment advice.
- Not a custody solution.
- Not a strategy marketplace (that is a future vision, not this version).
- Not a promise of profitability.

## Forensic scores

ProofGate uses four forensic metrics as probability flags, not proof:

| Score | What it measures | Source |
|---|---|---|
| Beneish M-Score | Earnings manipulation probability | Custom implementation |
| Altman Z-Score | Bankruptcy / solvency risk | FinanceToolkit native |
| Sloan Accruals Ratio | Earnings quality / accrual magnitude | Custom implementation |
| Piotroski F-Score | Fundamental financial strength (0-9) | FinanceToolkit native |

These are research signals. They are not trading signals, fraud proof, or investment recommendations.

## Architecture

```
proofgate-finance/
  src/
    ingestion/       # SEC EDGAR fetcher, financial data loader
    metrics/         # Beneish, Altman, Sloan, Piotroski implementations
    agents/          # Research agent: summarize, compare, flag
    policies/        # Policy schema and deterministic rule checker
    receipts/        # Receipt generator with policy and proposal hashes
    reports/         # Markdown report builder
    proof_experiments/  # Midnight/Compact proof design notes and mocks
  tests/             # Unit tests for all deterministic modules
  examples/          # Sample policies, proposals, and reports
  docs/              # Specs, compliance map, proof experiment design
  data/samples/      # Sample financial data for testing
```

## Data sources

- SEC EDGAR (free, public)
- FinanceToolkit via FinancialModelingPrep (requires free API key)
- yfinance as fallback for market data

## Setup

```bash
pip install -r requirements.txt
```

Set environment variables:
```
FMP_API_KEY=your_fmp_key        # FinancialModelingPrep (free tier available)
ANTHROPIC_API_KEY=your_key      # For research agent summarization
```

## Quickstart

```python
from src.metrics.beneish import beneish_m_score
from src.metrics.altman import altman_z_score
from src.policies.gate import PolicyGate
from src.receipts.receipt import Receipt

# Run forensic check on a ticker
# (see examples/ for full workflow)
```

## Compliance disclaimer

For research and educational purposes only. Not investment advice. Forensic scores are probability indicators, not proof of fraud or financial distress. Simulated results do not predict future performance. ZK proofs verify constraints, not profitability.

## Phases

| Phase | Status | Description |
|---|---|---|
| 1 | In progress | Forensic finance research agent |
| 2 | Planned | Strategy sandbox and backtesting |
| 3 | Planned | Risk-gated agent prototype |
| 4 | Planned | Midnight/Compact proof experiment |
| 5 | Future | Private strategy licensing concept |
