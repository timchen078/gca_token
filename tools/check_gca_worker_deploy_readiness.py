#!/usr/bin/env python3
"""Check whether the GCA Cloudflare Worker is ready to deploy.

The default mode is static and local. Optional Wrangler checks are read-only or
dry-run only: this script never writes D1 records, deploys a Worker, prints
ADMIN_READ_TOKEN, or reads user ledgers.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    tomllib = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
WORKER_DIR = ROOT / "cloudflare" / "gca-registration-worker"
WRANGLER_CONFIG = WORKER_DIR / "wrangler.toml"
BUNDLED_NODE_BIN = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "bin"

ACCOUNT_ID_RE = re.compile(r"^[a-f0-9]{32}$")
UUID_RE = re.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$")
SECRET_LINE_RE = re.compile(r"\b(ADMIN_READ_TOKEN|PRIVACY_HASH_SALT|CLOUDFLARE_API_TOKEN)\s*=\s*[^ \n\r\t]+")
OFFICIAL_CONTACT_EMAIL = "support@gcagochina.com"


class ReadinessError(RuntimeError):
    pass


def check(checks: list[dict[str, Any]], check_id: str, passed: bool, detail: str, **extra: Any) -> None:
    checks.append(
        {
            "id": check_id,
            "status": "passed" if passed else "failed",
            "detail": detail,
            **extra,
        }
    )


def skipped(checks: list[dict[str, Any]], check_id: str, detail: str, **extra: Any) -> None:
    checks.append({"id": check_id, "status": "skipped", "detail": detail, **extra})


def load_wrangler_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise ReadinessError(f"Missing Wrangler config: {config_path}")
    if tomllib is None:
        raise ReadinessError("Python tomllib is unavailable; use Python 3.11+ for TOML parsing.")
    with config_path.open("rb") as handle:
        return tomllib.load(handle)


def sanitized_command_result(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    combined = f"{result.stdout}\n{result.stderr}"
    if "Authentication error [code: 10000]" in combined:
        summary = "Cloudflare authentication or permission error [code: 10000]."
    elif result.returncode == 0:
        summary = "Command completed successfully."
    else:
        lines = [
            SECRET_LINE_RE.sub(r"\1=<redacted>", line.strip())
            for line in combined.splitlines()
            if line.strip() and "Logs were written to" not in line
        ]
        summary = lines[-1][:240] if lines else "Wrangler command failed; see local Wrangler logs."
    return {
        "returnCode": result.returncode,
        "summary": summary,
    }


def has_auth_error(checks: list[dict[str, Any]]) -> bool:
    for item in checks:
        result = item.get("result")
        if isinstance(result, dict) and "code: 10000" in str(result.get("summary", "")):
            return True
    return False


def build_auth_recovery(checks: list[dict[str, Any]], *, run_cloudflare: bool) -> dict[str, Any]:
    cloudflare_failed = [
        item["id"]
        for item in checks
        if item["id"].startswith("cloudflare-") and item["status"] == "failed"
    ]
    code_10000_seen = has_auth_error(checks)
    if not run_cloudflare:
        status = "not-checked"
    elif cloudflare_failed:
        status = "cloudflare-auth-or-permission-blocked"
    else:
        status = "cloudflare-permission-checks-passed"

    safe_next_actions = [
        "Confirm Wrangler is logged into the Cloudflare account that owns the gca-registration-api Worker and gca_registration D1 database.",
        "If needed, run wrangler logout and wrangler login, or set a Cloudflare API token scoped to the target account.",
        "Re-run python3 tools/check_gca_worker_deploy_readiness.py --run-wrangler --run-cloudflare --require-deploy-auth before applying migrations or deploying.",
    ]
    if code_10000_seen:
        safe_next_actions.insert(0, "Resolve Cloudflare authentication or permission error [code: 10000] before any publish attempt.")

    return {
        "status": status,
        "code10000Seen": code_10000_seen,
        "failedCloudflareChecks": cloudflare_failed,
        "requiredCapabilities": [
            "read authenticated Cloudflare account membership for the configured account_id",
            "list the configured gca_registration D1 database",
            "read gca-registration-api Worker deployment history",
            "apply remote D1 migrations only after readiness passes",
            "deploy the gca-registration-api Worker only after readiness passes",
        ],
        "safeNextActions": safe_next_actions,
        "blockedUntilReadinessPasses": [
            "npx wrangler d1 migrations apply gca_registration --remote",
            "npx wrangler deploy",
            "mark new or changed Worker routes as production-live",
            "run token-protected admin smoke checks against changed routes",
        ],
        "boundaries": {
            "writesD1Records": False,
            "deploysWorker": False,
            "printsAdminReadToken": False,
            "readsUserLedgers": False,
        },
    }


def command_env() -> dict[str, str]:
    env = os.environ.copy()
    if BUNDLED_NODE_BIN.exists():
        env["PATH"] = f"{BUNDLED_NODE_BIN}{os.pathsep}{env.get('PATH', '')}"
    return env


def run_command(args: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        env=command_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def wrangler_command(worker_dir: Path) -> list[str]:
    local_wrangler = worker_dir / "node_modules" / ".bin" / "wrangler"
    if local_wrangler.exists():
        return [str(local_wrangler)]
    found = shutil.which("wrangler")
    if found:
        return [found]
    return ["wrangler"]


def build_report(
    root: Path = ROOT,
    *,
    run_wrangler: bool = False,
    run_cloudflare: bool = False,
    timeout: int = 30,
    runner=run_command,
) -> dict[str, Any]:
    worker_dir = root / "cloudflare" / "gca-registration-worker"
    config_path = worker_dir / "wrangler.toml"
    config = load_wrangler_config(config_path)
    checks: list[dict[str, Any]] = []

    account_id = str(config.get("account_id", "")).strip()
    check(
        checks,
        "wrangler-account-id",
        bool(ACCOUNT_ID_RE.fullmatch(account_id)),
        "wrangler.toml includes an explicit Cloudflare account_id for deploy commands.",
        configured=bool(account_id),
    )

    d1_bindings = config.get("d1_databases") or []
    d1 = d1_bindings[0] if d1_bindings else {}
    database_id = str(d1.get("database_id", "")).strip()
    check(
        checks,
        "d1-database-id",
        bool(UUID_RE.fullmatch(database_id)),
        "wrangler.toml includes the GCA D1 database_id.",
        configured=bool(database_id),
    )

    worker_vars = config.get("vars") or {}
    contact_email = str(worker_vars.get("CONTACT_EMAIL", "")).strip().lower()
    check(
        checks,
        "worker-contact-email",
        contact_email == OFFICIAL_CONTACT_EMAIL,
        "Worker contact email matches the official gcagochina.com support mailbox.",
        configured=bool(contact_email),
    )

    check(
        checks,
        "worker-source",
        (worker_dir / "src" / "worker.mjs").exists(),
        "Worker source file exists.",
    )
    check(
        checks,
        "credit-usage-migration",
        (worker_dir / "migrations" / "0004_credit_usage_ledger.sql").exists(),
        "Credit usage D1 migration exists.",
    )
    check(
        checks,
        "service-requests-migration",
        (worker_dir / "migrations" / "0005_service_requests.sql").exists(),
        "Service request queue D1 migration exists.",
    )
    check(
        checks,
        "member-reviews-migration",
        (worker_dir / "migrations" / "0006_member_reviews.sql").exists(),
        "Member review D1 migration exists.",
    )
    check(
        checks,
        "wrangler-package",
        (worker_dir / "package-lock.json").exists() and (worker_dir / "node_modules" / ".bin" / "wrangler").exists(),
        "Worker package dependencies and local Wrangler binary are installed.",
    )

    wrangler = wrangler_command(worker_dir)
    if run_wrangler:
        dry_run = runner([*wrangler, "deploy", "--dry-run"], worker_dir, timeout)
        dry_run_result = sanitized_command_result(dry_run)
        check(
            checks,
            "wrangler-deploy-dry-run",
            dry_run.returncode == 0,
            "Wrangler can bundle the Worker and resolve D1 bindings without publishing.",
            result=dry_run_result,
        )
    else:
        skipped(checks, "wrangler-deploy-dry-run", "Pass --run-wrangler to run Wrangler deploy --dry-run.")

    if run_cloudflare:
        whoami_args = [*wrangler, "whoami", "--json"]
        if ACCOUNT_ID_RE.fullmatch(account_id):
            whoami_args.extend(["--account", account_id])
        whoami = runner(whoami_args, worker_dir, timeout)
        whoami_result = sanitized_command_result(whoami)
        check(
            checks,
            "cloudflare-auth-session",
            whoami.returncode == 0,
            "Wrangler can read the authenticated Cloudflare identity for the configured account without exposing identity details.",
            result=whoami_result,
        )

        d1_list = runner([*wrangler, "d1", "list"], worker_dir, timeout)
        d1_result = sanitized_command_result(d1_list)
        d1_ok = d1_list.returncode == 0 and database_id in f"{d1_list.stdout}\n{d1_list.stderr}"
        check(
            checks,
            "cloudflare-d1-visible",
            d1_ok,
            "Cloudflare account can list the configured GCA D1 database.",
            result=d1_result,
        )

        deployments = runner([*wrangler, "deployments", "list", "--json"], worker_dir, timeout)
        deployment_result = sanitized_command_result(deployments)
        check(
            checks,
            "cloudflare-worker-deploy-permission",
            deployments.returncode == 0,
            "Cloudflare account can read Worker deployments; this is the minimum gate before publishing an updated Worker.",
            result=deployment_result,
        )
    else:
        skipped(checks, "cloudflare-auth-session", "Pass --run-cloudflare to check Wrangler account authentication.")
        skipped(checks, "cloudflare-d1-visible", "Pass --run-cloudflare to check Cloudflare D1 visibility.")
        skipped(checks, "cloudflare-worker-deploy-permission", "Pass --run-cloudflare to check Worker deployment permissions.")

    failed = [item for item in checks if item["status"] == "failed"]
    return {
        "schema": "gca_worker_deploy_readiness_v1",
        "root": str(root),
        "workerDirectory": str(worker_dir.relative_to(root)),
        "wranglerConfig": str(config_path.relative_to(root)),
        "workerName": config.get("name"),
        "accountIdConfigured": bool(account_id),
        "databaseIdConfigured": bool(database_id),
        "runWrangler": run_wrangler,
        "runCloudflare": run_cloudflare,
        "readyToAttemptDeploy": not failed,
        "failedChecks": [item["id"] for item in failed],
        "checks": checks,
        "authRecovery": build_auth_recovery(checks, run_cloudflare=run_cloudflare),
        "boundaries": {
            "writesD1Records": False,
            "deploysWorker": False,
            "printsAdminReadToken": False,
            "readsUserLedgers": False,
        },
        "nextStep": "Run wrangler deploy only after cloudflare-worker-deploy-permission passes.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check GCA Cloudflare Worker deployment readiness without writing production data.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root. Defaults to this script's GCA repo.")
    parser.add_argument("--run-wrangler", action="store_true", help="Run wrangler deploy --dry-run.")
    parser.add_argument("--run-cloudflare", action="store_true", help="Run read-only Cloudflare permission checks.")
    parser.add_argument("--require-deploy-auth", action="store_true", help="Exit non-zero unless Worker deployment permission check passes.")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per Wrangler command in seconds.")
    args = parser.parse_args(argv)

    report = build_report(args.root.resolve(), run_wrangler=args.run_wrangler, run_cloudflare=args.run_cloudflare, timeout=args.timeout)
    print(json.dumps(report, indent=2, sort_keys=True))

    if report["failedChecks"]:
        if args.require_deploy_auth or any(check_id != "cloudflare-worker-deploy-permission" for check_id in report["failedChecks"]):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
