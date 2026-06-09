"""
Xerberus Risk API client.

Xerberus provides on-chain risk scores for Cardano, Ethereum, and Polygon tokens,
protocols, vaults, and DeFi pools. It is especially strong on Cardano native assets.

Docs:     https://xerberus.gitbook.io/documentation/apis/risk-ratings-api
Base URL: https://api.xerberus.io/public/v1
Auth:     x-api-key header + x-user-email header (both required)

To get an API key:
  1. Email ms@xerberus.io with your use case
  OR
  2. Register at https://app.xerberus.io and check Settings → API

Set in .env:
  XERBERUS_API_KEY=your_key_here
  XERBERUS_EMAIL=your@email.com
"""

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional


BASE_URL = "https://api.xerberus.io/public/v1"

_RATING_LABELS = {
    "AAA": "Minimal risk",
    "AA": "Very low risk",
    "A": "Low risk",
    "BBB": "Moderate risk",
    "BB": "Moderate-high risk",
    "B": "High risk",
    "CCC": "Very high risk",
    "CC": "Extreme risk",
    "C": "Near default",
    "D": "Default / rug risk",
}


@dataclass
class XerberusRating:
    asset_id: str              # policy_id.asset_name (Cardano) or contract address (EVM)
    ticker: str
    chain: str                 # "cardano" | "ethereum" | "polygon"
    rating: str                # "AAA" through "D"
    rating_label: str
    risk_score: float          # 0–100, higher = riskier
    liquidity_score: Optional[float]
    volatility_score: Optional[float]
    raw: dict = field(default_factory=dict, repr=False)

    def summary(self) -> str:
        return (
            f"Xerberus Risk: {self.ticker} ({self.chain})  "
            f"Rating: {self.rating} — {self.rating_label}  "
            f"Risk score: {self.risk_score:.1f}/100"
        )

    @property
    def flag(self) -> str:
        if self.rating in ("CCC", "CC", "C", "D"):
            return "HIGH_RISK"
        if self.rating in ("B", "BB"):
            return "ELEVATED"
        if self.rating in ("BBB",):
            return "WATCH"
        return "CLEAN"


@dataclass
class XerberusVaultRisk:
    vault_id: str
    protocol: str
    chain: str
    rating: str
    rating_label: str
    risk_score: float
    tvl_usd: float
    raw: dict = field(default_factory=dict, repr=False)

    def summary(self) -> str:
        return (
            f"Vault Risk: {self.protocol} ({self.chain})  "
            f"Rating: {self.rating} — {self.rating_label}  "
            f"TVL: ${self.tvl_usd:,.0f}  Risk: {self.risk_score:.1f}/100"
        )


def _get_headers() -> dict:
    api_key = os.getenv("XERBERUS_API_KEY", "")
    email = os.getenv("XERBERUS_EMAIL", "")
    if not api_key:
        raise EnvironmentError(
            "XERBERUS_API_KEY not set. "
            "Email ms@xerberus.io to request access or register at https://app.xerberus.io"
        )
    if not email:
        raise EnvironmentError("XERBERUS_EMAIL not set. Both key and email are required.")
    return {
        "x-api-key": api_key,
        "x-user-email": email,
        "Content-Type": "application/json",
    }


def _request(path: str, params: Optional[dict] = None) -> dict:
    url = f"{BASE_URL}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"
    headers = _get_headers()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"Xerberus API error {e.code}: {body}") from e


def get_token_risk(asset_id: str, chain: str = "cardano") -> XerberusRating:
    """
    Fetch risk rating for a single token.

    For Cardano: asset_id is the full policy_id.asset_name hex string.
    For EVM chains: asset_id is the contract address.

    Example:
        ada = get_token_risk("lovelace", chain="cardano")
        link = get_token_risk("0x514910771af9ca656af840dff83e8264ecf986ca", chain="ethereum")
    """
    data = _request("/risk/token", {"asset_id": asset_id, "chain": chain})

    rating = data.get("rating", "UNKNOWN")
    return XerberusRating(
        asset_id=asset_id,
        ticker=data.get("ticker", asset_id[:12] + "..."),
        chain=chain,
        rating=rating,
        rating_label=_RATING_LABELS.get(rating, "Unknown rating"),
        risk_score=float(data.get("risk_score", 0)),
        liquidity_score=data.get("liquidity_score"),
        volatility_score=data.get("volatility_score"),
        raw=data,
    )


def get_protocol_risk(protocol_id: str, chain: str = "cardano") -> XerberusRating:
    """Fetch risk rating for a protocol (organization-level risk)."""
    data = _request("/risk/protocol", {"protocol_id": protocol_id, "chain": chain})

    rating = data.get("rating", "UNKNOWN")
    return XerberusRating(
        asset_id=protocol_id,
        ticker=data.get("name", protocol_id),
        chain=chain,
        rating=rating,
        rating_label=_RATING_LABELS.get(rating, "Unknown rating"),
        risk_score=float(data.get("risk_score", 0)),
        liquidity_score=data.get("liquidity_score"),
        volatility_score=data.get("volatility_score"),
        raw=data,
    )


def get_vault_risk(vault_id: str, chain: str = "cardano") -> XerberusVaultRisk:
    """
    Fetch risk score for a specific vault or DeFi pool.

    Vaults are used by protocols like Liqwid, Indigo, Minswap on Cardano
    or Aave, Compound on Ethereum.
    """
    data = _request("/vault/risk", {"vault_id": vault_id, "chain": chain})

    rating = data.get("rating", "UNKNOWN")
    return XerberusVaultRisk(
        vault_id=vault_id,
        protocol=data.get("protocol", "unknown"),
        chain=chain,
        rating=rating,
        rating_label=_RATING_LABELS.get(rating, "Unknown rating"),
        risk_score=float(data.get("risk_score", 0)),
        tvl_usd=float(data.get("tvl_usd", 0)),
        raw=data,
    )


def search_assets(query: str, chain: Optional[str] = None) -> list[dict]:
    """
    Search for assets by name or ticker across chains.

    Returns a list of dicts with keys: asset_id, ticker, chain, rating.
    Use this to look up the asset_id for a token before calling get_token_risk().
    """
    params: dict = {"query": query}
    if chain:
        params["chain"] = chain
    data = _request("/registry/search", params)
    return data.get("assets", [])


def get_wallet_risk(address: str, chain: str = "cardano") -> dict:
    """
    Get risk profile for a wallet address.

    Returns a dict with keys like:
      risk_score, concentration_score, defi_exposure, flagged_protocols
    """
    return _request("/wallet/risk", {"address": address, "chain": chain})
