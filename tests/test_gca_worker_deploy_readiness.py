import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools import check_gca_worker_deploy_readiness as readiness


ACCOUNT_ID = "5d966731ce064f1f6b252b36d1e16d94"
DATABASE_ID = "b4cb13f7-c52e-4dbc-b8d6-50346a814819"


class GcaWorkerDeployReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        worker_dir = self.tmp / "cloudflare" / "gca-registration-worker"
        (worker_dir / "src").mkdir(parents=True)
        (worker_dir / "migrations").mkdir()
        (worker_dir / "node_modules" / ".bin").mkdir(parents=True)
        (worker_dir / "src" / "worker.mjs").write_text("export default {};\n", encoding="utf-8")
        (worker_dir / "migrations" / "0004_credit_usage_ledger.sql").write_text("CREATE TABLE gca_credit_usage(id TEXT);\n", encoding="utf-8")
        (worker_dir / "package-lock.json").write_text("{}\n", encoding="utf-8")
        (worker_dir / "node_modules" / ".bin" / "wrangler").write_text("#!/bin/sh\n", encoding="utf-8")
        self.worker_dir = worker_dir

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write_config(self, *, account_id=ACCOUNT_ID, database_id=DATABASE_ID):
        account_line = f'account_id = "{account_id}"\n' if account_id else ""
        (self.worker_dir / "wrangler.toml").write_text(
            f"""name = "gca-registration-api"
main = "src/worker.mjs"
compatibility_date = "2026-05-19"
{account_line}workers_dev = true

[[d1_databases]]
binding = "REGISTRATION_DB"
database_name = "gca_registration"
database_id = "{database_id}"
migrations_dir = "migrations"
""",
            encoding="utf-8",
        )

    def test_static_report_passes_without_calling_cloudflare(self):
        self.write_config()
        report = readiness.build_report(self.tmp)
        self.assertTrue(report["readyToAttemptDeploy"])
        self.assertEqual(report["failedChecks"], [])
        self.assertFalse(report["boundaries"]["writesD1Records"])
        self.assertFalse(report["boundaries"]["deploysWorker"])
        self.assertFalse(report["boundaries"]["printsAdminReadToken"])
        self.assertIn("wrangler-deploy-dry-run", {item["id"] for item in report["checks"] if item["status"] == "skipped"})

    def test_missing_account_id_blocks_static_readiness(self):
        self.write_config(account_id="")
        report = readiness.build_report(self.tmp)
        self.assertFalse(report["readyToAttemptDeploy"])
        self.assertIn("wrangler-account-id", report["failedChecks"])

    def test_live_checks_identify_worker_permission_failure_without_printing_secrets(self):
        self.write_config()
        calls = []

        def fake_runner(args, cwd, timeout):
            calls.append(args)
            command = " ".join(args)
            if "deploy --dry-run" in command:
                return subprocess.CompletedProcess(args, 0, stdout="env.REGISTRATION_DB D1 Database\n", stderr="")
            if "d1 list" in command:
                return subprocess.CompletedProcess(args, 0, stdout=f"{DATABASE_ID} gca_registration\n", stderr="")
            if "deployments list" in command:
                return subprocess.CompletedProcess(
                    args,
                    1,
                    stdout="",
                    stderr="Authentication error [code: 10000]\nADMIN_READ_TOKEN=do-not-print\n",
                )
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="unexpected")

        report = readiness.build_report(self.tmp, run_wrangler=True, run_cloudflare=True, runner=fake_runner)
        self.assertIn("cloudflare-worker-deploy-permission", report["failedChecks"])
        deployment_check = next(item for item in report["checks"] if item["id"] == "cloudflare-worker-deploy-permission")
        self.assertEqual(deployment_check["result"]["summary"], "Cloudflare authentication or permission error [code: 10000].")
        self.assertNotIn("do-not-print", str(report))
        self.assertTrue(any("deploy" in call and "--dry-run" in call for call in calls))
        self.assertTrue(any("d1" in call and "list" in call for call in calls))


if __name__ == "__main__":
    unittest.main()
