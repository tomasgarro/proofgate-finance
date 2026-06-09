# ProofGate Finance: MVP Specification

## Project name

ProofGate Finance

## MVP promise

An AI financial research agent that screens assets, explains risk, and can only recommend actions that satisfy user-defined constraints.

## Phase 1: Forensic finance research agent

### Goal

Build a working agent that produces a research memo from public data without any trade execution.

### Core flow

1. User provides a ticker, company name, or token.
2. System fetches relevant public financial data (SEC filings, structured financials, market data).
3. System computes four forensic/risk metrics deterministically.
4. Agent summarizes findings with source citations and caveats.
5. System produces a structured research memo in Markdown.

### Forensic metrics

#### Beneish M-Score
- Custom implementation (not in FinanceToolkit).
- Eight-variable model predicting earnings manipulation probability.
- Threshold: M > -2.22 suggests potential manipulation.
- Inputs required: net receivables, sales, COGS, current assets, PP&E, total assets, depreciation, SGA expenses, long-term debt, current liabilities, net income, operating cash flow.
- Data sources: income statement + balance sheet + cash flow statement.

#### Altman Z-Score
- Available in FinanceToolkit (`financetoolkit.models.altman_model`).
- Five-variable solvency/bankruptcy prediction model.
- Zones: Z > 2.99 = safe, 1.81-2.99 = grey, < 1.81 = distress.
- Inputs: working capital, retained earnings, EBIT, market cap, total assets, total liabilities, sales.

#### Sloan Accruals Ratio
- Custom implementation (not in FinanceToolkit as standalone).
- Measures earnings quality: high accruals relative to assets suggest earnings may not persist.
- Formula: (Net Income - Cash Flow from Operations - Cash Flow from Investing) / Average Total Assets.
- High positive values (above ~5%) are a caution flag.

#### Piotroski F-Score
- Available in FinanceToolkit (`financetoolkit.models.piotroski_model`).
- Nine-criteria binary scoring (0-9).
- Scores 0-2: weak, 3-6: neutral, 7-9: strong fundamentals.
- Inputs: ROA, operating cash flow, leverage, current ratio, shares outstanding, gross margin, asset turnover.

### Output format

```
Research Memo: [TICKER] — [DATE]

RISK SUMMARY
  Beneish M-Score: -1.78 (CAUTION — above manipulation threshold)
  Altman Z-Score: 3.41 (SAFE ZONE)
  Sloan Accruals Ratio: 8.2% (ELEVATED — earnings quality concern)
  Piotroski F-Score: 6/9 (NEUTRAL-STRONG)

RED FLAGS
  - M-Score above -2.22 threshold; review receivables and gross margin trends
  - Sloan ratio above 5%; cash conversion of earnings is below reported income

GREEN FLAGS
  - Altman Z > 2.99 indicates low near-term bankruptcy risk
  - Piotroski 6/9 shows solid fundamentals across most criteria

DATA SOURCES
  - SEC EDGAR 10-K [link]
  - FinancialModelingPrep [link]

UNCERTAINTY NOTES
  - Market data from [date]; may be stale
  - Cash flow statement uses TTM figures

DISCLAIMER
  For research purposes only. Not investment advice.
```

### Agent layer

- Calls deterministic metrics engine first.
- Passes structured results plus raw source data to LLM.
- LLM task: summarize, flag changes vs prior periods, generate research questions.
- LLM must not invent financial figures. All numbers come from the metrics engine.
- Every number in the output must link back to a source.

## Phase 2: Strategy sandbox and backtesting

### Goal

Allow strategy ideas to be tested on historical data without execution.

### Core flow

1. User defines a strategy template (e.g. "buy only stocks with Piotroski > 6 and Altman in safe zone").
2. System applies it to historical data across a universe.
3. System reports returns, drawdown, hit rate, and regime sensitivity.
4. System flags leakage risks from repeated signal outputs.

### Key design constraint

No LLM inside the performance calculation. All backtest numbers are deterministic and reproducible. The LLM only interprets results.

## Phase 3: Risk-gated agent prototype

### Goal

Demonstrate that an agent cannot recommend or simulate an action unless it satisfies explicit constraints.

### Policy schema

```json
{
  "version": "1.0",
  "allowed_assets": ["BTC", "ETH", "ADA"],
  "blocked_assets": [],
  "max_position_pct": 5.0,
  "max_daily_loss_pct": 2.0,
  "max_drawdown_pct": 10.0,
  "allow_leverage": false,
  "max_leverage": 1.0,
  "allowed_venues": ["simulated"],
  "blocked_venues": [],
  "allowed_time_windows": [],
  "requires_user_approval": true,
  "strategy_license_required": false
}
```

### Proposal schema

```json
{
  "asset": "ADA",
  "action": "buy",
  "position_pct": 3.0,
  "venue": "simulated",
  "leverage": 1.0,
  "rationale": "Piotroski 7/9, Altman safe zone, no red flags"
}
```

### Receipt schema

```json
{
  "decision": "allow",
  "checked_constraints": [
    "asset_in_allowed_list",
    "position_size_within_limit",
    "venue_allowed",
    "no_leverage",
    "user_approval_required"
  ],
  "failed_constraints": [],
  "timestamp_utc": "2026-06-09T12:00:00Z",
  "policy_hash": "sha256:...",
  "proposal_hash": "sha256:...",
  "version": "1.0"
}
```

## Phase 4: Midnight/Compact proof experiment

### Goal

Determine whether a simple private risk constraint can be represented and verified in Compact.

### Candidate proof

Given a private max position size and a public proposed position size, prove the proposed size is at or below the private max without revealing the private max.

```
private input: max_position_pct  (e.g. 5.0)
public input:  proposed_position_pct  (e.g. 3.0)
constraint:    proposed_position_pct <= max_position_pct
output:        valid | invalid
```

### Design notes

- Verify syntax and tooling with Midnight Expert tools before implementing.
- If Compact cannot represent this cleanly today, document the blocker.
- Keep a deterministic mock that simulates the proof output for demo purposes.
- The mock must be clearly labeled as a simulation, not a real ZK proof.

See `docs/midnight-proof-experiments.md` for full design notes.

## Non-goals for all phases

- No real-money trading in any phase.
- No investment advice claims.
- No custody of user assets.
- No private strategy marketplace in v1 or v2.
- No promises of profitability.
- No handling of exchange API keys.
- No marketing as alpha generation.
