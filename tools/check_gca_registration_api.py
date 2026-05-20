#!/usr/bin/env python3
"""Read-only smoke checks for the live GCA registration API.

This checks the Cloudflare Worker health endpoint, CORS preflight behavior,
unauthorized admin-read rejection, and token-protected admin-read response
shape. It does not submit registrations, does not write production data, and
does not print the admin token or user email records.
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.export_cloudflare_email_registrations import (  # noqa: E402
    DEFAULT_API_BASE,
    DEFAULT_CA_FILE,
    DEFAULT_TOKEN_FILE,
    ExportError,
    load_admin_token,
)


DEFAULT_ORIGIN = "https://gcagochina.com"
DEFAULT_USER_AGENT = "GCA-Operator-Registration-API-Check/1.0"


class ApiCheckError(RuntimeError):
    """Raised for expected operator-facing API check failures."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_url(base_url: str, path: str, query: dict[str, str] | None = None) -> str:
    clean_base = base_url.rstrip("/")
    clean_path = path if path.startswith("/") else f"/{path}"
    if query:
        return f"{clean_base}{clean_path}?{urlencode(query)}"
    return f"{clean_base}{clean_path}"


def response_headers(response: Any) -> dict[str, str]:
    headers = getattr(response, "headers", {})
    if hasattr(headers, "items"):
        return {str(key).lower(): str(value) for key, value in headers.items()}
    return {}


def read_response_body(response: Any) -> bytes:
    body = response.read()
    if isinstance(body, str):
        return body.encode("utf-8")
    return body


def parse_json_body(raw_body: bytes, *, url: str, allow_empty: bool = False) -> Any:
    if not raw_body:
        if allow_empty:
            return {}
        raise ApiCheckError(f"{url} returned an empty response body")
    try:
        return json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ApiCheckError(f"{url} returned invalid JSON") from exc


