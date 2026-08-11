#!/usr/bin/env python3
"""Read and validate the official GCA/USDT GeckoTerminal pool snapshot.

This checker is public and read-only. It validates the exact network, pool,
token, quote-asset, and DEX identifiers before exposing aggregate market data.
It never connects a wallet, builds a quote, signs, or submits a transaction.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import certifi
except ImportError:  # pragma: no cover - system CA stores may already work.
    certifi = None


NETWORK = "base"
CHAIN_ID = 8453
POOL_ADDRESS = "0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0"
GCA_ADDRESS = "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6"
USDT_ADDRESS = "0xfde4c96c8593536e31f229ea8f37b2ada2699bb2"
DEX_ID = "uniswap-v4-base"
API_VERSION = "20230302"
API_URL = f"https://api.geckoterminal.com/api/v2/networks/{NETWORK}/pools/{POOL_ADDRESS}"
PUBLIC_POOL_URL = f"https://www.geckoterminal.com/{NETWORK}/pools/{POOL_ADDRESS}"
USER_AGENT = "GCA-Market-Health-Checker/1.0 (+https://gcagochina.com/)"
MAX_RESPONSE_BYTES = 65_536


class MarketHealthCheckError(RuntimeError):
    """Raised when the public market snapshot cannot be safely classified."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MarketHealthCheckError(f"JSON fixture not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise MarketHealthCheckError(f"JSON fixture is not UTF-8: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MarketHealthCheckError(f"JSON fixture is invalid: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise MarketHealthCheckError("market response must be a JSON object")
    return payload


def fetch_json(url: str, timeout: float) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": f"application/json;version={API_VERSION}",
        },
    )
    ssl_context = (
        ssl.create_default_context(cafile=certifi.where())
        if certifi is not None
        else ssl.create_default_context()
    )
    try:
        with urlopen(request, timeout=timeout, context=ssl_context) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise MarketHealthCheckError(f"GeckoTerminal returned HTTP {status}")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise MarketHealthCheckError(f"GeckoTerminal returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise MarketHealthCheckError(f"Could not read GeckoTerminal: {exc.reason}") from exc
    except TimeoutError as exc:
        raise MarketHealthCheckError(
            f"GeckoTerminal request timed out after {timeout:g} seconds"
        ) from exc

    if len(raw) > MAX_RESPONSE_BYTES:
        raise MarketHealthCheckError("GeckoTerminal response exceeded the size limit")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MarketHealthCheckError("GeckoTerminal returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise MarketHealthCheckError("GeckoTerminal response must be a JSON object")
    return payload


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MarketHealthCheckError(f"{label} must be an object")
    return value


def decimal_string(value: Any, label: str, *, nonnegative: bool = False) -> str:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise MarketHealthCheckError(f"{label} must be numeric") from exc
    if not number.is_finite():
        raise MarketHealthCheckError(f"{label} must be finite")
    if nonnegative and number < 0:
        raise MarketHealthCheckError(f"{label} must be non-negative")
    normalized = format(number, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise MarketHealthCheckError(f"{label} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise MarketHealthCheckError(f"{label} must be an integer") from exc
    if number < 0 or str(number) != str(value):
        raise MarketHealthCheckError(f"{label} must be a non-negative integer")
    return number


def classify_market(payload: dict[str, Any], *, checked_at: str | None = None) -> dict[str, Any]:
    data = require_object(payload.get("data"), "data")
    attributes = require_object(data.get("attributes"), "data.attributes")
    relationships = require_object(data.get("relationships"), "data.relationships")

    expected_pool_id = f"{NETWORK}_{POOL_ADDRESS}"
    expected_gca_id = f"{NETWORK}_{GCA_ADDRESS}"
    expected_usdt_id = f"{NETWORK}_{USDT_ADDRESS}"
    base_token = require_object(
        require_object(relationships.get("base_token"), "base_token").get("data"),
        "base_token.data",
    )
    quote_token = require_object(
        require_object(relationships.get("quote_token"), "quote_token").get("data"),
        "quote_token.data",
    )
    dex = require_object(
        require_object(relationships.get("dex"), "dex").get("data"),
        "dex.data",
    )
    identity = {
        "poolId": str(data.get("id") or "").lower(),
        "poolType": str(data.get("type") or ""),
        "poolAddress": str(attributes.get("address") or "").lower(),
        "baseTokenId": str(base_token.get("id") or "").lower(),
        "quoteTokenId": str(quote_token.get("id") or "").lower(),
        "dexId": str(dex.get("id") or ""),
    }
    expected = {
        "poolId": expected_pool_id,
        "poolType": "pool",
        "poolAddress": POOL_ADDRESS,
        "baseTokenId": expected_gca_id,
        "quoteTokenId": expected_usdt_id,
        "dexId": DEX_ID,
    }
    mismatches = [key for key, expected_value in expected.items() if identity[key] != expected_value]
    if mismatches:
        raise MarketHealthCheckError(
            "official pool identity mismatch: " + ", ".join(mismatches)
        )

    volume = require_object(attributes.get("volume_usd"), "volume_usd")
    transactions = require_object(attributes.get("transactions"), "transactions")
    transactions_24h = require_object(transactions.get("h24"), "transactions.h24")
    price_change = require_object(
        attributes.get("price_change_percentage"),
        "price_change_percentage",
    )
    buys = nonnegative_int(transactions_24h.get("buys"), "transactions.h24.buys")
    sells = nonnegative_int(transactions_24h.get("sells"), "transactions.h24.sells")
    buyers = nonnegative_int(transactions_24h.get("buyers"), "transactions.h24.buyers")
    sellers = nonnegative_int(transactions_24h.get("sellers"), "transactions.h24.sellers")
    total_transactions = buys + sells

    return {
        "ok": True,
        "packetVersion": "gca_market_health_check_v1",
        "checkedAt": checked_at or utc_now(),
        "status": "official-pool-observed",
        "identityVerified": True,
        "network": "Base Mainnet",
        "networkId": NETWORK,
        "chainId": CHAIN_ID,
        "contractAddress": GCA_ADDRESS,
        "quoteAssetAddress": USDT_ADDRESS,
        "poolAddress": POOL_ADDRESS,
        "dexId": DEX_ID,
        "source": {
            "provider": "GeckoTerminal Public API",
            "apiVersion": API_VERSION,
            "apiUrl": API_URL,
            "publicPoolUrl": PUBLIC_POOL_URL,
        },
        "observed": {
            "poolName": str(attributes.get("name") or ""),
            "poolCreatedAt": str(attributes.get("pool_created_at") or ""),
            "baseTokenPriceUsd": decimal_string(
                attributes.get("base_token_price_usd"),
                "base_token_price_usd",
                nonnegative=True,
            ),
            "reserveInUsd": decimal_string(
                attributes.get("reserve_in_usd"),
                "reserve_in_usd",
                nonnegative=True,
            ),
            "volumeUsd24h": decimal_string(
                volume.get("h24"),
                "volume_usd.h24",
                nonnegative=True,
            ),
            "priceChangePercentage24h": decimal_string(
                price_change.get("h24"),
                "price_change_percentage.h24",
            ),
            "transactions24h": {
                "buys": buys,
                "sells": sells,
                "buyers": buyers,
                "sellers": sellers,
                "total": total_transactions,
            },
        },
        "interpretation": {
            "liquidityDepthStatus": "starter-depth-only",
            "activityStatus": (
                "24h-transactions-observed"
                if total_transactions > 0
                else "no-24h-transactions-observed"
            ),
            "doesNotProveOrganicDemand": True,
            "nextAction": (
                "Keep the official route consistent and improve market quality through "
                "transparent liquidity, product delivery, and legitimate participation."
            ),
        },
        "boundaries": {
            "readOnlyPublicApi": True,
            "connectsWallet": False,
            "buildsExecutableQuote": False,
            "submitsTrade": False,
            "signsMessage": False,
            "requiresTransaction": False,
            "claimsDeepLiquidity": False,
            "claimsOrganicDemand": False,
            "claimsPriceSupport": False,
        },
    }


def check_market_health(
    *,
    api_url: str = API_URL,
    json_file: Path | None = None,
    timeout: float = 20,
    checked_at: str | None = None,
) -> dict[str, Any]:
    payload = load_json_file(json_file) if json_file is not None else fetch_json(api_url, timeout)
    result = classify_market(payload, checked_at=checked_at)
    result["source"]["apiUrl"] = api_url
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read and validate the official GCA/USDT GeckoTerminal pool snapshot."
    )
    parser.add_argument("--api-url", default=API_URL)
    parser.add_argument("--json-file", type=Path, help="Use a local JSON fixture instead of the network.")
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--checked-at", help="Override the UTC timestamp for deterministic fixtures.")
    parser.add_argument("--json", action="store_true", help="Print the complete JSON result.")
    return parser.parse_args(argv)


def failure_payload(error: str) -> dict[str, Any]:
    return {
        "ok": False,
        "packetVersion": "gca_market_health_check_v1",
        "checkedAt": utc_now(),
        "status": "market-snapshot-unavailable",
        "identityVerified": False,
        "error": error,
        "network": "Base Mainnet",
        "chainId": CHAIN_ID,
        "contractAddress": GCA_ADDRESS,
        "poolAddress": POOL_ADDRESS,
        "boundaries": {
            "readOnlyPublicApi": True,
            "connectsWallet": False,
            "buildsExecutableQuote": False,
            "submitsTrade": False,
            "signsMessage": False,
            "requiresTransaction": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = check_market_health(
            api_url=args.api_url,
            json_file=args.json_file,
            timeout=args.timeout,
            checked_at=args.checked_at,
        )
    except MarketHealthCheckError as exc:
        payload = failure_payload(str(exc))
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 2

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        observed = payload["observed"]
        print(
            f"{payload['status']}: reserve ${observed['reserveInUsd']}; "
            f"24h volume ${observed['volumeUsd24h']}; "
            f"24h transactions {observed['transactions24h']['total']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
