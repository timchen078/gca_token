import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.build_gca_daily_status_snapshot import build_snapshot
from tools.run_gca_daily_ops import run_daily_ops


BASESCAN_BLOCKED_OUTPUT = json.dumps({
    "readyForBaseScanResubmission": False,
    "status": "blocked-before-basescan-resubmission",
    "missingOrBlockedRequirements": [
        "official-domain-email",
        "domain-email-public-switch-check",
    ],
    "domainEmailPublicSwitchSummary": {
        "status": "public-email-switch-pending",
        "summary": {"filesStillUsingCurrentEmail": 3},
        "records": [
            {
                "path": "site/support.html",
                "status": "needs-switch",
                "currentEmailOccurrences": 2,
                "targetEmailOccurrences": 0,
            },
            {
                "path": "site/project.json",
                "status": "needs-switch",
                "currentEmailOccurrences": 1,
                "targetEmailOccurrences": 0,
            },
            {
                "path": "site/external-reviews.json",
                "status": "target-email-missing",
                "currentEmailOccurrences": 0,
                "targetEmailOccurrences": 0,
            },
        ],
    },
    "domainEmailSnapshotAlignmentSummary": {
        "status": "aligned",
        "summary": {
            "filesWithStaleSnapshotMarkers": 0,
            "filesMissingCurrentSnapshotDate": 0,
        },
    },
    "nextAction": "Do not resubmit BaseScan yet. Complete the blocked requirements first.",
})

BASESCAN_STALE_SNAPSHOT_OUTPUT = json.dumps({
    "readyForBaseScanResubmission": False,
    "status": "blocked-before-basescan-resubmission",
    "missingOrBlockedRequirements": [
        "domain-email-snapshot-alignment",
        "stale-dns-snapshot-markers",
    ],
    "domainEmailPublicSwitchSummary": {
        "status": "public-email-switched",
        "summary": {"filesStillUsingCurrentEmail": 0},
    },
    "domainEmailSnapshotAlignmentSummary": {
        "status": "stale-dns-snapshot-markers",
        "summary": {
            "filesWithStaleSnapshotMarkers": 2,
            "filesMissingCurrentSnapshotDate": 1,
        },
    },
    "nextAction": "Do not reuse platform packets yet. Fix stale or missing domain-email DNS snapshot references first.",
})


