# ProofGate Finance

> AI forensic research agent + deterministic risk gate for equities and DeFi protocols.
> Built at the intersection of traditional forensic accounting and on-chain risk analysis.
> Designed for the era of ZK-gated autonomous agents.

---

## What it does

ProofGate Finance screens companies and DeFi protocols the way a forensic analyst would — not with predictions, but with structural red flags from the filings themselves.

```
$ python forensic_screener.py SMCI

  Beneish M-Score : -2.14   ⚠ INVESTIGATE   ← above manipulation threshold
  Altman Z-Score  : 5.08    ✓ safe
  Piotroski F     : 8/9     ✓ strong
  Sloan Accruals  : -3.6%   ✓ clean

  VERDICT: INVESTIGATE
    - M-Score -2.14 — earnings manipulation signal
```

SuperMicro (SMCI) filed a restatement in 2024. The Beneish M-Score flags it above the -2.22 threshold. This is the tool working as intended.

```
$ python forensic_screener.py AAPL

  Beneish M-Score : -2.29   ✓ clean
  Altman Z-Score  : 11.46   ✓ safe
  Piotroski F     : 9/9     ✓ strong
  Sloan Accruals  : -4.1%   ✓ clean

  VERDICT: CLEAN
```

```
$ python forensic_screener.py --crypto aave

  Protocol: Aave  TVL: $X,XXX,XXX,XXX
  Fees 30d / Revenue 30d / Emissions / Concentration flags
```

---

## Thesis

AI agents can already research markets, compare filings, and generate trade ideas. The missing layer is not intelligence — it is **proof**: proof that an agent had permission, respected constraints, and used private strategy logic without exposing it.

ProofGate Finance builds from the ground up:

1. **Research layer** — forensic scoring from public data (SEC EDGAR, DefiLlama, Dune, Xerberus)
2. **Gate layer** — deterministic policy enforcement with SHA-256 audit receipts
3. **Proof layer** — ZK experiments on the Midnight blockchain (Phase 4, in design)

The thesis draws from the IC3 "Crypto × AI" research: transparent strategies are auditable but disclosure destroys edge; private strategies protect edge but create information asymmetry. Zero-knowledge proofs are the bridge.

---

## Forensic scores

| Score | What it catches | Threshold |
|---|---|---|
| **Beneish M-Score** | Earnings manipulation probability (8 variables) | > -2.22 investigate, > -1.78 high risk |
| **Altman Z-Score** | Bankruptcy / solvency risk (5 variables) | < 1.81 distress, > 2.99 safe |
| **Sloan Accruals Ratio** | Earnings quality — cash vs reported income gap | \|x\| > 5% flag |
| **Piotroski F-Score** | Fundamental financial strength (9 binary criteria) | < 3 weak, ≥ 7 strong |
| **Crypto Risk Flags** | Unlock cliffs, holder concentration, emissions vs revenue | Configurable thresholds |

These are probability flags from historical filings. They are not trading signals, fraud proof, or investment advice.

---

## Data sources

| Source | Coverage | Key |
|---|---|---|
| **SEC EDGAR** | All US public companies — 10-K filings, Risk Factors, MD&A | Free (identity string only) |
| **DefiLlama** | DeFi TVL, fees, revenue, token unlock schedules | Free (no key) |
| **yfinance** | Live market cap for Altman X4 component | Free (no key) |
| **Dune Analytics** | On-chain SQL — holder distribution, DEX volume, flows | Free tier |
| **Xerberus** | Risk ratings for Cardano, Ethereum, Polygon tokens + vaults | API key (contact ms@xerberus.io) |
| **FinancialModelingPrep** | Structured financials via FinanceToolkit | Free tier (250 req/day) |
| **Anthropic Claude** | Year-over-year Risk Factors + MD&A diff (--diff flag) | API key |

---

## Architecture

```
proofgate-finance/
├── forensic_screener.py      # CLI — run any ticker or DeFi slug
├── src/
│   ├── ingestion/
│   │   ├── edgar.py          # SEC EDGAR via edgartools 5.x
│   │   ├── defillama.py      # DefiLlama TVL, fees, unlock schedules
│   │   ├── dune_client.py    # Dune Analytics on-chain SQL
│   │   └── xerberus.py       # Xerberus DeFi risk ratings (Cardano + EVM)
│   ├── metrics/
│   │   ├── beneish.py        # Beneish M-Score (custom — not in FinanceToolkit)
│   │   ├── altman.py         # Altman Z-Score
│   │   ├── sloan.py          # Sloan Accruals Ratio (custom)
│   │   ├── piotroski.py      # Piotroski F-Score
│   │   └── crypto_risk.py    # DeFi unlock + concentration flags
│   ├── agents/
│   │   └── risk_diff.py      # Claude: year-over-year 10-K section diff
│   ├── policies/
│   │   └── gate.py           # Deterministic policy constraint checker
│   ├── receipts/
│   │   └── receipt.py        # SHA-256 audit receipts (policy + proposal hashes)
│   ├── reports/
│   │   └── memo.py           # Markdown research memo builder
│   └── proof_experiments/
│       └── mock_proof.py     # Midnight/Compact ZK proof design (mock)
├── tests/                    # 36 deterministic unit tests
├── docs/                     # Specs, compliance map, proof experiment design
└── examples/                 # Sample policies, proposals, full workflow
```

