import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_gca_daily_ops as daily_ops_module
from tools.build_gca_daily_status_snapshot import build_snapshot
from tools.run_gca_daily_ops import emit_github_observation_annotations, run_daily_ops


BASESCAN_BLOCKED_OUTPUT = json.dumps({
    "readyForBaseScanResubmission": False,
    "status": "blocked-before-basescan-resubmission",
    "missingOrBlockedRequirements": [
        "official-domain-email",
        "domain-email-public-switch-check",
    ],
    "domainEmailPublicSwitchSummary": {
        "status": "public-email-switch-pending",
        "summary": {
            "filesStillUsingCurrentEmail": 3,
            "filesPublishingForbiddenLegacyEmail": 3,
        },
        "records": [
            {
                "path": "site/support.html",
                "status": "needs-switch",
                "currentEmailOccurrences": 2,
                "forbiddenLegacyEmailOccurrences": 2,
                "targetEmailOccurrences": 0,
            },
            {
                "path": "site/project.json",
                "status": "needs-switch",
                "currentEmailOccurrences": 1,
                "forbiddenLegacyEmailOccurrences": 1,
                "targetEmailOccurrences": 0,
            },
            {
                "path": "site/external-reviews.json",
                "status": "target-email-missing",
                "currentEmailOccurrences": 0,
                "forbiddenLegacyEmailOccurrences": 0,
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
        "summary": {
            "filesStillUsingCurrentEmail": 0,
            "filesPublishingForbiddenLegacyEmail": 0,
        },
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

BASESCAN_PUBLIC_PROFILE_OUTPUT = json.dumps({
    "ok": True,
    "packetVersion": "gca_basescan_public_profile_check_v1",
    "checkedAt": "2026-07-23T12:00:00Z",
    "status": "token-profile-not-published",
    "profilePublished": False,
    "tokenRep": "Unknown",
    "holders": 10,
    "sourceVerificationObserved": True,
    "tokenUrl": "https://basescan.org/token/0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6",
    "addressUrl": "https://basescan.org/address/0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6#code",
    "signals": {
        "officialDomainPresent": False,
        "genericAddressTitle": True,
        "defaultPreviewImage": True,
    },
    "nextAction": "Submit one owner-controlled BaseScan update after final preflight.",
})

MARKET_HEALTH_OUTPUT = json.dumps({
    "ok": True,
    "packetVersion": "gca_market_health_check_v1",
    "checkedAt": "2026-08-11T20:00:00Z",
    "status": "official-pool-observed",
    "identityVerified": True,
    "network": "Base Mainnet",
    "chainId": 8453,
    "contractAddress": "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6",
    "quoteAssetAddress": "0xfde4c96c8593536e31f229ea8f37b2ada2699bb2",
    "poolAddress": "0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0",
    "dexId": "uniswap-v4-base",
    "source": {
        "provider": "GeckoTerminal Public API",
        "apiUrl": "https://api.geckoterminal.com/api/v2/networks/base/pools/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0",
        "publicPoolUrl": "https://www.geckoterminal.com/base/pools/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0",
    },
    "observed": {
        "poolName": "GCA / USDT 0.01%",
        "poolCreatedAt": "2026-05-10T14:54:55Z",
        "baseTokenPriceUsd": "0.00000180452417",
        "reserveInUsd": "41.8349",
        "volumeUsd24h": "2.5",
        "priceChangePercentage24h": "-1.25",
        "transactions24h": {
            "buys": 2,
            "sells": 1,
            "buyers": 2,
            "sellers": 1,
            "total": 3,
        },
    },
    "interpretation": {
        "liquidityDepthStatus": "starter-depth-only",
        "activityStatus": "24h-transactions-observed",
        "doesNotProveOrganicDemand": True,
        "nextAction": "Keep the official route consistent.",
    },
})

MARKET_HEALTH_SUMMARY = {
    "available": True,
    "status": "official-pool-observed",
    "identityVerified": True,
    "checkedAt": "2026-08-11T20:00:00Z",
    "poolAddress": "0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0",
    "contractAddress": "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6",
    "quoteAssetAddress": "0xfde4c96c8593536e31f229ea8f37b2ada2699bb2",
    "dexId": "uniswap-v4-base",
    "poolName": "GCA / USDT 0.01%",
    "poolCreatedAt": "2026-05-10T14:54:55Z",
    "baseTokenPriceUsd": "0.00000180452417",
    "reserveInUsd": "41.8349",
    "volumeUsd24h": "2.5",
    "priceChangePercentage24h": "-1.25",
    "transactions24h": {
        "buys": 2,
        "sells": 1,
        "buyers": 2,
        "sellers": 1,
        "total": 3,
    },
    "liquidityDepthStatus": "starter-depth-only",
    "activityStatus": "24h-transactions-observed",
    "sourceProvider": "GeckoTerminal Public API",
    "sourceApiUrl": "https://api.geckoterminal.com/api/v2/networks/base/pools/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0",
    "publicPoolUrl": "https://www.geckoterminal.com/base/pools/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0",
    "nextAction": "Keep the official route consistent.",
}


class GcaDailyOpsTests(unittest.TestCase):
    def test_github_annotations_include_only_failed_public_observations(self):
        stream = io.StringIO()
        emitted = emit_github_observation_annotations(
            {
                "steps": [
                    {
                        "id": "public-site",
                        "ok": False,
                        "blocksSummaryOk": True,
                        "returnCode": 1,
                        "stderrTail": "HTTP 503\nretry 100%",
                    },
                    {
                        "id": "member-access-ops",
                        "ok": False,
                        "returnCode": 1,
                        "stderrTail": "private-member-detail",
                    },
                    {
                        "id": "basescan-public-profile-status",
                        "ok": False,
                        "blocksSummaryOk": False,
                        "returnCode": 2,
                        "statusSummary": {
                            "status": "check-failed",
                            "error": "BaseScan returned HTTP 403",
                        },
                    },
                ]
            },
            stream=stream,
        )

        output = stream.getvalue()
        self.assertEqual(emitted, 2)
        self.assertIn("::error title=GCA public check failed: public-site::", output)
        self.assertIn("::warning title=GCA public check failed: basescan-public-profile-status::", output)
        self.assertIn("BaseScan returned HTTP 403", output)
        self.assertIn("HTTP 503%0Aretry 100%25", output)
        self.assertNotIn("private-member-detail", output)

    def test_github_annotations_skip_successful_public_observations(self):
        stream = io.StringIO()
        emitted = emit_github_observation_annotations(
            {"steps": [{"id": "public-site", "ok": True, "returnCode": 0}]},
            stream=stream,
        )

        self.assertEqual(emitted, 0)
        self.assertEqual(stream.getvalue(), "")

    def test_daily_ops_public_only_runs_site_and_api_checks(self):
        seen = []

        def runner(command, cwd, timeout):
            seen.append({"command": list(command), "cwd": cwd, "timeout": timeout})
            if any("check_basescan_public_profile.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_PUBLIC_PROFILE_OUTPUT, stderr="")
            if any("check_basescan_resubmission_readiness.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_BLOCKED_OUTPUT, stderr="")
            if any("check_gca_market_health.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=MARKET_HEALTH_OUTPUT, stderr="")
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
            [
                "public-site",
                "registration-api-public",
                "official-pool-market-health",
                "basescan-public-profile-status",
                "basescan-resubmission-preflight-status",
            ],
        )
        self.assertTrue(summary["boundaries"]["publicOnlyByDefault"])
        self.assertFalse(summary["boundaries"]["writesProductionData"])
        self.assertFalse(summary["boundaries"]["automaticTokenTransfer"])
        self.assertTrue(summary["includeBaseScanPublicProfileStatus"])
        self.assertTrue(summary["includeBaseScanPreflightStatus"])
        self.assertTrue(summary["includeMarketHealth"])
        self.assertFalse(summary["requireCompletePublicObservations"])
        self.assertTrue(summary["publicObservationsComplete"])
        self.assertEqual(summary["failedPublicObservations"], [])
        self.assertEqual(summary["missingPublicObservations"], [])
        self.assertEqual(summary["marketHealth"]["status"], "official-pool-observed")
        self.assertTrue(summary["marketHealth"]["identityVerified"])
        self.assertEqual(summary["marketHealth"]["reserveInUsd"], "41.8349")
        self.assertEqual(summary["marketHealth"]["volumeUsd24h"], "2.5")
        self.assertEqual(summary["marketHealth"]["transactions24h"]["total"], 3)
        self.assertTrue(summary["boundaries"]["baseScanPublicProfileReadOnly"])
        self.assertFalse(summary["boundaries"]["baseScanPublicProfileBlocksDailyOps"])
        self.assertTrue(summary["boundaries"]["baseScanPreflightStatusOnly"])
        self.assertFalse(summary["boundaries"]["baseScanPreflightBlocksDailyOps"])
        self.assertTrue(summary["boundaries"]["marketHealthReadOnly"])
        self.assertFalse(summary["boundaries"]["marketHealthBlocksDailyOps"])
        self.assertFalse(summary["boundaries"]["marketHealthBuildsExecutableQuote"])
        self.assertFalse(summary["boundaries"]["marketHealthSubmitsTrade"])
        self.assertFalse(summary["boundaries"]["submitsBaseScanRequest"])
        self.assertFalse(summary["baseScanPreflight"]["readyForBaseScanResubmission"])
        self.assertEqual(summary["baseScanPublicProfile"]["status"], "token-profile-not-published")
        self.assertFalse(summary["baseScanPublicProfile"]["profilePublished"])
        self.assertEqual(summary["baseScanPublicProfile"]["tokenRep"], "Unknown")
        self.assertEqual(summary["baseScanPublicProfile"]["holders"], 10)
        self.assertTrue(summary["baseScanPublicProfile"]["sourceVerificationObserved"])
        self.assertFalse(summary["baseScanPublicProfile"]["officialDomainPresent"])
        self.assertEqual(summary["baseScanPreflight"]["status"], "blocked-before-basescan-resubmission")
        self.assertEqual(summary["baseScanPreflight"]["publicEmailSwitchStatus"], "public-email-switch-pending")
        self.assertEqual(summary["baseScanPreflight"]["filesStillUsingOldEmail"], 3)
        self.assertEqual(summary["baseScanPreflight"]["oldEmailFilePaths"], ["site/support.html", "site/project.json"])
        self.assertEqual(summary["baseScanPreflight"]["filesPublishingForbiddenLegacyEmail"], 3)
        self.assertEqual(
            summary["baseScanPreflight"]["forbiddenLegacyEmailFilePaths"],
            ["site/support.html", "site/project.json"],
        )
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
        self.assertTrue(any("tools/check_gca_market_health.py" in command and "--json" in command for command in commands))
        self.assertTrue(any("tools/check_basescan_public_profile.py" in command and "--json" in command for command in commands))
        self.assertTrue(any("tools/check_basescan_resubmission_readiness.py" in command and "--skip-url-checks" in command for command in commands))

    def test_daily_ops_strict_public_observations_fail_for_retry(self):
        def runner(command, cwd, timeout):
            if any("check_gca_market_health.py" in part for part in command):
                return subprocess.CompletedProcess(
                    command,
                    1,
                    stdout='{"ok": false, "status": "market-api-unavailable"}',
                    stderr="temporary public API failure",
                )
            if any("check_basescan_public_profile.py" in part for part in command):
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=BASESCAN_PUBLIC_PROFILE_OUTPUT,
                    stderr="",
                )
            if any("check_basescan_resubmission_readiness.py" in part for part in command):
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=BASESCAN_BLOCKED_OUTPUT,
                    stderr="",
                )
            return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}', stderr="")

        with tempfile.TemporaryDirectory() as temp:
            summary = run_daily_ops(
                require_complete_public_observations=True,
                summary_output=Path(temp) / "summary.json",
                runner=runner,
            )

        self.assertFalse(summary["ok"])
        self.assertTrue(summary["requireCompletePublicObservations"])
        self.assertFalse(summary["publicObservationsComplete"])
        self.assertEqual(summary["failedPublicObservations"], ["official-pool-market-health"])
        self.assertEqual(summary["missingPublicObservations"], [])
        market_step = next(
            step for step in summary["steps"] if step["id"] == "official-pool-market-health"
        )
        self.assertFalse(market_step["blocksSummaryOk"])

    def test_strict_public_observations_reject_skipped_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "complete public observations require"):
                run_daily_ops(
                    include_market_health=False,
                    require_complete_public_observations=True,
                    summary_output=Path(temp) / "summary.json",
                    runner=lambda command, cwd, timeout: subprocess.CompletedProcess(
                        command, 0, stdout='{"ok": true}', stderr=""
                    ),
                )

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
        self.assertTrue(summary["includeBaseScanPublicProfileStatus"])
        self.assertEqual(
            [step["id"] for step in summary["steps"]],
            [
                "public-site",
                "registration-api-public",
                "official-pool-market-health",
                "basescan-public-profile-status",
            ],
        )
        self.assertFalse(summary["baseScanPreflight"]["available"])
        self.assertEqual(summary["baseScanPreflight"]["status"], "not-run")
        self.assertEqual(summary["baseScanPreflight"]["snapshotAlignmentStatus"], "")
        self.assertEqual(summary["baseScanPreflight"]["snapshotAlignmentStaleMarkers"], 0)
        self.assertEqual(summary["baseScanPreflight"]["oldEmailFilePaths"], [])
        self.assertEqual(summary["baseScanPreflight"]["forbiddenLegacyEmailFilePaths"], [])
        self.assertEqual(summary["baseScanPreflight"]["missingTargetEmailFilePaths"], [])

    def test_daily_ops_can_skip_market_health_explicitly(self):
        def runner(command, cwd, timeout):
            if any("check_basescan_public_profile.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_PUBLIC_PROFILE_OUTPUT, stderr="")
            if any("check_basescan_resubmission_readiness.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_BLOCKED_OUTPUT, stderr="")
            return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}', stderr="")

        with tempfile.TemporaryDirectory() as temp:
            summary = run_daily_ops(
                summary_output=Path(temp) / "summary.json",
                include_market_health=False,
                runner=runner,
            )

        self.assertTrue(summary["ok"])
        self.assertFalse(summary["includeMarketHealth"])
        self.assertNotIn("official-pool-market-health", [step["id"] for step in summary["steps"]])
        self.assertFalse(summary["marketHealth"]["available"])
        self.assertEqual(summary["marketHealth"]["status"], "not-run")

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
        self.assertEqual(summary["baseScanPreflight"]["filesPublishingForbiddenLegacyEmail"], 0)
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
        self.assertFalse(summary["includeServiceRoutes"])
        self.assertEqual(summary["steps"][-1]["id"], "member-access-ops")
        self.assertIn("tools/run_gca_member_access_ops.py", summary["steps"][-1]["command"])
        self.assertIn("--redact public", summary["steps"][-1]["command"])
        self.assertFalse(summary["includeHoldingReport"])
        self.assertFalse(summary["boundaries"]["walletCalls"])

    def test_daily_ops_can_include_service_routes_explicitly(self):
        def runner(command, cwd, timeout):
            if any("check_basescan_resubmission_readiness.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_BLOCKED_OUTPUT, stderr="")
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        with tempfile.TemporaryDirectory() as temp:
            summary = run_daily_ops(
                include_member_ops=True,
                include_service_routes=True,
                member_ops_redact="public",
                summary_output=Path(temp) / "summary.json",
                runner=runner,
            )

        self.assertTrue(summary["ok"])
        self.assertTrue(summary["includeServiceRoutes"])
        self.assertIn("--include-service-routes", summary["steps"][-1]["command"])
        self.assertTrue(summary["boundaries"]["serviceRouteReportsReadOnly"])

    def test_daily_ops_service_routes_require_member_ops(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                run_daily_ops(
                    include_service_routes=True,
                    summary_output=Path(temp) / "summary.json",
                    runner=lambda command, cwd, timeout: subprocess.CompletedProcess(command, 0, stdout="", stderr=""),
                )

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
            if any("check_basescan_public_profile.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_PUBLIC_PROFILE_OUTPUT, stderr="")
            if any("check_basescan_resubmission_readiness.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_BLOCKED_OUTPUT, stderr="")
            if any("check_gca_market_health.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=MARKET_HEALTH_OUTPUT, stderr="")
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
            self.assertFalse(summary["publicStatusSnapshot"]["referenceSync"]["requested"])
            self.assertTrue(summary["publicStatusSnapshot"]["referenceSync"]["ok"])
            self.assertEqual(
                summary["publicStatusSnapshot"]["referenceSync"]["status"],
                "skipped-noncanonical-output",
            )
            self.assertEqual(summary["publicStatusSnapshot"]["baseScanPreflightStatus"], "blocked-before-basescan-resubmission")
            self.assertEqual(summary["publicStatusSnapshot"]["filesStillUsingOldEmail"], 3)
            self.assertEqual(summary["publicStatusSnapshot"]["filesPublishingForbiddenLegacyEmail"], 3)
            payload = json.loads(json_output.read_text(encoding="utf-8"))
            page = html_output.read_text(encoding="utf-8")
            self.assertEqual(payload["snapshotGeneratedAt"], summary["generatedAt"])
            self.assertEqual(payload["dailyOps"]["steps"][0]["command"], "python3 tools/check_public_site.py --base-url https://gcagochina.com/ --timeout 20")
            self.assertEqual(payload["baseScanPublicProfile"]["status"], "token-profile-not-published")
            self.assertFalse(payload["baseScanPublicProfile"]["profilePublished"])
            self.assertTrue(payload["baseScanPublicProfile"]["sourceVerificationObserved"])
            self.assertEqual(payload["baseScanPreflight"]["oldEmailFilePaths"], ["site/support.html", "site/project.json"])
            self.assertEqual(payload["baseScanPreflight"]["forbiddenLegacyEmailFilePaths"], ["site/support.html", "site/project.json"])
            self.assertEqual(payload["baseScanPreflight"]["missingTargetEmailFilePaths"], ["site/external-reviews.json"])
            self.assertEqual(payload["ownerActionQueue"][0]["id"], "activate-domain-mailbox")
            self.assertNotIn("confirm-project-profile-map", {item["id"] for item in payload["ownerActionQueue"]})
            self.assertIn(summary["generatedAt"], page)
            self.assertNotIn("/Users/", json.dumps(payload))
            self.assertFalse(summary["boundaries"]["adminTokenPrinted"])
            self.assertFalse(summary["boundaries"]["writesProductionData"])
            self.assertTrue(
                summary["boundaries"][
                    "synchronizesBaseScanSnapshotReferencesOnlyForCanonicalPublicOutputs"
                ]
            )

    def test_daily_ops_syncs_reviewer_references_for_canonical_outputs(self):
        def runner(command, cwd, timeout):
            if any("check_basescan_public_profile.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_PUBLIC_PROFILE_OUTPUT, stderr="")
            if any("check_basescan_resubmission_readiness.py" in part for part in command):
                return subprocess.CompletedProcess(command, 0, stdout=BASESCAN_BLOCKED_OUTPUT, stderr="")
            return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}', stderr="")

        sync_report = {
            "status": "updated",
            "ok": True,
            "summary": {
                "filesChanged": 4,
                "timestampReplacements": 9,
                "profileDateReplacements": 3,
            },
            "missingFilePaths": [],
            "missingCanonicalReferencePaths": [],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            summary_output = root / "summary.json"
            json_output = root / "daily-status.json"
            html_output = root / "daily-status.html"
            html_output.write_text(
                (Path(__file__).resolve().parents[1] / "site" / "daily-status.html").read_text(),
                encoding="utf-8",
            )

            with (
                patch.object(daily_ops_module, "DEFAULT_DAILY_STATUS_JSON_OUTPUT", json_output),
                patch.object(daily_ops_module, "DEFAULT_DAILY_STATUS_HTML_OUTPUT", html_output),
                patch.object(
                    daily_ops_module,
                    "synchronize_references",
                    return_value=sync_report,
                ) as sync_references,
            ):
                summary = run_daily_ops(
                    summary_output=summary_output,
                    update_public_status=True,
                    daily_status_json_output=json_output,
                    daily_status_html_output=html_output,
                    runner=runner,
                )

        reference_sync = summary["publicStatusSnapshot"]["referenceSync"]
        self.assertTrue(summary["ok"])
        self.assertTrue(reference_sync["requested"])
        self.assertTrue(reference_sync["ok"])
        self.assertEqual(reference_sync["status"], "updated")
        self.assertEqual(reference_sync["filesChanged"], 4)
        self.assertEqual(reference_sync["timestampReplacements"], 9)
        self.assertEqual(reference_sync["profileDateReplacements"], 3)
        sync_references.assert_called_once_with(
            daily_status_path=json_output,
            write=True,
        )

    def test_daily_status_snapshot_builder_publishes_public_safe_artifacts(self):
        summary = {
            "ok": True,
            "packetVersion": "gca_daily_ops_summary_v1",
            "generatedAt": "2026-05-30T10:11:12Z",
            "siteBaseUrl": "https://gcagochina.com/",
            "apiBaseUrl": "https://gca-registration-api.gcagochina.workers.dev",
            "boundaries": {"publicOnlyByDefault": True},
            "baseScanPublicProfile": json.loads(BASESCAN_PUBLIC_PROFILE_OUTPUT),
            "baseScanPreflight": {
                "status": "blocked-before-basescan-resubmission",
                "readyForBaseScanResubmission": False,
                "publicEmailSwitchStatus": "public-email-switch-pending",
                "snapshotAlignmentStatus": "aligned",
                "filesStillUsingOldEmail": 3,
                "filesPublishingForbiddenLegacyEmail": 3,
                "oldEmailFilePaths": [
                    "site/support.html",
                    "site/project.json",
                    "/path/to/gca_token/site/private.html",
                    "../outside.json",
                ],
                "forbiddenLegacyEmailFilePaths": [
                    "site/support.html",
                    "site/project.json",
                    "/path/to/gca_token/site/private.html",
                    "../outside.json",
                ],
                "missingTargetEmailFilePaths": ["site/external-reviews.json"],
                "missingOrBlockedRequirements": [
                    "official-domain-email",
                    "domain-email-public-switch-check",
                ],
                "nextAction": "Do not resubmit BaseScan yet.",
            },
            "marketHealth": MARKET_HEALTH_SUMMARY,
            "steps": [
                {
                    "id": "public-site",
                    "ok": True,
                    "blocksSummaryOk": True,
                    "command": "/path/to/gca_token/.venv/bin/python tools/check_public_site.py --base-url https://gcagochina.com/ --timeout 20",
                },
                {
                    "id": "registration-api-public",
                    "ok": True,
                    "blocksSummaryOk": True,
                    "command": "/path/to/gca_token/.venv/bin/python tools/check_gca_registration_api.py --base-url https://gca-registration-api.gcagochina.workers.dev --public-only --timeout 20",
                },
                {
                    "id": "official-pool-market-health",
                    "ok": True,
                    "blocksSummaryOk": False,
                    "command": "/path/to/gca_token/.venv/bin/python tools/check_gca_market_health.py --json --timeout 20",
                },
                {
                    "id": "basescan-public-profile-status",
                    "ok": True,
                    "blocksSummaryOk": False,
                    "command": "/path/to/gca_token/.venv/bin/python tools/check_basescan_public_profile.py --json --timeout 20",
                },
                {
                    "id": "basescan-resubmission-preflight-status",
                    "ok": True,
                    "blocksSummaryOk": False,
                    "command": "/path/to/gca_token/.venv/bin/python tools/check_basescan_resubmission_readiness.py --skip-url-checks --json",
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
            self.assertEqual(payload["dailyOps"]["steps"][2]["id"], "official-pool-market-health")
            self.assertEqual(payload["dailyOps"]["steps"][2]["blocksSummaryOk"], False)
            self.assertEqual(payload["dailyOps"]["steps"][3]["id"], "basescan-public-profile-status")
            self.assertEqual(payload["dailyOps"]["steps"][3]["blocksSummaryOk"], False)
            self.assertEqual(payload["dailyOps"]["steps"][4]["blocksSummaryOk"], False)
            self.assertTrue(payload["marketHealth"]["identityVerified"])
            self.assertEqual(payload["marketHealth"]["reserveInUsd"], "41.8349")
            self.assertEqual(payload["marketHealth"]["transactions24h"]["total"], 3)
            self.assertEqual(payload["baseScanPublicProfile"]["status"], "token-profile-not-published")
            self.assertFalse(payload["baseScanPublicProfile"]["profilePublished"])
            self.assertEqual(payload["baseScanPreflight"]["filesStillUsingOldEmail"], 3)
            self.assertEqual(payload["baseScanPreflight"]["oldEmailFilePaths"], ["site/support.html", "site/project.json"])
            self.assertEqual(payload["baseScanPreflight"]["filesPublishingForbiddenLegacyEmail"], 3)
            self.assertEqual(payload["baseScanPreflight"]["forbiddenLegacyEmailFilePaths"], ["site/support.html", "site/project.json"])
            self.assertEqual(payload["baseScanPreflight"]["missingTargetEmailFilePaths"], ["site/external-reviews.json"])
            self.assertEqual(payload["ownerActionQueue"][-1]["id"], "final-basescan-preflight")
            self.assertNotIn("confirm-project-profile-map", {item["id"] for item in payload["ownerActionQueue"]})
            self.assertFalse(payload["boundaries"]["adminTokenPrinted"])
            self.assertFalse(payload["boundaries"]["userEmailsPrinted"])
            serialized = json_output.read_text(encoding="utf-8")
            page = html_output.read_text(encoding="utf-8")
            self.assertIn("2026-05-30T10:11:12Z", page)
            self.assertIn("GCA/USDT Market Health", page)
            self.assertIn("$41.8349", page)
            self.assertIn("3 (2 buys / 1 sells)", page)
            self.assertIn("<code>filesStillUsingOldEmail</code> as 3 tracked files", page)
            self.assertIn("<code>filesPublishingForbiddenLegacyEmail</code> as 3 tracked files", page)
            self.assertIn("<code>site/support.html</code>", page)
            self.assertIn("<code>site/external-reviews.json</code>", page)
            self.assertNotIn("/Users/", serialized)
            self.assertNotIn("redacted-personal-contact@example.invalid", serialized + page)
            self.assertNotIn('href="daily-status.json"', page)


if __name__ == "__main__":
    unittest.main()