class GcaDailyOpsTests(unittest.TestCase):
    def test_daily_ops_public_only_runs_site_and_api_checks(self):
        seen = []

        def runner(command, cwd, timeout):
            seen.append({"command": list(command), "cwd": cwd, "timeout": timeout})
            if any("check_basescan_resubmission_readiness.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_BLOCKED_OUTPUT, stderr="")
            return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}', stderr="")

        with tempfile.TemporaryDirectory() as temp:
            summary = run_daily_ops(
                site_base_url="https://example.com/",
                api_base_url="https://api.example.com",
                timeout=5,
                summary_output=Path(temp) / "summary.json",
                runner=runner,
            )

        self.assertTrue(summary["ok"])
        self.assertFalse(summary["includeMemberOps"])
        self.assertEqual(
            [step["id"] for step in summary["steps"]],
            ["public-site", "registration-api-public", "basescan-resubmission-preflight-status"],
        )
        self.assertTrue(summary["boundaries"]["publicOnlyByDefault"])
        self.assertFalse(summary["boundaries"]["writesProductionData"])
        self.assertFalse(summary["boundaries"]["automaticTokenTransfer"])
        self.assertTrue(summary["includeBaseScanPreflightStatus"])
        self.assertTrue(summary["boundaries"]["baseScanPreflightStatusOnly"])
        self.assertFalse(summary["boundaries"]["baseScanPreflightBlocksDailyOps"])
        self.assertFalse(summary["boundaries"]["submitsBaseScanRequest"])
        self.assertFalse(summary["baseScanPreflight"]["readyForBaseScanResubmission"])
        self.assertEqual(summary["baseScanPreflight"]["status"], "blocked-before-basescan-resubmission")
        self.assertEqual(summary["baseScanPreflight"]["publicEmailSwitchStatus"], "public-email-switch-pending")
        self.assertEqual(summary["baseScanPreflight"]["filesStillUsingOldEmail"], 3)
        self.assertEqual(summary["baseScanPreflight"]["oldEmailFilePaths"], ["site/support.html", "site/project.json"])
        self.assertEqual(summary["baseScanPreflight"]["missingTargetEmailFilePaths"], ["site/external-reviews.json"])
        self.assertEqual(summary["baseScanPreflight"]["snapshotAlignmentStatus"], "aligned")
        self.assertEqual(summary["baseScanPreflight"]["snapshotAlignmentStaleMarkers"], 0)
        self.assertEqual(summary["baseScanPreflight"]["snapshotAlignmentMissingCurrentDate"], 0)
        self.assertIn("official-domain-email", summary["baseScanPreflight"]["missingOrBlockedRequirements"])
        self.assertFalse(summary["steps"][-1]["blocksSummaryOk"])
        self.assertFalse(summary["includeHoldingReport"])
        self.assertFalse(summary["buildDigest"])
        self.assertFalse(summary["operatorDigest"]["requested"])
        self.assertFalse(summary["operatorDigest"]["built"])
        self.assertFalse(summary["boundaries"]["walletCalls"])
        commands = [" ".join(item["command"]) for item in seen]
        self.assertTrue(any("tools/check_public_site.py" in command for command in commands))
        self.assertTrue(any("tools/check_gca_registration_api.py" in command and "--public-only" in command for command in commands))
        self.assertTrue(any("tools/check_basescan_resubmission_readiness.py" in command and "--skip-url-checks" in command for command in commands))

    def test_daily_ops_can_skip_basescan_status_explicitly(self):
        def runner(command, cwd, timeout):
            return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}', stderr="")

        with tempfile.TemporaryDirectory() as temp:
            summary = run_daily_ops(
                summary_output=Path(temp) / "summary.json",
                include_basescan_preflight_status=False,
                runner=runner,
            )

        self.assertTrue(summary["ok"])
        self.assertFalse(summary["includeBaseScanPreflightStatus"])
        self.assertEqual([step["id"] for step in summary["steps"]], ["public-site", "registration-api-public"])
        self.assertFalse(summary["baseScanPreflight"]["available"])
        self.assertEqual(summary["baseScanPreflight"]["status"], "not-run")
        self.assertEqual(summary["baseScanPreflight"]["snapshotAlignmentStatus"], "")
        self.assertEqual(summary["baseScanPreflight"]["snapshotAlignmentStaleMarkers"], 0)
        self.assertEqual(summary["baseScanPreflight"]["oldEmailFilePaths"], [])
        self.assertEqual(summary["baseScanPreflight"]["missingTargetEmailFilePaths"], [])

    def test_daily_ops_summarizes_basescan_snapshot_alignment_status(self):
        def runner(command, cwd, timeout):
            if any("check_basescan_resubmission_readiness.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_STALE_SNAPSHOT_OUTPUT, stderr="")
            return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}', stderr="")

        with tempfile.TemporaryDirectory() as temp:
            summary = run_daily_ops(
                summary_output=Path(temp) / "summary.json",
                runner=runner,
            )

        self.assertTrue(summary["ok"])
        self.assertEqual(summary["baseScanPreflight"]["publicEmailSwitchStatus"], "public-email-switched")
        self.assertEqual(summary["baseScanPreflight"]["filesStillUsingOldEmail"], 0)
        self.assertEqual(summary["baseScanPreflight"]["snapshotAlignmentStatus"], "stale-dns-snapshot-markers")
        self.assertEqual(summary["baseScanPreflight"]["snapshotAlignmentStaleMarkers"], 2)
        self.assertEqual(summary["baseScanPreflight"]["snapshotAlignmentMissingCurrentDate"], 1)
        self.assertIn("domain-email-snapshot-alignment", summary["baseScanPreflight"]["missingOrBlockedRequirements"])

    def test_daily_ops_can_include_member_ops_explicitly(self):
        def runner(command, cwd, timeout):
            if any("check_basescan_resubmission_readiness.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_BLOCKED_OUTPUT, stderr="")
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        with tempfile.TemporaryDirectory() as temp:
            summary = run_daily_ops(
                include_member_ops=True,
                member_ops_redact="public",
                summary_output=Path(temp) / "summary.json",
                runner=runner,
            )

        self.assertTrue(summary["ok"])
        self.assertTrue(summary["includeMemberOps"])
        self.assertEqual(summary["steps"][-1]["id"], "member-access-ops")
        self.assertIn("tools/run_gca_member_access_ops.py", summary["steps"][-1]["command"])
        self.assertIn("--redact public", summary["steps"][-1]["command"])
        self.assertFalse(summary["includeHoldingReport"])
        self.assertFalse(summary["boundaries"]["walletCalls"])

    def test_daily_ops_can_include_holding_report_explicitly(self):
        def runner(command, cwd, timeout):
            if any("check_basescan_resubmission_readiness.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_BLOCKED_OUTPUT, stderr="")
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        with tempfile.TemporaryDirectory() as temp:
            summary = run_daily_ops(
                include_member_ops=True,
                include_holding_report=True,
                holding_force_same_day=True,
                summary_output=Path(temp) / "summary.json",
                runner=runner,
            )

        self.assertTrue(summary["ok"])
        self.assertTrue(summary["includeMemberOps"])
        self.assertTrue(summary["includeHoldingReport"])
        self.assertTrue(summary["holdingForceSameDay"])
        self.assertTrue(summary["boundaries"]["walletCalls"])
        self.assertIn("--include-holding-report", summary["steps"][-1]["command"])
        self.assertIn("--holding-force-same-day", summary["steps"][-1]["command"])

    def test_daily_ops_holding_report_requires_member_ops(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                run_daily_ops(
                    include_holding_report=True,
                    summary_output=Path(temp) / "summary.json",
                    runner=lambda command, cwd, timeout: subprocess.CompletedProcess(command, 0, stdout="", stderr=""),
                )

    def test_daily_ops_holding_report_can_rebuild_without_live_wallet_reads(self):
        def runner(command, cwd, timeout):
            if any("check_basescan_resubmission_readiness.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_BLOCKED_OUTPUT, stderr="")
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        with tempfile.TemporaryDirectory() as temp:
            summary = run_daily_ops(
                include_member_ops=True,
                include_holding_report=True,
                holding_no_live_read=True,
                summary_output=Path(temp) / "summary.json",
                runner=runner,
            )

        self.assertTrue(summary["ok"])
        self.assertTrue(summary["includeHoldingReport"])
        self.assertTrue(summary["holdingNoLiveRead"])
        self.assertFalse(summary["boundaries"]["walletCalls"])
        self.assertIn("--include-holding-report", summary["steps"][-1]["command"])
        self.assertIn("--holding-no-live-read", summary["steps"][-1]["command"])

    def test_daily_ops_marks_failure_without_printing_tokens(self):
        def runner(command, cwd, timeout):
            if any("check_public_site.py" in part for part in command):
                return subprocess.CompletedProcess(command, 1, stdout="", stderr="site failed")
            if any("check_basescan_resubmission_readiness.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_BLOCKED_OUTPUT, stderr="")
            return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}', stderr="")

        with tempfile.TemporaryDirectory() as temp:
            summary_output = Path(temp) / "summary.json"
            summary = run_daily_ops(summary_output=summary_output, runner=runner)

            self.assertFalse(summary["ok"])
            self.assertFalse(summary["steps"][0]["ok"])
            self.assertEqual(summary["steps"][0]["stderrTail"], "site failed")
            self.assertFalse(summary["steps"][2]["blocksSummaryOk"])
            self.assertTrue(summary_output.exists())
            serialized = json.dumps(summary)
            self.assertNotIn("ADMIN_READ_TOKEN", serialized)
            self.assertNotIn("secret-token", serialized)

    def test_daily_ops_can_build_redacted_operator_digest(self):
        def runner(command, cwd, timeout):
            if any("check_basescan_resubmission_readiness.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_BLOCKED_OUTPUT, stderr="")
            return subprocess.CompletedProcess(command, 0, stdout='{"ok": true, "email": "private-user@example.com"}', stderr="")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            summary_output = root / "summary.json"
            digest_output = root / "digest.md"
            digest_json_output = root / "digest.json"
            summary = run_daily_ops(
                summary_output=summary_output,
                build_digest=True,
                digest_output=digest_output,
                digest_json_output=digest_json_output,
                runner=runner,
            )

            self.assertTrue(summary["ok"])
            self.assertTrue(summary["buildDigest"])
            self.assertTrue(summary["operatorDigest"]["requested"])
            self.assertTrue(summary["operatorDigest"]["built"])
            self.assertTrue(summary["operatorDigest"]["ok"])
            self.assertEqual(summary["operatorDigest"]["packetVersion"], "gca_operator_digest_v1")
            self.assertTrue(summary_output.exists())
            self.assertTrue(digest_output.exists())
            self.assertTrue(digest_json_output.exists())

            digest_payload = json.loads(digest_json_output.read_text(encoding="utf-8"))
            self.assertEqual(digest_payload["packetVersion"], "gca_operator_digest_v1")
            self.assertTrue(digest_payload["dailyOps"]["available"])
            self.assertFalse(digest_payload["boundaries"]["writesProductionData"])
            self.assertFalse(digest_payload["boundaries"]["walletCalls"])
            self.assertFalse(digest_payload["boundaries"]["requiresSignature"])
            self.assertFalse(digest_payload["boundaries"]["automaticTokenTransfer"])
            serialized = digest_output.read_text(encoding="utf-8") + digest_json_output.read_text(encoding="utf-8")
            self.assertNotIn("private-user@example.com", serialized)
            self.assertNotIn("stdoutTail", serialized)
            self.assertNotIn("secret-token", serialized)

    def test_daily_ops_can_refresh_public_status_snapshot(self):
        def runner(command, cwd, timeout):
            if any("check_basescan_resubmission_readiness.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_BLOCKED_OUTPUT, stderr="")
            return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}', stderr="")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            summary_output = root / "summary.json"
            json_output = root / "daily-status.json"
            html_output = root / "daily-status.html"
            html_output.write_text((Path(__file__).resolve().parents[1] / "site" / "daily-status.html").read_text(), encoding="utf-8")

            summary = run_daily_ops(
                summary_output=summary_output,
                update_public_status=True,
                daily_status_json_output=json_output,
                daily_status_html_output=html_output,
                runner=runner,
            )

            self.assertTrue(summary["ok"])
            self.assertTrue(summary["publicStatusSnapshot"]["requested"])
            self.assertTrue(summary["publicStatusSnapshot"]["built"])
            self.assertTrue(summary["publicStatusSnapshot"]["ok"])
            self.assertEqual(summary["publicStatusSnapshot"]["baseScanPreflightStatus"], "blocked-before-basescan-resubmission")
            self.assertEqual(summary["publicStatusSnapshot"]["filesStillUsingOldEmail"], 3)
            payload = json.loads(json_output.read_text(encoding="utf-8"))
            page = html_output.read_text(encoding="utf-8")
            self.assertEqual(payload["snapshotGeneratedAt"], summary["generatedAt"])
            self.assertEqual(payload["dailyOps"]["steps"][0]["command"], "python3 tools/check_public_site.py --base-url https://gcagochina.com/ --timeout 20")
            self.assertIn(summary["generatedAt"], page)
            self.assertNotIn("/Users/", json.dumps(payload))
            self.assertFalse(summary["boundaries"]["adminTokenPrinted"])
            self.assertFalse(summary["boundaries"]["writesProductionData"])

    def test_daily_status_snapshot_builder_publishes_public_safe_artifacts(self):
        summary = {
            "ok": True,
            "packetVersion": "gca_daily_ops_summary_v1",
            "generatedAt": "2026-05-30T10:11:12Z",
            "siteBaseUrl": "https://gcagochina.com/",
            "apiBaseUrl": "https://gca-registration-api.gcagochina.workers.dev",
            "boundaries": {"publicOnlyByDefault": True},
            "baseScanPreflight": {
                "status": "blocked-before-basescan-resubmission",
                "readyForBaseScanResubmission": False,
                "publicEmailSwitchStatus": "public-email-switch-pending",
                "snapshotAlignmentStatus": "aligned",
                "filesStillUsingOldEmail": 3,
                "missingOrBlockedRequirements": [
                    "official-domain-email",
                    "domain-email-public-switch-check",
                ],
                "nextAction": "Do not resubmit BaseScan yet.",
            },
            "steps": [
                {
                    "id": "public-site",
                    "ok": True,
                    "blocksSummaryOk": True,
                    "command": "/Users/abc/Desktop/gca_token/.venv/bin/python tools/check_public_site.py --base-url https://gcagochina.com/ --timeout 20",
                },
                {
                    "id": "registration-api-public",
                    "ok": True,
                    "blocksSummaryOk": True,
                    "command": "/Users/abc/Desktop/gca_token/.venv/bin/python tools/check_gca_registration_api.py --base-url https://gca-registration-api.gcagochina.workers.dev --public-only --timeout 20",
                },
                {
                    "id": "basescan-resubmission-preflight-status",
                    "ok": True,
                    "blocksSummaryOk": False,
                    "command": "/Users/abc/Desktop/gca_token/.venv/bin/python tools/check_basescan_resubmission_readiness.py --skip-url-checks --json",
                },
            ],
        }

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            summary_input = root / "summary.json"
            json_output = root / "daily-status.json"
            html_output = root / "daily-status.html"
            summary_input.write_text(json.dumps(summary), encoding="utf-8")
            html_output.write_text((Path(__file__).resolve().parents[1] / "site" / "daily-status.html").read_text(), encoding="utf-8")

            payload = build_snapshot(summary_input, json_output, html_output)

            self.assertEqual(payload["snapshotGeneratedAt"], "2026-05-30T10:11:12Z")
            self.assertEqual(payload["dailyOps"]["steps"][0]["id"], "public-site")
            self.assertEqual(payload["dailyOps"]["steps"][0]["command"], "python3 tools/check_public_site.py --base-url https://gcagochina.com/ --timeout 20")
            self.assertEqual(payload["dailyOps"]["steps"][2]["blocksSummaryOk"], False)
            self.assertEqual(payload["baseScanPreflight"]["filesStillUsingOldEmail"], 3)
            self.assertFalse(payload["boundaries"]["adminTokenPrinted"])
            self.assertFalse(payload["boundaries"]["userEmailsPrinted"])
            serialized = json_output.read_text(encoding="utf-8")
            page = html_output.read_text(encoding="utf-8")
            self.assertIn("2026-05-30T10:11:12Z", page)
            self.assertIn("<code>filesStillUsingOldEmail</code> as 3 tracked files", page)
            self.assertNotIn("/Users/abc", serialized)
            self.assertNotIn('href="daily-status.json"', page)


if __name__ == "__main__":
    unittest.main()