def http_json_request(
    *,
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    timeout: float = 20,
    cafile: str = "",
    opener: Callable[..., Any] = urlopen,
    allow_error_status: bool = False,
    allow_empty: bool = False,
) -> tuple[int, dict[str, str], Any]:
    request_headers = {"user-agent": DEFAULT_USER_AGENT}
    request_headers.update(headers or {})
    request = Request(url, method=method, headers=request_headers)
    kwargs: dict[str, Any] = {"timeout": timeout}
    if opener is urlopen:
        ca_path = cafile or os.environ.get("SSL_CERT_FILE", "")
        if not ca_path and Path(DEFAULT_CA_FILE).exists():
            ca_path = DEFAULT_CA_FILE
        if ca_path:
            kwargs["context"] = ssl.create_default_context(cafile=ca_path)
    try:
        with opener(request, **kwargs) as response:
            status = int(getattr(response, "status", getattr(response, "code", 200)))
            return status, response_headers(response), parse_json_body(
                read_response_body(response),
                url=url,
                allow_empty=allow_empty,
            )
    except HTTPError as exc:
        if not allow_error_status:
            raise ApiCheckError(f"{url} returned HTTP {exc.code}") from exc
        return exc.code, response_headers(exc), parse_json_body(
            exc.read(),
            url=url,
            allow_empty=allow_empty,
        )
    except URLError as exc:
        raise ApiCheckError(f"{url} request failed: {exc.reason}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ApiCheckError(message)


def check_health(*, base_url: str, timeout: float, cafile: str, opener: Callable[..., Any]) -> dict[str, Any]:
    url = build_url(base_url, "/health")
    status, _, payload = http_json_request(url=url, timeout=timeout, cafile=cafile, opener=opener)
    require(status == 200, "health endpoint must return HTTP 200")
    require(payload.get("ok") is True, "health endpoint must return ok=true")
    require(payload.get("service") == "gca-registration-api", "health endpoint returned wrong service")
    require(payload.get("storage") == "cloudflare-d1", "health endpoint returned wrong storage")
    require(payload.get("packetVersion") == "gca_email_registration_v1", "health endpoint returned wrong email packet version")
    require(payload.get("contactSuppressionVersion") == "gca_contact_suppression_v1", "health endpoint returned wrong suppression packet version")
    return {
        "id": "health",
        "ok": True,
        "status": status,
        "service": payload.get("service"),
        "storage": payload.get("storage"),
        "packetVersion": payload.get("packetVersion"),
        "contactSuppressionVersion": payload.get("contactSuppressionVersion"),
    }


def check_cors_preflight(
    *,
    base_url: str,
    path: str,
    check_id: str,
    origin: str,
    timeout: float,
    cafile: str,
    opener: Callable[..., Any],
) -> dict[str, Any]:
    url = build_url(base_url, path)
    status, headers, _ = http_json_request(
        url=url,
        method="OPTIONS",
        headers={
            "origin": origin,
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
        timeout=timeout,
        cafile=cafile,
        opener=opener,
        allow_empty=True,
    )
    require(status == 204, f"{path} preflight must return HTTP 204")
    require(headers.get("access-control-allow-origin") == origin, f"{path} preflight returned wrong allow-origin")
    require("POST" in headers.get("access-control-allow-methods", ""), f"{path} preflight must allow POST")
    return {
        "id": check_id,
        "ok": True,
        "status": status,
        "allowOrigin": headers.get("access-control-allow-origin"),
        "allowMethods": headers.get("access-control-allow-methods"),
    }


def check_unauthorized_admin_read(
    *,
    base_url: str,
    path: str,
    check_id: str,
    timeout: float,
    cafile: str,
    opener: Callable[..., Any],
) -> dict[str, Any]:
    url = build_url(base_url, path, {"limit": "1"})
    status, _, payload = http_json_request(
        url=url,
        timeout=timeout,
        cafile=cafile,
        opener=opener,
        allow_error_status=True,
    )
    require(status == 401, f"{path} must reject unauthenticated admin reads with HTTP 401")
    require(payload.get("ok") is False, f"{path} unauthorized response must return ok=false")
    return {
        "id": check_id,
        "ok": True,
        "status": status,
        "rejectedWithoutToken": True,
    }


def check_authorized_admin_read(
    *,
    base_url: str,
    path: str,
    check_id: str,
    token: str,
    limit: int,
    timeout: float,
    cafile: str,
    opener: Callable[..., Any],
) -> dict[str, Any]:
    url = build_url(base_url, path, {"limit": str(limit)})
    status, _, payload = http_json_request(
        url=url,
        headers={
            "authorization": f"Bearer {token}",
            "user-agent": DEFAULT_USER_AGENT,
        },
        timeout=timeout,
        cafile=cafile,
        opener=opener,
    )
    records = payload.get("records")
    require(status == 200, f"{path} admin read must return HTTP 200")
    require(payload.get("ok") is True, f"{path} admin read must return ok=true")
    require(isinstance(records, list), f"{path} admin read must return records[]")
    return {
        "id": check_id,
        "ok": True,
        "status": status,
        "count": int(payload.get("count", len(records))),
        "recordsReturned": len(records),
        "recordsPrinted": False,
        "adminTokenPrinted": False,
    }


def run_checks(
    *,
    base_url: str,
    token: str,
    origin: str = DEFAULT_ORIGIN,
    limit: int = 5,
    timeout: float = 20,
    cafile: str = "",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    if limit < 1 or limit > 100:
        raise ApiCheckError("limit must be between 1 and 100")
    checks = [
        check_health(base_url=base_url, timeout=timeout, cafile=cafile, opener=opener),
        check_cors_preflight(
            base_url=base_url,
            path="/gca/email-registrations",
            check_id="cors-email-registrations",
            origin=origin,
            timeout=timeout,
            cafile=cafile,
            opener=opener,
        ),
        check_cors_preflight(
            base_url=base_url,
            path="/gca/contact-suppressions",
            check_id="cors-contact-suppressions",
            origin=origin,
            timeout=timeout,
            cafile=cafile,
            opener=opener,
        ),
        check_unauthorized_admin_read(
            base_url=base_url,
            path="/gca/email-registrations",
            check_id="unauth-email-registrations-read",
            timeout=timeout,
            cafile=cafile,
            opener=opener,
        ),
        check_unauthorized_admin_read(
            base_url=base_url,
            path="/gca/contact-suppressions",
            check_id="unauth-contact-suppressions-read",
            timeout=timeout,
            cafile=cafile,
            opener=opener,
        ),
        check_authorized_admin_read(
            base_url=base_url,
            path="/gca/email-registrations",
            check_id="admin-email-registrations-read",
            token=token,
            limit=limit,
            timeout=timeout,
            cafile=cafile,
            opener=opener,
        ),
        check_authorized_admin_read(
            base_url=base_url,
            path="/gca/contact-suppressions",
            check_id="admin-contact-suppressions-read",
            token=token,
            limit=limit,
            timeout=timeout,
            cafile=cafile,
            opener=opener,
        ),
    ]
    return {
        "ok": all(item["ok"] for item in checks),
        "checkedAt": utc_now(),
        "baseUrl": base_url.rstrip("/"),
        "origin": origin,
        "checks": checks,
        "boundaries": {
            "readOnlySmokeCheck": True,
            "writesProductionData": False,
            "submitsRegistration": False,
            "submitsContactSuppression": False,
            "adminTokenPrinted": False,
            "userEmailsPrinted": False,
            "walletConnectionRequired": False,
            "signatureRequired": False,
            "transactionRequired": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run read-only smoke checks against the live GCA registration API.")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE, help=f"Worker API base URL. Default: {DEFAULT_API_BASE}")
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE, help="Path to ignored local admin env file.")
    parser.add_argument("--origin", default=DEFAULT_ORIGIN, help=f"CORS origin to verify. Default: {DEFAULT_ORIGIN}")
    parser.add_argument("--limit", type=int, default=5, help="Maximum admin records to count, 1-100. Default: 5.")
    parser.add_argument("--timeout", type=float, default=20, help="HTTP timeout in seconds. Default: 20.")
    parser.add_argument("--cafile", default="", help=f"Optional CA bundle path. Default fallback: {DEFAULT_CA_FILE}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        token = load_admin_token(args.token_file)
        result = run_checks(
            base_url=args.base_url,
            token=token,
            origin=args.origin,
            limit=args.limit,
            timeout=args.timeout,
            cafile=args.cafile,
        )
    except (ApiCheckError, ExportError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
