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
        lines = [line.strip() for line in combined.splitlines() if line.strip()]
        summary = lines[-1][:240] if lines else "Command failed without output."
    return {
        "returnCode": result.returncode,
        "summary": summary,
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
