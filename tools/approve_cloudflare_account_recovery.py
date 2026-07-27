#!/usr/bin/env python3
"""Issue a one-time GCA device-access recovery credential.

The protected Worker returns the credential once. This tool writes it to an
ignored local file with mode 0600 and never prints the credential or admin
token. The operator must deliver it only to the account's registered email.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
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


APPROVAL_VERSION = "gca_account_status_recovery_approval_v1"
RECOVERY_REQUEST_ID_RE = re.compile(r"^gca_recovery_request_[a-f0-9]{20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
OPERATOR_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
REASON_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")
RECOVERY_CREDENTIAL_RE = re.compile(r"^gca_recovery_[A-Za-z0-9_-]{43}$")


class AccountRecoveryError(RuntimeError):
    """Raised for expected operator-facing recovery failures."""


def build_approval_payload(
    *,
    recovery_request_id: str,
    registered_email: str,
    operator_id: str,
    reason_code: str,
    registered_email_verified: bool = False,
    identity_reviewed: bool = False,
) -> dict[str, Any]:
    clean_request_id = recovery_request_id.strip().lower()
    clean_email = registered_email.strip().lower()
    clean_operator_id = operator_id.strip().lower()
    clean_reason_code = reason_code.strip().lower()
    if not RECOVERY_REQUEST_ID_RE.fullmatch(clean_request_id):
        raise AccountRecoveryError(
            "recovery request id must match gca_recovery_request_ plus 20 lowercase hex characters"
        )
    if len(clean_email) > 254 or not EMAIL_RE.fullmatch(clean_email):
        raise AccountRecoveryError("registered email must be a valid email address")
    if not OPERATOR_ID_RE.fullmatch(clean_operator_id):
        raise AccountRecoveryError("operator id must be a short lowercase identifier")
    if not REASON_CODE_RE.fullmatch(clean_reason_code):
        raise AccountRecoveryError("reason code must be a short lowercase identifier")
    if not registered_email_verified:
        raise AccountRecoveryError(
            "--confirm-registered-email-ownership is required"
        )
    if not identity_reviewed:
        raise AccountRecoveryError("--confirm-manual-identity-review is required")
    return {
        "packetVersion": APPROVAL_VERSION,
        "recoveryRequestId": clean_request_id,
        "registeredEmail": clean_email,
        "operatorId": clean_operator_id,
        "reasonCode": clean_reason_code,
        "source": "gca-account-status-recovery-operator-cli",
        "acknowledgements": {
            "registeredEmailOwnershipVerified": True,
            "manualIdentityReviewCompleted": True,
            "noSecretsRequested": True,
            "noWalletAction": True,
        },
    }


def submit_recovery_approval(
    *,
    base_url: str,
    token: str,
    payload: dict[str, Any],
    timeout: float = 20,
    cafile: str = "",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    request = Request(
        f"{base_url.rstrip('/')}/gca/account-status/recovery-approvals",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "user-agent": "GCA-Operator-Account-Recovery/1.0",
        },
    )
    kwargs: dict[str, Any] = {"timeout": timeout}
    if opener is urlopen:
        ca_path = cafile or os.environ.get("SSL_CERT_FILE", "")
        if not ca_path and Path(DEFAULT_CA_FILE).exists():
            ca_path = DEFAULT_CA_FILE
        if ca_path:
            kwargs["context"] = ssl.create_default_context(cafile=ca_path)
    try:
        with opener(request, **kwargs) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            error_payload = json.loads(exc.read().decode("utf-8"))
            detail = str(error_payload.get("error") or f"HTTP {exc.code}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            detail = f"HTTP {exc.code}"
        raise AccountRecoveryError(
            f"account recovery API rejected the request: {detail}"
        ) from exc
    except URLError as exc:
        raise AccountRecoveryError(
            f"account recovery API request failed: {exc.reason}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise AccountRecoveryError(
            "account recovery API returned invalid JSON"
        ) from exc

    credential = str(result.get("recoveryCredential") or "")
    if result.get("ok") is not True:
        raise AccountRecoveryError("account recovery API did not return ok=true")
    if not RECOVERY_CREDENTIAL_RE.fullmatch(credential):
        raise AccountRecoveryError(
            "account recovery API did not return a valid one-time credential"
        )
    if result.get("recoveryRequestId") != payload["recoveryRequestId"]:
        raise AccountRecoveryError(
            "account recovery API returned a mismatched request id"
        )
    return result


def write_delivery_packet(
    *,
    output: Path,
    registered_email: str,
    result: dict[str, Any],
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    packet = {
        "packetVersion": "gca_account_status_recovery_delivery_v1",
        "recoveryRequestId": result["recoveryRequestId"],
        "registeredEmail": registered_email.strip().lower(),
        "recoveryCredential": result["recoveryCredential"],
        "recoveryCredentialExpiresAt": result.get(
            "recoveryCredentialExpiresAt", ""
        ),
        "deliveryBoundary": (
            "Deliver only to the registered email. Never request or include a "
            "device key, private key, seed phrase, wallet password, signature, "
            "approval, or transaction."
        ),
    }
    encoded = (
        json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        file_descriptor = os.open(output, flags, 0o600)
    except FileExistsError as exc:
        raise AccountRecoveryError(
            f"delivery packet already exists: {output}"
        ) from exc
    with os.fdopen(file_descriptor, "wb") as handle:
        handle.write(encoded)
    os.chmod(output, 0o600)
    return output


def safe_result(result: dict[str, Any], output: Path) -> dict[str, Any]:
    return {
        "ok": True,
        "recoveryRequestId": result.get("recoveryRequestId", ""),
        "status": result.get("status", ""),
        "approvedAt": result.get("approvedAt", ""),
        "recoveryCredentialExpiresAt": result.get(
            "recoveryCredentialExpiresAt", ""
        ),
        "reissued": bool(result.get("reissued", False)),
        "deliveryPacket": str(output),
        "deliveryPacketMode": "0600",
        "registeredEmailOnly": True,
        "adminTokenPrinted": False,
        "recoveryCredentialPrinted": False,
        "walletActionRequired": False,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Issue a one-time, registered-email-only GCA device recovery "
            "credential through the protected production Worker."
        )
    )
    parser.add_argument("--recovery-request-id", required=True)
    parser.add_argument("--registered-email", required=True)
    parser.add_argument("--operator-id", default="gca-operator")
    parser.add_argument("--reason-code", default="registered_email_verified")
    parser.add_argument(
        "--confirm-registered-email-ownership",
        action="store_true",
        help="Required after confirming the request came from the registered mailbox.",
    )
    parser.add_argument(
        "--confirm-manual-identity-review",
        action="store_true",
        help="Required after completing the manual account identity review.",
    )
    parser.add_argument(
        "--confirm-production-write",
        action="store_true",
        help="Required because this command writes an approval to production D1.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Ignored local 0600 delivery file. Default: "
            ".gca_access_data/account_recovery/<request-id>.json"
        ),
    )
    parser.add_argument("--base-url", default=DEFAULT_API_BASE)
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE)
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--cafile", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if not args.confirm_production_write:
            raise AccountRecoveryError("--confirm-production-write is required")
        payload = build_approval_payload(
            recovery_request_id=args.recovery_request_id,
            registered_email=args.registered_email,
            operator_id=args.operator_id,
            reason_code=args.reason_code,
            registered_email_verified=args.confirm_registered_email_ownership,
            identity_reviewed=args.confirm_manual_identity_review,
        )
        token = load_admin_token(args.token_file)
        result = submit_recovery_approval(
            base_url=args.base_url,
            token=token,
            payload=payload,
            timeout=args.timeout,
            cafile=args.cafile,
        )
        output = args.output or (
            ROOT
            / ".gca_access_data"
            / "account_recovery"
            / f"{payload['recoveryRequestId']}.json"
        )
        written = write_delivery_packet(
            output=output,
            registered_email=payload["registeredEmail"],
            result=result,
        )
    except (AccountRecoveryError, ExportError) as exc:
        print(
            json.dumps(
                {"ok": False, "error": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            safe_result(result, written),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
