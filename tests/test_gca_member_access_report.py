import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.build_gca_member_access_report import build_report, load_export


ROOT = Path(__file__).resolve().parents[1]


def member_access_export_payload():
    return {
        "ok": True,
        "packetVersion": "gca_cloudflare_member_access_export_v1",
        "exportedAt": "2026-05-20T15:00:00Z",
        "redactedForExternalSharing": False,
        "datasets": {
            "member-access": {
                "records": [{
                    "accountId": "gca_account_1",
                    "status": "active",
                    "createdAt": "2026-05-20T15:00:00Z",
                    "updatedAt": "2026-05-20T15:00:00Z",
                    "email": "user@example.com",
                    "emailSha256": "0" * 64,
                    "displayName": "User",
                    "walletAddress": "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
                    "programIntent": "holder_bonus_and_member",
                    "holdingStartDate": "2026-04-19",
                    "evidenceTxHash": "0x" + "1" * 64,
                    "source": "gca/member-access",
                    "language": "zh-CN",
                }],
            },
            "wallet-verifications": {
                "records": [{
                    "walletVerificationId": "gca_wallet_1",
                    "accountId": "gca_account_1",
                    "walletAddress": "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
                    "chainId": 8453,
                    "contractAddress": "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6",
                    "checkedAt": "2026-05-20T15:00:00Z",
                    "gcaBalance": "1000000",
                    "holderBonusEligible": True,
                    "gcaMemberEligible": True,
                    "gcaMemberHoldingPeriodEligible": True,
                    "holdingPeriodDaysVerified": 31,
                    "evidenceTxHash": "0x" + "1" * 64,
                    "evidenceTxHashFormatOk": True,
                    "status": "verified",
                }],
            },
            "credit-ledger": {
                "records": [{
                    "creditLedgerId": "gca_credit_1",
                    "accountId": "gca_account_1",
                    "walletAddress": "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
                    "creditAmount": 100,
                    "creditType": "GCA AI Quant Access credits",
                    "activatedAt": "2026-05-20T15:00:00Z",
                    "expiresAt": "2026-11-16T15:00:00Z",
                    "remainingCredits": 100,
                    "source": "cloudflare-wallet-balance-verification",
                    "transferable": False,
                    "cashRedeemable": False,
                    "status": "ledger_recorded",
                }],
            },
            "service-requests": {
                "records": [{
                    "serviceRequestId": "gca_service_req_1",
                    "status": "queued_operator_review",
                    "createdAt": "2026-05-20T15:05:00Z",
                    "accountId": "gca_account_1",
                    "email": "user@example.com",
                    "emailSha256": "0" * 64,
                    "walletAddress": "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
                    "creditLedgerId": "gca_credit_1",
                    "serviceId": "risk-warning-review",
                    "serviceName": "Risk Warning Review",
                    "requestedCreditHold": 10,
                    "remainingCreditsAtRequest": 100,
                    "requestTitle": "Risk warning review",
                    "requestSummary": "Review a position plan before manual action.",
                    "marketContext": "BTC/ETH volatility watch.",
                    "preferredLanguage": "zh-CN",
                    "source": "gca-service-request-operator",
                    "operatorReviewRequired": True,
                    "doesNotDeductCredits": True,
                    "requiresSignature": False,
                    "requiresTransaction": False,
                    "automaticTokenTransfer": False,
                    "writesWallet": False,
                    "createsTradingPermission": False,
                }],
            },
            "service-request-reviews": {
                "records": [{
                    "serviceRequestReviewId": "gca_service_review_1",
                    "serviceRequestId": "gca_service_req_1",
                    "packetVersion": "gca_service_request_review_v1",
                    "decision": "needs_more_information",
                    "reasonCode": "scope_incomplete",
                    "reviewerId": "gca-operator",
                    "operatorNote": "Internal review note.",
                    "memberPrompt": "Please add the intended timeframe.",
                    "deliveryReference": "",
                    "creditUsageId": "",
                    "creditAmountUsed": 0,
                    "remainingCreditsBefore": 100,
                    "remainingCreditsAfter": 100,
                    "reviewedAt": "2026-05-20T15:06:00Z",
                    "source": "gca-service-request-review-operator-cli",
                    "manualReviewCompleted": True,
                    "deliveryCompleted": False,
                    "creditsDeducted": False,
                    "requiresSignature": False,
                    "requiresTransaction": False,
                    "automaticTokenTransfer": False,
                    "writesWallet": False,
                    "createsTradingPermission": False,
                }],
            },
            "service-request-followups": {
                "records": [{
                    "serviceRequestFollowupId": "gca_service_followup_1",
                    "serviceRequestId": "gca_service_req_1",
                    "accountId": "gca_account_1",
                    "clientFollowupId": "gca_client_followup_example",
                    "packetVersion": "gca_account_service_request_followup_v1",
                    "responseText": "The intended timeframe is four hours.",
                    "submittedAt": "2026-05-20T15:07:00Z",
                    "source": "gca-member-access-service-request-followup",
                    "noSecretsNoCustody": True,
                    "manualReviewOnly": True,
                    "changesCredits": False,
                    "requiresSignature": False,
                    "requiresTransaction": False,
                    "automaticTokenTransfer": False,
                    "writesWallet": False,
                    "createsTradingPermission": False,
                }],
            },
            "credit-usage": {
                "records": [{
                    "creditUsageId": "gca_credit_use_1",
                    "creditLedgerId": "gca_credit_1",
                    "accountId": "gca_account_1",
                    "walletAddress": "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
                    "serviceId": "risk-warning-review",
                    "serviceName": "Risk Warning Review",
                    "creditAmountUsed": 10,
                    "remainingCreditsBefore": 100,
                    "remainingCreditsAfter": 90,
                    "usedAt": "2026-05-20T15:10:00Z",
                    "source": "gca-credit-usage-operator",
                    "operatorNote": "Delivered risk warning review.",
                    "status": "usage_recorded",
                }],
            },
            "member-ledger": {
                "records": [
                    {
                        "memberLedgerId": "gca_member_1",
                        "accountId": "gca_account_1",
                        "walletAddress": "0x18d0007bc6be029f8ccd7cb13e324aa21891092d",
                        "tierName": "GCA Member",
                        "verifiedBalance": "1000000",
                        "holdingStartDate": "2026-04-19",
                        "holdingPeriodDaysVerified": 31,
                        "evidenceTxHash": "0x" + "1" * 64,
                        "evidenceTxHashFormatOk": True,
                        "memberBenefitReviewEvidenceStatus": "eligible",
                        "memberBenefitAmount": "10000 GCA",
                        "memberBenefitClaimStatus": "pending_manual_reserve_transfer",
                        "memberBenefitTransferTx": "",
                        "activatedAt": "2026-05-20T15:00:00Z",
                        "nextRefreshDueAt": "2026-06-19T15:00:00Z",
                        "requiresManualReserveTransferReview": True,
                        "automaticTransfer": False,
                        "status": "active",
                        "updatedAt": "2026-05-20T15:00:00Z",
                    },
                    {
                        "memberLedgerId": "gca_member_2",
                        "accountId": "gca_account_2",
                        "walletAddress": "0x28d0007bc6be029f8ccd7cb13e324aa21891092d",
                        "tierName": "GCA Member",
                        "verifiedBalance": "1000000",
                        "holdingStartDate": "2026-05-19",
                        "holdingPeriodDaysVerified": 1,
                        "evidenceTxHash": "",
                        "evidenceTxHashFormatOk": False,
                        "memberBenefitReviewEvidenceStatus": "needs_more_information",
                        "memberBenefitAmount": "10000 GCA",
                        "memberBenefitClaimStatus": "needs_holding_period_review",
                        "memberBenefitTransferTx": "",
                        "activatedAt": "",
                        "nextRefreshDueAt": "",
                        "requiresManualReserveTransferReview": True,
                        "automaticTransfer": False,
                        "status": "queued",
                        "updatedAt": "2026-05-20T15:00:00Z",
                    },
                ],
            },
        },
    }


