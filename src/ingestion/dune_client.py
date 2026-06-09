"""
Dune Analytics client.

Dune has 100,000+ community-built dashboards querying blockchain data via SQL.
Free tier: 2,500 credits/month (metadata endpoints are free, execution costs credits).

Use cases for ProofGate Finance:
- Token holder distribution (who holds the most, are they wallets or exchanges?)
- Protocol fee revenue on-chain vs what DefiLlama reports
- Unlock cliff schedules from vesting contracts
- DEX volume and liquidity depth over time
- Smart money wallet flows (if public queries exist)

Sign up: https://dune.com/auth/register
API key: https://dune.com/settings/api

Set in .env:
  DUNE_API_KEY=your_key_here

Docs: https://docs.dune.com/api-reference/overview/introduction
Python SDK: pip install dune-client (recommended for production use)
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional


BASE_URL = "https://api.dune.com/api/v1"

# Pre-built community queries useful for ProofGate research.
# Find more at: https://dune.com/discover/content/trending
KNOWN_QUERIES = {
    # Token holder distributions
    "ada_top_holders":       3468423,   # Top ADA holders (Cardano)
    "eth_top_holders":       2870285,   # ETH whale tracker
    # Protocol revenue
    "defi_protocol_revenue": 2538043,   # Aggregated protocol fees and revenue
    "uniswap_fees":          3325567,   # Uniswap v3 fees by pool
    "aave_revenue":          2058604,   # Aave protocol revenue
    # Token unlocks
    "linear_vesting":        2951840,   # Linear vesting contract flows
    # DEX
    "dex_aggregator_volume": 2694293,   # DEX aggregated volume across chains
}


@dataclass
class QueryResult:
    query_id: int
    execution_id: str
    state: str               # "QUERY_STATE_COMPLETED" | "QUERY_STATE_PENDING" | etc.
    rows: list[dict] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.state == "QUERY_STATE_COMPLETED" and self.error is None

    def to_dataframe(self):
        """Convert result rows to a pandas DataFrame (requires pandas)."""
        import pandas as pd  # noqa: PLC0415
        return pd.DataFrame(self.rows, columns=self.columns or None)


def _get_headers() -> dict:
    api_key = os.getenv("DUNE_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "DUNE_API_KEY not set. "
            "Sign up at https://dune.com and get your key at https://dune.com/settings/api"
        )
    return {
        "X-DUNE-API-KEY": api_key,
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, body: Optional[dict] = None) -> dict:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_get_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        raise RuntimeError(f"Dune API error {e.code}: {body_text}") from e


def execute_query(
    query_id: int,
    params: Optional[dict] = None,
    wait: bool = True,
    timeout_s: int = 60,
) -> QueryResult:
    """
    Execute a Dune query by ID and return the results.

    Args:
        query_id:  The integer ID from the Dune URL, e.g. dune.com/queries/2538043
        params:    Optional dict of query parameters (only used for parameterized queries)
        wait:      If True, poll until complete (blocks up to timeout_s seconds)
        timeout_s: Max seconds to wait for a PENDING query to finish

    Example:
        result = execute_query(KNOWN_QUERIES["defi_protocol_revenue"])
        for row in result.rows[:10]:
            print(row)
    """
    body: dict = {}
    if params:
        body["query_parameters"] = [
            {"name": k, "value": v} for k, v in params.items()
        ]

    resp = _request("POST", f"/query/{query_id}/execute", body)
    execution_id = resp["execution_id"]

    if not wait:
        return QueryResult(
            query_id=query_id,
            execution_id=execution_id,
            state="QUERY_STATE_PENDING",
        )

    return _wait_for_result(query_id, execution_id, timeout_s)


def get_latest_result(query_id: int) -> QueryResult:
    """
    Fetch the most recent cached result for a query — no credits consumed.

    This is the cheapest way to pull data from popular community queries.
    Results may be hours old. For fresh data, use execute_query() instead.
    """
    resp = _request("GET", f"/query/{query_id}/results")
    return _parse_result(query_id, resp)


def _wait_for_result(
    query_id: int, execution_id: str, timeout_s: int
) -> QueryResult:
    """Poll until execution completes or times out."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        resp = _request("GET", f"/execution/{execution_id}/status")
        state = resp.get("state", "")
        if state == "QUERY_STATE_COMPLETED":
            result_resp = _request("GET", f"/execution/{execution_id}/results")
            return _parse_result(query_id, result_resp)
        if state in ("QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"):
            return QueryResult(
                query_id=query_id,
                execution_id=execution_id,
                state=state,
                error=resp.get("error", {}).get("message", state),
            )
        time.sleep(2)

    return QueryResult(
        query_id=query_id,
        execution_id=execution_id,
        state="TIMEOUT",
        error=f"Query did not complete within {timeout_s}s",
    )


def _parse_result(query_id: int, resp: dict) -> QueryResult:
    result = resp.get("result", {})
    rows_raw = result.get("rows", [])
    meta = result.get("metadata", {})
    columns = [c.get("name", "") for c in meta.get("column_names", [])] if meta else []

    return QueryResult(
        query_id=query_id,
        execution_id=resp.get("execution_id", ""),
        state=resp.get("state", "QUERY_STATE_COMPLETED"),
        rows=rows_raw,
        columns=columns,
        metadata=meta,
    )


def search_queries(keyword: str, limit: int = 10) -> list[dict]:
    """
    Search public Dune queries by keyword.
    Returns list of dicts with keys: query_id, name, description, author.

    Example:
        results = search_queries("cardano ADA holders")
    """
    resp = _request("GET", f"/query/search?q={urllib.parse.quote(keyword)}&limit={limit}")
    return resp.get("results", [])


def get_usage() -> dict:
    """Return current API credit usage for the month."""
    return _request("GET", "/user/usage")
