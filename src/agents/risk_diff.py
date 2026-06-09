"""
L2 AI layer: year-over-year diff on 10-K Risk Factors and MD&A.

This agent fetches two consecutive 10-K filings, extracts the relevant
sections, and uses Claude to identify what changed — new risk language,
removed disclosures, and any material shifts in management narrative.

Usage:
    from src.agents.risk_diff import diff_10k_sections
    result = diff_10k_sections("AAPL", sections=["risk_factors", "mda"])
    print(result.risk_factors_diff)
    print(result.mda_diff)
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DiffResult:
    ticker: str
    risk_factors_diff: Optional[str] = None
    mda_diff: Optional[str] = None
    keyword_flags: list[str] = field(default_factory=list)
    error: Optional[str] = None


_RISK_DIFF_PROMPT = """You are analyzing two consecutive annual 10-K filings for changes in disclosed risk.

Your task: compare THIS YEAR's section against LAST YEAR's section.
Report ONLY:
1. New language added this year (quote it, then explain the risk)
2. Language removed from last year (note what disappeared)
3. Significant rewrites that change the substance of a risk (not just style)

Ignore: boilerplate that appears in both, cosmetic rewordings, formatting changes.

End with one sentence: "VERDICT: [does any change here materially shift the risk picture?]"

LAST YEAR:
{prior}

THIS YEAR:
{current}
"""

_MDA_DIFF_PROMPT = """You are analyzing two consecutive 10-K Management Discussion & Analysis sections.

Your task: compare THIS YEAR's MD&A against LAST YEAR's MD&A.
Report ONLY what is substantively different:
1. New themes, warnings, or trends introduced this year
2. Topics that dropped out entirely
3. Changes in management tone around revenue, margins, liquidity, or outlook

Ignore: normal year-to-year number changes, boilerplate.

End with: "VERDICT: [does the change in narrative signal anything worth investigating?]"

LAST YEAR:
{prior}

THIS YEAR:
{current}
"""

_KEYWORD_FLAGS = [
    "material weakness",
    "going concern",
    "restatement",
    "regulatory investigation",
    "customer concentration",
    "key supplier",
    "covenant breach",
    "liquidity risk",
    "off-balance-sheet",
]

_MAX_SECTION_CHARS = 40_000  # Claude context limit buffer


def diff_10k_sections(
    ticker: str,
    sections: list[str] = None,
    model: str = "claude-opus-4-8",
    identity: Optional[str] = None,
) -> DiffResult:
    """
    Fetch two consecutive 10-K filings and diff the requested sections.

    sections: list of ["risk_factors", "mda"] — defaults to both
    model: Claude model to use for the diff
    identity: SEC identity string "Name email@example.com" (or set SEC_IDENTITY env var)

    Requires ANTHROPIC_API_KEY env var.
    """
    sections = sections or ["risk_factors", "mda"]
    result = DiffResult(ticker=ticker)

    try:
        current_text, prior_text = _fetch_section_texts(ticker, identity)
    except Exception as e:
        result.error = f"Failed to fetch filings: {e}"
        return result

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        result.error = "ANTHROPIC_API_KEY not set — skipping AI diff. Keyword scan still ran."
        result.keyword_flags = _scan_keywords(current_text.get("risk_factors", ""))
        return result

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        result.error = "anthropic package not installed: pip install anthropic"
        return result

    if "risk_factors" in sections and current_text.get("risk_factors") and prior_text.get("risk_factors"):
        result.risk_factors_diff = _run_diff(
            client, model, _RISK_DIFF_PROMPT,
            current=current_text["risk_factors"][:_MAX_SECTION_CHARS],
            prior=prior_text["risk_factors"][:_MAX_SECTION_CHARS],
        )
        result.keyword_flags = _scan_keywords(current_text["risk_factors"])

    if "mda" in sections and current_text.get("mda") and prior_text.get("mda"):
        result.mda_diff = _run_diff(
            client, model, _MDA_DIFF_PROMPT,
            current=current_text["mda"][:_MAX_SECTION_CHARS],
            prior=prior_text["mda"][:_MAX_SECTION_CHARS],
        )

    return result


def _fetch_section_texts(
    ticker: str,
    identity: Optional[str],
) -> tuple[dict[str, str], dict[str, str]]:
    """Fetch Risk Factors and MD&A text from the two most recent 10-K filings."""
    from edgar import Company
    if identity or os.environ.get("SEC_IDENTITY"):
        from edgar import set_identity
        set_identity(identity or os.environ["SEC_IDENTITY"])

    company = Company(ticker)
    filings = company.get_filings(form="10-K").latest(2)

    if len(filings) < 2:
        raise ValueError(f"Could not find 2 consecutive 10-K filings for {ticker}")

    def extract_sections(filing) -> dict[str, str]:
        ten_k = filing.obj()
        texts = {}
        # Risk Factors = Item 1A
        rf = getattr(ten_k, "risk_factors", None)
        if rf is not None:
            texts["risk_factors"] = str(rf) if not isinstance(rf, str) else rf
        # MD&A = Item 7
        mda = getattr(ten_k, "management_discussion", None)
        if mda is not None:
            texts["mda"] = str(mda) if not isinstance(mda, str) else mda
        return texts

    current_texts = extract_sections(filings[0])
    prior_texts = extract_sections(filings[1])
    return current_texts, prior_texts


def _run_diff(client, model: str, prompt_template: str, current: str, prior: str) -> str:
    """Run the diff prompt through Claude."""
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": prompt_template.format(current=current, prior=prior)
            }],
        )
        return msg.content[0].text
    except Exception as e:
        return f"[Diff failed: {e}]"


def _scan_keywords(text: str) -> list[str]:
    """
    Scan section text for red-flag keywords without AI.
    Returns list of found flags. Fast and free.
    """
    text_lower = text.lower()
    found = []
    for kw in _KEYWORD_FLAGS:
        if kw in text_lower:
            found.append(kw)
    return found


def full_text_search_market(query: str, form: str = "10-K", limit: int = 20) -> list[dict]:
    """
    EDGAR full-text search across all filings.

    Example: find all companies that recently disclosed "material weakness":
        results = full_text_search_market("material weakness")

    Returns list of dicts with ticker, company_name, filing_date, filing_url.
    """
    try:
        from edgar import TextSearch
        results = TextSearch.search(query, form=form, hits=limit)
        return [
            {
                "ticker": getattr(r, "ticker", None),
                "company_name": getattr(r, "company_name", str(r)),
                "filing_date": getattr(r, "filing_date", None),
            }
            for r in results
        ]
    except Exception as e:
        return [{"error": str(e)}]