---

## Quickstart

**1. Clone and install**
```bash
git clone https://github.com/tomasgarro/proofgate-finance
cd proofgate-finance
pip install -r requirements.txt
```

**2. Set up `.env`**
```bash
cp .env.example .env
# Edit .env — minimum required:
# SEC_IDENTITY="Your Name your@email.com"
```

**3. Run**
```bash
# Screen any US equity
python forensic_screener.py AAPL
python forensic_screener.py TSLA NVDA SMCI

# Add AI year-over-year diff (requires ANTHROPIC_API_KEY)
python forensic_screener.py SMCI --diff

# Stricter M-Score threshold (-1.78)
python forensic_screener.py SMCI --strict-m

# Screen DeFi protocols via DefiLlama
python forensic_screener.py --crypto aave uniswap compound

# Save a Markdown report
python forensic_screener.py AAPL TSLA --save-report

# Run all tests
python -m pytest tests/ -v
```

**See [SETUP.md](SETUP.md) for a complete walkthrough** — terminal setup on Windows, every API sign-up, GitHub collaboration.

---

## Policy gate + audit receipts

Beyond research, ProofGate includes a deterministic rule checker and receipt system:

```python
from src.policies.gate import Policy, Proposal, check
from src.receipts.receipt import generate

policy = Policy(
    max_position_pct=5.0,
    allowed_assets=["BTC", "ETH", "ADA"],
    blocked_assets=["LUNA"],
    max_leverage=1.0,
    allowed_venues=["coinbase", "kraken"],
)

proposal = Proposal(
    asset="ETH", action="buy", position_pct=3.0,
    venue="coinbase", leverage=1.0,
)

result = check(policy, proposal)
# GateResult(decision="allow", passed=[...], failed=[])

receipt = generate(policy, proposal, result)
# Receipt with SHA-256 hashes of policy + proposal — tamper-evident audit trail
```

Every decision is labeled with which constraints passed and which failed. No LLM in the gate — fully deterministic, fully auditable.

---

## Roadmap

| Phase | Status | Description |
|---|---|---|
| **1 — Forensic agent** | ✅ Complete | EDGAR ingestion, 4 forensic scores, DefiLlama, policy gate, receipts |
| **2 — Enrichment** | 🔄 In progress | Dune on-chain queries, Xerberus DeFi risk, AI filing diff, Markdown reports |
| **3 — Risk-gated agent** | 📋 Planned | Agent that proposes, checks against policy, and produces receipts autonomously |
| **4 — Midnight proof** | 📋 Planned | Compact circuit to prove `position ≤ private_max` without revealing the max |
| **5 — Strategy licensing** | 🔭 Future | ZK-selective disclosure of strategy parameters to counterparties |

---

## ZK proof experiment (Phase 4)

The core research question: can a trading agent prove it respected a private risk limit — without revealing the limit?

```
prove: proposed_position_pct ≤ private_max_pct
without revealing: private_max_pct
using: Midnight/Compact ZK circuit
```

This is architecturally equivalent to the "CoinAlg Bind" problem in IC3's June 2026 AI × Crypto survey — the bridge between transparent auditability and private strategy edge.

Phase 4 will implement this as a real Compact circuit on Midnight testnet. A Python hash-commitment mock exists in `src/proof_experiments/mock_proof.py`.

---

## Compliance

This is a research and educational project. Not investment advice. Forensic scores are probability flags derived from historical filings — they are not proof of fraud, and do not predict future performance. Scores may be incorrect due to data quality, XBRL mapping gaps, or changes in accounting standards.

ZK proof components verify mathematical constraints, not financial outcomes.

Do your own research. Open the filing.

---

## Contributing

Built in public. Issues and PRs welcome.

Core team: [@tomasgarro](https://github.com/tomasgarro) + collaborators from AI Players and the Midnight/Cardano ecosystem.

Data scientists and mathematicians: see `docs/mvp-spec.md` for the formula implementations and `tests/` for the validation suite.
