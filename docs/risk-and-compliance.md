# Risk and Compliance Map

## Framing

ProofGate Finance v1 is research software. All activity is simulated, educational, and non-custodial.

## Safe v1 framing

- Research software for financial analysis.
- Educational forensic scoring tool.
- No custody of user assets.
- No automated trade execution.
- No personalized investment advice.
- No performance promises.
- Simulated environment only for policy gate demos.

## Risky areas to avoid in v1

| Area | Risk | Avoidance |
|---|---|---|
| Placing real trades | Broker-dealer / investment advisor regulation | No execution capability in v1 |
| Managing user assets | Custody / fund management regulation | No custody, no API key handling |
| Personalized buy/sell instructions | Investment advice regulation | Agent outputs are research, not advice |
| Copy-trading | Regulatory classification varies by jurisdiction | Not implemented |
| Performance fees | Securities law, fund regulation | Not implemented |
| Exchange API key handling | Security and legal risk | Not in scope |
| Alpha or return marketing | FTC, securities law | Explicitly disclaimed |

## Required disclaimers

Include on all outputs and in the UI:

```
For research and educational purposes only.
Not investment advice.
Forensic scores are probability indicators, not proof of fraud or financial distress.
ZK proofs verify constraints, not profitability.
Simulated results do not predict future performance.
Past performance of any described strategy does not predict future results.
```

## Leakage risks to document

Even in simulation, repeated outputs from a private strategy can leak information:

- Trade timing patterns
- Asset selection patterns
- Position sizing patterns
- Allow/reject rate from a strategy
- Frequency of constraint violations
- Correlation of outputs with market events

Leakage analysis should be part of Phase 4 deliverables.

## Jurisdiction notes

No specific jurisdiction is targeted in v1.

Before any commercialization or user-facing product launch, consult legal counsel on:
- Whether the research agent constitutes investment advice in target jurisdiction.
- Whether the strategy sandbox constitutes investment services.
- Whether the policy gate constitutes financial infrastructure requiring licensing.
- Data usage rights for SEC EDGAR and third-party financial data.

## Data usage

| Source | License / Terms |
|---|---|
| SEC EDGAR | Public domain, free, no attribution required |
| FinancialModelingPrep | Requires API key, free tier has limits, review ToS |
| yfinance | Yahoo Finance data, personal/research use only, review ToS |
| On-chain data | Varies by provider; review ToS |

## Security notes

- No API keys should be hardcoded. Use environment variables.
- Policy files should be stored locally and never transmitted without user consent.
- Receipt hashes are one-way and do not expose policy content.
- Proof experiments must clearly label simulated outputs vs real ZK proofs.
