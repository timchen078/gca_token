import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tools.check_basescan_resubmission_readiness import (
    REQUIRED_URL_FIELDS,
    TARGET_DOMAIN_EMAIL,
    build_readiness_report,
    check_public_urls,
    main,
)


class FakeResponse:
    def __init__(self, status=200, body=b"ok"):
        self.status = status
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size=-1):
        return self.body[:size] if size != -1 else self.body


def ready_values():
    values = {
        "packageStatus": "ready-for-resubmission",
        "nextSubmissionReady": True,
        "chainId": 8453,
        "contractAddress": "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6",
        "officialEmail": TARGET_DOMAIN_EMAIL,
        "timChenProfessionalProfileUrl": "https://gcagochina.com/tim-chen.html",
        "domainEmailSetupPlanUrl": "https://gcagochina.com/domain-email.html",
    }
    for field in REQUIRED_URL_FIELDS:
        values.setdefault(field, f"https://gcagochina.com/{field}.html")
    return values


def ready_evidence_packet():
    return {
        "status": "ready-for-owner-resubmission",
        "readyForBaseScanResubmission": True,
        "targetDomainEmail": TARGET_DOMAIN_EMAIL,
        "dnsReadiness": {"readyForBaseScanEmailEvidence": True, "missingOrBlockedChecks": []},
        "websiteEmailUpdatedToTarget": True,
    }


def ready_public_switch_report():
    return {
        "status": "public-email-switch-complete",
        "readyForBaseScanPublicEmailAlignment": True,
        "targetDomainEmail": TARGET_DOMAIN_EMAIL,
        "summary": {"filesStillUsingCurrentEmail": 0, "filesPublishingForbiddenLegacyEmail": 0},
    }


def ready_snapshot_alignment_report():
    return {
        "status": "aligned",
        "alignedForPublicPlatformPackets": True,
        "canonicalSnapshot": {
            "date": "2026-05-30",
            "checkedAt": "2026-05-30T08:13:47Z",
            "readyForBaseScanEmailEvidence": False,
        },
        "summary": {
            "filesWithStaleSnapshotMarkers": 0,
            "filesMissingCurrentSnapshotDate": 0,
            "missingMonitoredFiles": 0,
        },
    }