class GcaMemberAccessReportTests(unittest.TestCase):
    def test_build_report_writes_csvs_and_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output_dir = root / "report"
            summary_output = output_dir / "summary.json"
            summary = build_report(member_access_export_payload(), output_dir, summary_output)

            self.assertTrue(summary["ok"])
            self.assertEqual(summary["counts"]["accounts"], 1)
            self.assertEqual(summary["counts"]["creditLedgerRecorded"], 1)
            self.assertEqual(summary["counts"]["serviceRequestRecords"], 1)
            self.assertEqual(summary["counts"]["serviceRequestsPendingReview"], 1)
            self.assertEqual(summary["counts"]["queuedServiceRequests"], 1)
            self.assertEqual(summary["counts"]["serviceRequestsExpiredCreditLedger"], 0)
            self.assertEqual(summary["counts"]["serviceRequestsAwaitingMemberFollowup"], 0)
            self.assertEqual(summary["counts"]["serviceRequestsAwaitingDelivery"], 0)
            self.assertEqual(summary["counts"]["deliveredServiceRequests"], 0)
            self.assertEqual(summary["counts"]["requestedCreditHoldQueued"], 10)
            self.assertEqual(summary["counts"]["serviceRequestReviewRecords"], 1)
            self.assertEqual(summary["counts"]["serviceRequestReviewsNeedMoreInformation"], 1)
            self.assertEqual(summary["counts"]["serviceRequestFollowupRecords"], 1)
            self.assertEqual(summary["counts"]["creditUsageRecords"], 1)
            self.assertEqual(summary["counts"]["creditUsageRecorded"], 1)
            self.assertEqual(summary["counts"]["creditsConsumed"], 10)
            self.assertEqual(summary["counts"]["activeGcaMembers"], 1)
            self.assertEqual(summary["counts"]["queuedGcaMembers"], 1)
            self.assertEqual(summary["counts"]["pendingManualReserveTransfers"], 1)
            self.assertEqual(summary["counts"]["holdingPeriodReviewsNeeded"], 1)
            self.assertEqual(summary["counts"]["memberBenefitReviewQueueRows"], 2)
            self.assertFalse(summary["boundaries"]["writesProductionData"])
            self.assertFalse(summary["boundaries"]["automaticTokenTransfer"])
            self.assertTrue(summary["boundaries"]["serviceRouteReportsReadOnly"])
            self.assertTrue(summary_output.exists())
            self.assertTrue(Path(summary["outputs"]["serviceRequestsCsv"]).exists())
            self.assertTrue(Path(summary["outputs"]["serviceRequestReviewsCsv"]).exists())
            self.assertTrue(Path(summary["outputs"]["serviceRequestFollowupsCsv"]).exists())
            self.assertTrue(Path(summary["outputs"]["creditUsageCsv"]).exists())

            with Path(summary["outputs"]["memberBenefitReviewQueueCsv"]).open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["reviewLane"], "pending_manual_reserve_transfer")
            self.assertEqual(rows[1]["reviewLane"], "holding_period_review")

    def test_build_report_counts_current_service_request_lanes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payload = member_access_export_payload()
            statuses = (
                "queued_operator_review",
                "queued_insufficient_credits",
                "queued_expired_credit_ledger",
                "queued_missing_credit_ledger",
                "needs_more_information",
                "approved_operator_review",
                "delivered",
                "rejected_operator_review",
                "cancelled_by_account",
            )
            payload["datasets"]["service-requests"]["records"] = [
                {
                    "serviceRequestId": f"gca_service_req_{index}",
                    "status": status,
                    "requestedCreditHold": 1,
                }
                for index, status in enumerate(statuses, start=1)
            ]

            summary = build_report(payload, root / "report", root / "report" / "summary.json")
            counts = summary["counts"]

            self.assertEqual(counts["serviceRequestRecords"], 9)
            self.assertEqual(counts["serviceRequestsPendingReview"], 4)
            self.assertEqual(counts["queuedServiceRequests"], 1)
            self.assertEqual(counts["serviceRequestsInsufficientCredits"], 1)
            self.assertEqual(counts["serviceRequestsExpiredCreditLedger"], 1)
            self.assertEqual(counts["serviceRequestsMissingCreditLedger"], 1)
            self.assertEqual(counts["serviceRequestsAwaitingMemberFollowup"], 1)
            self.assertEqual(counts["serviceRequestsAwaitingDelivery"], 1)
            self.assertEqual(counts["deliveredServiceRequests"], 1)
            self.assertEqual(counts["rejectedServiceRequests"], 1)
            self.assertEqual(counts["cancelledServiceRequests"], 1)

    def test_load_export_rejects_wrong_packet(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text(json.dumps({"ok": True, "packetVersion": "wrong", "datasets": {}}), encoding="utf-8")
            with self.assertRaises(Exception):
                load_export(path)

    def test_cli_builds_report_from_export_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_path = root / "export.json"
            output_dir = root / "report"
            summary_output = root / "summary.json"
            input_path.write_text(json.dumps(member_access_export_payload()), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/build_gca_member_access_report.py",
                    "--input",
                    str(input_path),
                    "--output-dir",
                    str(output_dir),
                    "--summary-output",
                    str(summary_output),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"])
            self.assertTrue((output_dir / "gca_member_accounts.csv").exists())
            self.assertTrue((output_dir / "gca_member_benefit_review_queue.csv").exists())
            self.assertTrue(summary_output.exists())


if __name__ == "__main__":
    unittest.main()