class BaseScanResubmissionReadinessTests(unittest.TestCase):
    def test_report_blocks_when_values_and_evidence_are_not_ready(self):
        values = ready_values()
        values["nextSubmissionReady"] = False
        values["officialEmail"] = "GCAgochina@outlook.com"

        report = build_readiness_report(
            values=values,
            evidence_packet=None,
            public_switch_report=None,
            snapshot_alignment_report=None,
            public_url_checks=check_public_urls(values, skip=True),
            generated_at="2026-05-24T00:00:00Z",
        )

        self.assertFalse(report["readyForBaseScanResubmission"])
        self.assertEqual(report["status"], "blocked-before-basescan-resubmission")
        self.assertIn("next-submission-ready-flag", report["missingOrBlockedRequirements"])
        self.assertIn("official-domain-email", report["missingOrBlockedRequirements"])
        self.assertIn("domain-email-evidence-packet", report["missingOrBlockedRequirements"])
        self.assertIn("domain-email-public-switch-check", report["missingOrBlockedRequirements"])
        self.assertIn("domain-email-snapshot-alignment", report["missingOrBlockedRequirements"])
        self.assertFalse(report["boundaries"]["submitsBaseScanRequest"])
        self.assertFalse(report["boundaries"]["touchesWalletOrContract"])

    def test_report_is_ready_when_values_evidence_and_public_urls_pass(self):
        values = ready_values()
        report = build_readiness_report(
            values=values,
            evidence_packet=ready_evidence_packet(),
            public_switch_report=ready_public_switch_report(),
            snapshot_alignment_report=ready_snapshot_alignment_report(),
            public_url_checks=check_public_urls(values, skip=True),
            generated_at="2026-05-24T00:00:00Z",
        )

        self.assertTrue(report["readyForBaseScanResubmission"])
        self.assertEqual(report["status"], "ready-for-owner-resubmission")
        self.assertEqual(report["missingOrBlockedRequirements"], [])
        self.assertIn("one clean BaseScan resubmission", report["nextAction"])

    def test_public_url_failure_blocks_readiness(self):
        values = ready_values()
        url_checks = check_public_urls(values, timeout=1, opener=lambda request, timeout: FakeResponse(status=500))

        report = build_readiness_report(
            values=values,
            evidence_packet=ready_evidence_packet(),
            public_switch_report=ready_public_switch_report(),
            snapshot_alignment_report=ready_snapshot_alignment_report(),
            public_url_checks=url_checks,
            generated_at="2026-05-24T00:00:00Z",
        )

        self.assertFalse(report["readyForBaseScanResubmission"])
        self.assertTrue(any(item.startswith("public-url:") for item in report["missingOrBlockedRequirements"]))

    def test_public_email_switch_failure_blocks_readiness(self):
        values = ready_values()
        public_switch = {
            "status": "public-email-switch-pending",
            "readyForBaseScanPublicEmailAlignment": False,
            "targetDomainEmail": TARGET_DOMAIN_EMAIL,
            "summary": {"filesStillUsingCurrentEmail": 3},
        }

        report = build_readiness_report(
            values=values,
            evidence_packet=ready_evidence_packet(),
            public_switch_report=public_switch,
            snapshot_alignment_report=ready_snapshot_alignment_report(),
            public_url_checks=check_public_urls(values, skip=True),
            generated_at="2026-05-24T00:00:00Z",
        )

        self.assertFalse(report["readyForBaseScanResubmission"])
        self.assertIn("domain-email-public-switch-check", report["missingOrBlockedRequirements"])
        self.assertIn("domain-email-public-switch-old-email", report["missingOrBlockedRequirements"])
        self.assertEqual(report["domainEmailPublicSwitchSummary"]["status"], "public-email-switch-pending")

    def test_forbidden_legacy_email_blocks_readiness_even_without_old_outlook(self):
        values = ready_values()
        public_switch = {
            "status": "public-email-switch-pending",
            "readyForBaseScanPublicEmailAlignment": False,
            "targetDomainEmail": TARGET_DOMAIN_EMAIL,
            "summary": {
                "filesStillUsingCurrentEmail": 0,
                "filesPublishingForbiddenLegacyEmail": 1,
            },
        }

        report = build_readiness_report(
            values=values,
            evidence_packet=ready_evidence_packet(),
            public_switch_report=public_switch,
            snapshot_alignment_report=ready_snapshot_alignment_report(),
            public_url_checks=check_public_urls(values, skip=True),
            generated_at="2026-05-24T00:00:00Z",
        )

        self.assertFalse(report["readyForBaseScanResubmission"])
        self.assertIn("domain-email-public-switch-check", report["missingOrBlockedRequirements"])
        self.assertIn("domain-email-public-switch-forbidden-legacy-email", report["missingOrBlockedRequirements"])
        self.assertNotIn("domain-email-public-switch-old-email", report["missingOrBlockedRequirements"])

    def test_snapshot_alignment_failure_blocks_readiness(self):
        values = ready_values()
        snapshot_alignment = ready_snapshot_alignment_report()
        snapshot_alignment["status"] = "stale-dns-snapshot-markers"
        snapshot_alignment["alignedForPublicPlatformPackets"] = False
        snapshot_alignment["summary"]["filesWithStaleSnapshotMarkers"] = 2

        report = build_readiness_report(
            values=values,
            evidence_packet=ready_evidence_packet(),
            public_switch_report=ready_public_switch_report(),
            snapshot_alignment_report=snapshot_alignment,
            public_url_checks=check_public_urls(values, skip=True),
            generated_at="2026-05-24T00:00:00Z",
        )

        self.assertFalse(report["readyForBaseScanResubmission"])
        self.assertIn("domain-email-snapshot-alignment", report["missingOrBlockedRequirements"])
        self.assertIn("domain-email-snapshot-stale-markers", report["missingOrBlockedRequirements"])
        self.assertEqual(report["domainEmailSnapshotAlignmentSummary"]["status"], "stale-dns-snapshot-markers")

    def test_cli_blocks_current_unready_package_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            values_path = temp_path / "values.json"
            evidence_path = temp_path / "packet.json"
            switch_path = temp_path / "switch.json"
            snapshot_path = temp_path / "snapshot.json"
            values = ready_values()
            values["nextSubmissionReady"] = False
            values["officialEmail"] = "GCAgochina@outlook.com"
            values_path.write_text(json.dumps(values), encoding="utf-8")
            evidence_path.write_text(json.dumps({"readyForBaseScanResubmission": False}), encoding="utf-8")
            switch_path.write_text(json.dumps({"readyForBaseScanPublicEmailAlignment": False}), encoding="utf-8")
            snapshot_path.write_text(json.dumps(ready_snapshot_alignment_report()), encoding="utf-8")

            output = StringIO()
            with redirect_stdout(output):
                exit_code = main([
                    "--values",
                    str(values_path),
                    "--evidence-packet",
                    str(evidence_path),
                    "--public-switch-report",
                    str(switch_path),
                    "--snapshot-alignment-report",
                    str(snapshot_path),
                    "--skip-url-checks",
                    "--json",
                    "--require-ready",
                ])

            self.assertEqual(exit_code, 1)
            payload = json.loads(output.getvalue())
            self.assertFalse(payload["readyForBaseScanResubmission"])
            self.assertIn("Do not resubmit BaseScan yet", payload["nextAction"])


if __name__ == "__main__":
    unittest.main()
