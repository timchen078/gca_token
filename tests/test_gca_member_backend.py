import json
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import UTC, datetime, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tools.gca_member_backend import (
    BaseRpcBalanceReader,
    CONTRACT_ADDRESS,
    EMAIL_REGISTRATION_VERSION,
    HOLDER_THRESHOLD_UNITS,
    MEMBER_BENEFIT_UNITS,
    MEMBER_THRESHOLD_UNITS,
    REDACTED_EXTERNAL_VALUE,
    TRANSFER_TOPIC,
    GcaMemberBackend,
    JsonlLedgerStore,
    BackendError,
    balance_of_calldata,
    build_handler,
    holding_days_from_date,
    read_json_request,
    units_to_gca,
    verify_package_digest,
)


ROOT = Path(__file__).resolve().parents[1]
WALLET = "0x18d0007bc6be029f8ccd7cb13e324aa21891092d"
TRANSFER_TX = "0x" + "b" * 64
SOURCE_WALLET = "0x5e8F84748612B913aAcC937492AC25dc5630E246"


class FixedBalanceReader:
    def __init__(self, balance_units, transfer_evidence=None):
        self.balance_units = balance_units
        self.wallets = []
        self.transfer_evidence = transfer_evidence
        self.transfer_requests = []

    def get_balance_units(self, wallet):
        self.wallets.append(wallet)
        return self.balance_units

    def get_transfer_evidence(self, tx_hash, recipient_wallet, source_wallet=""):
        self.transfer_requests.append({
            "txHash": tx_hash,
            "recipientWallet": recipient_wallet,
            "sourceWallet": source_wallet,
        })
        if self.transfer_evidence is not None:
            return dict(self.transfer_evidence)
        return {
            "status": "verified",
            "chainId": 8453,
            "contractAddress": CONTRACT_ADDRESS,
            "transactionHash": tx_hash,
            "recipientWallet": recipient_wallet.lower(),
            "sourceWallet": source_wallet.lower(),
            "expectedMinimumAmount": "10000 GCA",
            "expectedMinimumAmountUnits": str(MEMBER_BENEFIT_UNITS),
            "matchedTransfer": True,
            "matchedTransferAmount": "10000",
            "matchedTransferAmountUnits": str(MEMBER_BENEFIT_UNITS),
            "matchedFrom": source_wallet.lower(),
            "matchedTo": recipient_wallet.lower(),
            "receiptStatus": "success",
            "readOnlyRpcMethod": "eth_getTransactionReceipt",
            "requiresSignature": False,
            "requiresTransaction": False,
            "automaticTransfer": False,
        }


class FixedReceiptReader(BaseRpcBalanceReader):
    def __init__(self, receipt):
        self.receipt = receipt
        self.calls = []

    def rpc(self, method, params):
        self.calls.append({"method": method, "params": params})
        return self.receipt


def sample_packet(wallet=WALLET):
    holding_start = (datetime.now(UTC).date() - timedelta(days=31)).isoformat()
    return {
        "packetVersion": "gca_member_preregistration_v2",
        "programIntent": "gca_member",
        "declaredGcaBalance": "1000000",
        "user": {
            "email": "member@example.com",
            "telegram": "@member",
            "walletAddress": wallet,
        },
        "memberBenefitReviewEvidence": {
            "holdingStartDate": holding_start,
            "evidenceTxHash": "0x" + "a" * 64,
            "evidenceNote": "Public purchase transaction supplied for local review.",
        },
        "acknowledgements": {
            "preRegistrationOnly": True,
            "noSecretsNoCustody": True,
        },
    }


class GcaMemberBackendTests(unittest.TestCase):
    def make_backend(self, balance_units, transfer_evidence=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = JsonlLedgerStore(Path(temp.name))
        backend = GcaMemberBackend(store=store, balance_reader=FixedBalanceReader(balance_units, transfer_evidence))
        return backend, store

    def test_balance_helpers_match_erc20_balanceof_contract(self):
        calldata = balance_of_calldata(WALLET)
        self.assertTrue(calldata.startswith("0x70a08231"))
        self.assertEqual(len(calldata), 74)
        self.assertIn(WALLET.removeprefix("0x").lower(), calldata)
        self.assertEqual(units_to_gca(HOLDER_THRESHOLD_UNITS), "10000")
        self.assertEqual(units_to_gca(MEMBER_THRESHOLD_UNITS), "1000000")
        self.assertGreaterEqual(
            holding_days_from_date((datetime.now(UTC).date() - timedelta(days=31)).isoformat()),
            30,
        )

    def test_transfer_receipt_verifier_matches_gca_transfer_log(self):
        receipt = {
            "status": "0x1",
            "logs": [
                {
                    "address": CONTRACT_ADDRESS,
                    "topics": [
                        TRANSFER_TOPIC,
                        "0x" + SOURCE_WALLET.removeprefix("0x").lower().rjust(64, "0"),
                        "0x" + WALLET.removeprefix("0x").lower().rjust(64, "0"),
                    ],
                    "data": hex(MEMBER_BENEFIT_UNITS),
                }
            ],
        }
        reader = FixedReceiptReader(receipt)
        evidence = reader.get_transfer_evidence(TRANSFER_TX, WALLET, SOURCE_WALLET)

        self.assertEqual(evidence["status"], "verified")
        self.assertTrue(evidence["matchedTransfer"])
        self.assertEqual(evidence["matchedTransferAmount"], "10000")
        self.assertEqual(evidence["matchedTransferAmountUnits"], str(MEMBER_BENEFIT_UNITS))
        self.assertEqual(evidence["readOnlyRpcMethod"], "eth_getTransactionReceipt")
        self.assertFalse(evidence["requiresSignature"])
        self.assertFalse(evidence["automaticTransfer"])
        self.assertEqual(reader.calls[0]["method"], "eth_getTransactionReceipt")

    def test_submit_pre_registration_creates_wallet_credit_and_member_records(self):
        backend, store = self.make_backend(MEMBER_THRESHOLD_UNITS)
        response = backend.submit_pre_registration(sample_packet())

        self.assertTrue(response["ok"])
        self.assertEqual(response["registration"]["status"], "received")
        self.assertEqual(response["walletVerification"]["contractAddress"], CONTRACT_ADDRESS)
        self.assertTrue(response["walletVerification"]["holderBonusEligible"])
        self.assertTrue(response["walletVerification"]["gcaMemberEligible"])
        self.assertTrue(response["walletVerification"]["gcaMemberHoldingPeriodEligible"])
        self.assertEqual(response["creditLedger"]["creditAmount"], 100)
        self.assertEqual(response["creditLedger"]["status"], "ledger_recorded")
        self.assertEqual(response["memberLedger"]["tierName"], "GCA Member")
        self.assertEqual(response["memberLedger"]["status"], "active")
        self.assertEqual(response["memberLedger"]["memberBenefitAmount"], "10000 GCA")
        self.assertEqual(response["memberLedger"]["memberBenefitClaimStatus"], "pending_manual_reserve_transfer")
        self.assertFalse(response["memberLedger"]["automaticTransfer"])
        self.assertEqual(response["memberReview"]["status"], "ledger_recorded")

        self.assertEqual(len(store.read_all("pre_registrations")), 1)
        self.assertEqual(len(store.read_all("wallet_verifications")), 1)
        self.assertEqual(len(store.read_all("credit_ledger")), 1)
        self.assertEqual(len(store.read_all("member_ledger")), 1)
        self.assertEqual(len(store.read_all("member_benefit_transfers")), 0)

        self.assertEqual(len(store.read_all("support_reviews")), 1)

        summary = backend.operator_summary()
        self.assertTrue(summary["ok"])
        self.assertFalse(summary["publicSelfServiceClaim"])
        self.assertFalse(summary["automaticTokenTransfer"])
        self.assertTrue(summary["localJsonlDataOnly"])
        self.assertEqual(summary["totals"]["preRegistrations"], 1)
        self.assertEqual(summary["totals"]["creditLedgerRecords"], 1)
        self.assertEqual(summary["totals"]["activeMembers"], 1)
        self.assertEqual(summary["totals"]["pendingManualReserveTransfers"], 1)
        self.assertEqual(summary["totals"]["memberBenefitTransfers"], 0)
        self.assertEqual(summary["dataLedgers"]["support_reviews"]["count"], 1)
        self.assertTrue(summary["operatorBoundaries"]["readOnlyWalletVerification"])

        transfer = backend.record_member_benefit_transfer({
            "memberLedgerId": response["memberLedger"]["memberLedgerId"],
            "memberBenefitTransferTx": TRANSFER_TX,
            "sourceWallet": SOURCE_WALLET,
            "recipientWallet": WALLET,
            "reviewerNote": "Manual reserve-wallet transfer completed and recorded locally.",
        })
        self.assertFalse(transfer["alreadyRecorded"])
        self.assertEqual(transfer["transferRecord"]["status"], "transferred")
        self.assertEqual(transfer["transferRecord"]["memberBenefitAmount"], "10000 GCA")
        self.assertEqual(transfer["transferRecord"]["memberBenefitTransferTx"], TRANSFER_TX)
        self.assertEqual(transfer["transferRecord"]["transferVerificationStatus"], "verified")
        self.assertTrue(transfer["transferRecord"]["transferVerification"]["matchedTransfer"])
        self.assertIn(TRANSFER_TX, transfer["transferRecord"]["memberBenefitTransferUrl"])
        self.assertFalse(transfer["transferRecord"]["automaticTransfer"])
        self.assertEqual(transfer["memberLedger"]["memberBenefitClaimStatus"], "transferred")
        self.assertEqual(transfer["memberLedger"]["transferVerificationStatus"], "verified")
        self.assertEqual(transfer["supportReview"]["memberBenefitTransferTx"], TRANSFER_TX)
        self.assertEqual(transfer["supportReview"]["transferVerificationStatus"], "verified")
        self.assertEqual(len(store.read_all("member_benefit_transfers")), 1)
        self.assertEqual(len(store.read_all("member_ledger")), 2)
        self.assertEqual(len(store.read_all("support_reviews")), 2)

        summary = backend.operator_summary()
        self.assertEqual(summary["totals"]["memberLedgerRecords"], 1)
        self.assertEqual(summary["totals"]["pendingManualReserveTransfers"], 0)
        self.assertEqual(summary["totals"]["memberBenefitTransfers"], 1)
        self.assertEqual(summary["totals"]["transferredMemberBenefits"], 1)

        review_package = backend.review_package()
        self.assertTrue(review_package["ok"])
        self.assertEqual(review_package["packageType"], "gca-local-review-package")
        self.assertEqual(review_package["localEndpoint"], "/gca/review-package")
        self.assertFalse(review_package["publicSelfServiceClaim"])
        self.assertFalse(review_package["automaticTokenTransfer"])
        self.assertTrue(review_package["exportBoundaries"]["localhostOnly"])
        self.assertTrue(review_package["exportBoundaries"]["readOnlyTransferReceiptVerification"])
        self.assertEqual(review_package["operatorSummary"]["totals"]["memberBenefitTransfers"], 1)
        self.assertIn("memberBenefitTransfer", review_package["publicReferences"])
        self.assertFalse(review_package["redactedForExternalSharing"])

        self.assertEqual(review_package["packageDigestAlgorithm"], "sha256-json-sort-keys-excluding-packageDigestSha256")
        self.assertRegex(review_package["packageDigestSha256"], r"^[a-f0-9]{64}$")
        self.assertEqual(review_package["recordManifest"]["ledgerCounts"]["member_benefit_transfers"], 1)
        self.assertEqual(review_package["recordManifest"]["latestRecordCounts"]["support_reviews"], 2)
        self.assertTrue(review_package["fullLocalExportWarning"]["internalOnly"])
        self.assertFalse(review_package["fullLocalExportWarning"]["externalSharingAllowed"])
        self.assertTrue(review_package["fullLocalExportWarning"]["operatorConfirmationRequired"])
        self.assertEqual(review_package["fullLocalExportWarning"]["externalSharingAlternative"], "GET /gca/review-package?redact=public")
        self.assertIn("reviewerNote", review_package["fullLocalExportWarning"]["mayContainLocalFields"])
        self.assertIn("Use redacted-public mode", review_package["fullLocalExportWarning"]["warning"])
        self.assertEqual(review_package["handoffInstructions"]["externalSharingMode"], "redacted-public")
        self.assertEqual(review_package["handoffInstructions"]["fullLocalMode"], "internal-only")
        self.assertIn("tools/export_gca_review_package.py", review_package["handoffInstructions"]["offlineRedactedExportCommand"])
        self.assertIn("tools/verify_gca_review_package.py", review_package["handoffInstructions"]["verifyCommand"])
        self.assertEqual(review_package["handoffInstructions"]["replyTemplatePage"], "https://gcagochina.com/platform-replies.html")
        self.assertIn("verify packageDigestSha256 before sending", review_package["handoffInstructions"]["beforeExternalSharing"])
        self.assertIn("support evidence only", review_package["handoffInstructions"]["publicClaimBoundary"])
        verification = verify_package_digest(review_package)
        self.assertTrue(verification["ok"])
        self.assertEqual(verification["status"], "verified")
        self.assertEqual(verification["expectedDigest"], review_package["packageDigestSha256"])

        redacted_package = backend.review_package(redacted=True)
        redacted_text = json.dumps(redacted_package)
        self.assertTrue(redacted_package["redactedForExternalSharing"])
        self.assertEqual(redacted_package["redactionPolicy"]["mode"], "redacted-public")
        self.assertRegex(redacted_package["packageDigestSha256"], r"^[a-f0-9]{64}$")
        self.assertNotEqual(redacted_package["packageDigestSha256"], review_package["packageDigestSha256"])
        self.assertEqual(redacted_package["recordManifest"]["ledgerCounts"], review_package["recordManifest"]["ledgerCounts"])
        self.assertEqual(
            redacted_package["operatorSummary"]["dataLedgers"]["pre_registrations"]["latest"][0]["email"],
            REDACTED_EXTERNAL_VALUE,
        )
        self.assertNotIn("member@example.com", redacted_text)
        self.assertNotIn("@member", redacted_text)
        self.assertNotIn("Manual reserve-wallet transfer completed and recorded locally.", redacted_text)
        self.assertIn(WALLET.lower(), redacted_text)
        self.assertIn(TRANSFER_TX, redacted_text)
        self.assertTrue(verify_package_digest(redacted_package)["ok"])

        tampered_package = json.loads(json.dumps(redacted_package))
        tampered_package["contactEmail"] = "changed@example.com"
        tampered_verification = verify_package_digest(tampered_package)
        self.assertFalse(tampered_verification["ok"])
        self.assertEqual(tampered_verification["status"], "digest_mismatch")

        with tempfile.TemporaryDirectory() as temp:
            package_path = Path(temp) / "gca-review-package.json"
            package_path.write_text(json.dumps(redacted_package), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "tools/verify_gca_review_package.py", str(package_path)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        cli_result = json.loads(completed.stdout)
        self.assertTrue(cli_result["ok"])
        self.assertEqual(cli_result["computedDigest"], redacted_package["packageDigestSha256"])

        with tempfile.TemporaryDirectory() as temp:
            export_path = Path(temp) / "gca-public-review-package.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/export_gca_review_package.py",
                    "--data-dir",
                    str(store.data_dir),
                    "--redact",
                    "public",
                    "--output",
                    str(export_path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            export_result = json.loads(completed.stdout)
            self.assertTrue(export_result["ok"])
            self.assertTrue(export_result["redactedForExternalSharing"])
            self.assertTrue(export_path.exists())
            exported_package = json.loads(export_path.read_text(encoding="utf-8"))
        exported_text = json.dumps(exported_package)
        self.assertTrue(exported_package["redactedForExternalSharing"])
        self.assertEqual(exported_package["redactionPolicy"]["mode"], "redacted-public")
        self.assertTrue(verify_package_digest(exported_package)["ok"])
        self.assertNotIn("member@example.com", exported_text)
        self.assertNotIn("@member", exported_text)
        self.assertIn(WALLET.lower(), exported_text)

        completed = subprocess.run(
            [
                sys.executable,
                "tools/export_gca_review_package.py",
                "--data-dir",
                str(store.data_dir),
                "--limit",
                "5",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        stdout_package = json.loads(completed.stdout)
        self.assertFalse(stdout_package["redactedForExternalSharing"])
        self.assertTrue(verify_package_digest(stdout_package)["ok"])
        self.assertEqual(stdout_package["recordManifest"]["limit"], 5)

        with tempfile.TemporaryDirectory() as temp:
            tampered_path = Path(temp) / "gca-review-package-tampered.json"
            tampered_path.write_text(json.dumps(tampered_package), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "tools/verify_gca_review_package.py", str(tampered_path)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 1)
        cli_result = json.loads(completed.stdout)
        self.assertFalse(cli_result["ok"])
        self.assertEqual(cli_result["status"], "digest_mismatch")

        duplicate = backend.record_member_benefit_transfer({
            "memberLedgerId": response["memberLedger"]["memberLedgerId"],
            "memberBenefitTransferTx": TRANSFER_TX,
            "recipientWallet": WALLET,
        })
        self.assertTrue(duplicate["alreadyRecorded"])
        self.assertEqual(duplicate["transferRecord"]["transferRecordId"], transfer["transferRecord"]["transferRecordId"])
        self.assertEqual(duplicate["memberLedger"]["memberBenefitClaimStatus"], "transferred")
        self.assertEqual(len(store.read_all("member_benefit_transfers")), 1)
        self.assertEqual(len(store.read_all("member_ledger")), 2)

    def test_operator_digest_reads_redacted_local_digest_without_user_records(self):
        backend, store = self.make_backend(MEMBER_THRESHOLD_UNITS)
        digest_path = store.data_dir / "gca_operator_digest.json"
        digest_path.write_text(json.dumps({
            "ok": True,
            "packetVersion": "gca_operator_digest_v1",
            "generatedAt": "2026-05-20T16:38:07Z",
            "sourceFiles": {
                "dailyOps": {
                    "path": "/private/path/.gca_access_data/gca_daily_ops_summary.json",
                    "exists": True,
                    "ok": True,
                    "generatedAt": "2026-05-20T16:38:07Z",
                    "packetVersion": "gca_daily_ops_summary_v1",
                }
            },
            "dailyOps": {
                "available": True,
                "ok": True,
                "generatedAt": "2026-05-20T16:38:07Z",
                "includeMemberOps": False,
                "includeHoldingReport": False,
                "steps": [{"id": "public-site", "ok": True, "returnCode": 0, "stdoutTail": "private-user@example.com"}],
                "baseScanPreflight": {
                    "available": True,
                    "readyForBaseScanResubmission": False,
                    "status": "blocked-before-basescan-resubmission",
                    "publicEmailSwitchStatus": "public-email-switch-pending",
                    "filesStillUsingOldEmail": 14,
                    "missingOrBlockedRequirements": [
                        "official-domain-email",
                        "domain-email-public-switch-check",
                        "private-user@example.com",
                    ],
                },
            },
            "memberOps": {
                "available": True,
                "ok": True,
                "recordCount": 12,
                "supportQueue": {"rows": 3, "replyReadyRows": 1, "statusCounts": {"reply_ready": 1}},
                "report": {"pendingManualReserveTransfers": 2, "privateRecord": "private-user@example.com"},
                "holdingPeriod": {"observedEligibleFor30Days": 1, "walletsChecked": 4},
            },
            "supportQueue": {"available": True, "ok": True, "rows": 3, "replyReadyRows": 1},
            "holdingPeriod": {
                "available": True,
                "ok": True,
                "counts": {"observedEligibleFor30Days": 1},
                "laneCounts": {"continue_daily_snapshots": 2},
            },
            "nextActions": ["Review support queue for private-user@example.com"],
            "outputs": {
                "markdown": "/private/path/.gca_access_data/gca_operator_digest.md",
                "json": "/private/path/.gca_access_data/gca_operator_digest.json",
            },
        }), encoding="utf-8")

        digest = backend.operator_digest()
        self.assertTrue(digest["ok"])
        self.assertTrue(digest["available"])
        self.assertEqual(digest["status"], "loaded")
        self.assertEqual(digest["packetVersion"], "gca_operator_digest_v1")
        self.assertEqual(digest["sourceFileStatus"]["dailyOps"]["fileName"], "gca_daily_ops_summary.json")
        self.assertEqual(digest["outputs"]["markdownFile"], "gca_operator_digest.md")
        self.assertEqual(digest["dailyOps"]["steps"][0]["id"], "public-site")
        self.assertFalse(digest["dailyOps"]["baseScanPreflight"]["readyForBaseScanResubmission"])
        self.assertEqual(digest["dailyOps"]["baseScanPreflight"]["status"], "blocked-before-basescan-resubmission")
        self.assertEqual(digest["dailyOps"]["baseScanPreflight"]["filesStillUsingOldEmail"], 14)
        self.assertIn("official-domain-email", digest["dailyOps"]["baseScanPreflight"]["missingOrBlockedRequirements"])
        self.assertEqual(digest["memberOps"]["recordCount"], 12)
        self.assertEqual(digest["supportQueue"]["replyReadyRows"], 1)
        self.assertEqual(digest["holdingPeriod"]["counts"]["observedEligibleFor30Days"], 1)
        self.assertFalse(digest["boundaries"]["writesProductionData"])
        self.assertFalse(digest["boundaries"]["walletCalls"])
        self.assertFalse(digest["boundaries"]["requiresSignature"])
        self.assertFalse(digest["boundaries"]["automaticTokenTransfer"])
        serialized = json.dumps(digest)
        self.assertNotIn("private-user@example.com", serialized)
        self.assertNotIn("stdoutTail", serialized)
        self.assertNotIn("/private/path", serialized)

    def test_operator_digest_reports_missing_file_as_non_writing_local_status(self):
        backend, _store = self.make_backend(MEMBER_THRESHOLD_UNITS)
        digest = backend.operator_digest()

        self.assertTrue(digest["ok"])
        self.assertFalse(digest["available"])
        self.assertEqual(digest["status"], "missing")
        self.assertEqual(digest["digestFile"], "gca_operator_digest.json")
        self.assertTrue(any("run_gca_daily_ops.py --build-digest" in action for action in digest["nextActions"]))
        self.assertFalse(digest["boundaries"]["writesProductionData"])
        self.assertFalse(digest["boundaries"]["automaticTokenTransfer"])

    def test_operator_action_plan_prioritizes_manual_work_without_user_records(self):
        backend, store = self.make_backend(MEMBER_THRESHOLD_UNITS)
        response = backend.submit_pre_registration(sample_packet())
        digest_path = store.data_dir / "gca_operator_digest.json"
        digest_path.write_text(json.dumps({
            "ok": True,
            "packetVersion": "gca_operator_digest_v1",
            "generatedAt": "2026-05-20T16:38:07Z",
            "dailyOps": {
                "available": True,
                "ok": True,
                "steps": [],
                "baseScanPreflight": {
                    "available": True,
                    "readyForBaseScanResubmission": False,
                    "status": "blocked-before-basescan-resubmission",
                    "publicEmailSwitchStatus": "public-email-switch-pending",
                    "filesStillUsingOldEmail": 14,
                    "missingOrBlockedRequirements": ["official-domain-email", "domain-email-public-switch-check"],
                },
            },
            "memberOps": {
                "available": True,
                "ok": True,
                "supportQueue": {"rows": 2, "replyReadyRows": 1},
            },
            "supportQueue": {"available": True, "ok": True, "rows": 2, "replyReadyRows": 1},
            "holdingPeriod": {"available": True, "ok": True, "counts": {"observedEligibleFor30Days": 1}},
            "nextActions": ["Review private-user@example.com support queue."],
        }), encoding="utf-8")

        plan = backend.operator_action_plan(limit=5)
        self.assertTrue(plan["ok"])
        self.assertEqual(plan["packetVersion"], "gca_operator_action_plan_v1")
        self.assertTrue(plan["sourceStatus"]["operatorDigestAvailable"])
        self.assertTrue(plan["sourceStatus"]["operatorDigestOk"])
        item_ids = {item["id"] for item in plan["items"]}
        self.assertIn("review-support-replies", item_ids)
        self.assertIn("review-pending-reserve-transfers", item_ids)
        self.assertIn("review-holding-ready-wallets", item_ids)
        self.assertIn("complete-basescan-preflight", item_ids)
        self.assertTrue(plan["supportReviewPreview"])
        self.assertEqual(plan["supportReviewPreview"][0]["memberLedgerId"], response["memberLedger"]["memberLedgerId"])
        self.assertFalse(plan["boundaries"]["writesProductionData"])
        self.assertFalse(plan["boundaries"]["walletCalls"])
        self.assertFalse(plan["boundaries"]["requiresSignature"])
        self.assertFalse(plan["boundaries"]["automaticTokenTransfer"])
        serialized = json.dumps(plan)
        self.assertNotIn("member@example.com", serialized)
        self.assertNotIn("private-user@example.com", serialized)

    def test_operator_action_plan_handles_missing_digest(self):
        backend, _store = self.make_backend(MEMBER_THRESHOLD_UNITS)
        plan = backend.operator_action_plan()

        self.assertTrue(plan["ok"])
        self.assertFalse(plan["sourceStatus"]["operatorDigestAvailable"])
        self.assertTrue(any(item["id"] == "build-operator-digest" for item in plan["items"]))
        self.assertFalse(plan["boundaries"]["writesProductionData"])
        self.assertFalse(plan["boundaries"]["automaticUserReply"])

    def test_record_support_review_update_appends_local_operator_status(self):
        backend, store = self.make_backend(MEMBER_THRESHOLD_UNITS)
        response = backend.submit_pre_registration(sample_packet())
        parent_review = response["memberReview"]

        update = backend.record_support_review_update({
            "reviewId": parent_review["reviewId"],
            "memberLedgerId": response["memberLedger"]["memberLedgerId"],
            "status": "waiting_for_user_evidence",
            "nextStep": "Ask the member to provide a public Base transaction hash for the 30-day holding review.",
            "supportNote": "Operator prepared a follow-up note. No wallet signature or token transfer was requested.",
        })

        self.assertTrue(update["ok"])
        review = update["supportReview"]
        self.assertNotEqual(review["reviewId"], parent_review["reviewId"])
        self.assertEqual(review["parentReviewId"], parent_review["reviewId"])
        self.assertEqual(review["status"], "waiting_for_user_evidence")
        self.assertEqual(review["memberLedgerId"], response["memberLedger"]["memberLedgerId"])
        self.assertEqual(review["walletAddress"], WALLET.lower())
        self.assertFalse(review["automaticUserReply"])
        self.assertFalse(review["automaticTokenTransfer"])
        self.assertFalse(review["requiresSignature"])
        self.assertFalse(review["writesProductionData"])
        self.assertEqual(len(store.read_all("support_reviews")), 2)
        self.assertEqual(backend.query("support_reviews", {"parentReviewId": [parent_review["reviewId"]]})[0]["status"], "waiting_for_user_evidence")

        summary = backend.operator_summary()
        self.assertEqual(summary["dataLedgers"]["support_reviews"]["latest"][0]["status"], "waiting_for_user_evidence")

        with self.assertRaises(BackendError):
            backend.record_support_review_update({
                "reviewId": parent_review["reviewId"],
                "status": "unknown_status",
                "nextStep": "Unsupported status should fail.",
            })

    def test_submit_email_registration_records_email_only_user(self):
        backend, store = self.make_backend(0)
        response = backend.submit_email_registration({
            "packetVersion": EMAIL_REGISTRATION_VERSION,
            "email": "Customer@Example.com",
            "source": "register.html",
            "language": "zh-CN",
            "interests": ["gca_updates", "member_access"],
            "acknowledgements": {
                "emailContactConsent": True,
                "noSecretsNoCustody": True,
            },
        })

        self.assertTrue(response["ok"])
        self.assertFalse(response["alreadyRegistered"])
        self.assertEqual(response["emailRegistration"]["email"], "customer@example.com")
        self.assertEqual(response["emailRegistration"]["packetVersion"], EMAIL_REGISTRATION_VERSION)
        self.assertEqual(response["emailRegistration"]["status"], "received")
        self.assertFalse(response["emailRegistration"]["walletRequired"])
        self.assertFalse(response["emailRegistration"]["requiresSignature"])
        self.assertFalse(response["emailRegistration"]["requiresTransaction"])
        self.assertFalse(response["emailRegistration"]["requiresPrivateKey"])
        self.assertFalse(response["emailRegistration"]["requiresSeedPhrase"])
        self.assertFalse(response["emailRegistration"]["automaticTokenTransfer"])
        self.assertEqual(len(store.read_all("email_registrations")), 1)
        self.assertEqual(store.read_all("pre_registrations"), [])

        duplicate = backend.submit_email_registration({
            "email": "customer@example.com",
            "acknowledgements": {
                "emailContactConsent": True,
                "noSecretsNoCustody": True,
            },
        })
        self.assertTrue(duplicate["alreadyRegistered"])
        self.assertEqual(len(store.read_all("email_registrations")), 1)

    def test_email_registration_requires_valid_email_and_acknowledgements(self):
        backend, _store = self.make_backend(0)
        with self.assertRaises(BackendError):
            backend.submit_email_registration({
                "email": "not-an-email",
                "acknowledgements": {
                    "emailContactConsent": True,
                    "noSecretsNoCustody": True,
                },
            })
        with self.assertRaises(BackendError):
            backend.submit_email_registration({
                "email": "customer@example.com",
                "acknowledgements": {
                    "noSecretsNoCustody": True,
                },
            })
        with self.assertRaises(BackendError):
            backend.submit_email_registration({
                "email": "customer@example.com",
                "acknowledgements": {
                    "emailContactConsent": True,
                },
            })

    def test_member_benefit_transfer_requires_matching_read_only_receipt(self):
        backend, _store = self.make_backend(
            MEMBER_THRESHOLD_UNITS,
            transfer_evidence={
                "status": "contract_or_amount_mismatch",
                "matchedTransfer": False,
                "readOnlyRpcMethod": "eth_getTransactionReceipt",
                "requiresSignature": False,
                "automaticTransfer": False,
            },
        )
        response = backend.submit_pre_registration(sample_packet())
        with self.assertRaises(BackendError):
            backend.record_member_benefit_transfer({
                "memberLedgerId": response["memberLedger"]["memberLedgerId"],
                "memberBenefitTransferTx": TRANSFER_TX,
                "sourceWallet": SOURCE_WALLET,
                "recipientWallet": WALLET,
            })

    def test_member_benefit_transfer_requires_active_pending_member(self):
        backend, _store = self.make_backend(MEMBER_THRESHOLD_UNITS)
        packet = sample_packet()
        packet["memberBenefitReviewEvidence"] = {
            "holdingStartDate": "",
            "evidenceTxHash": "",
            "evidenceNote": "Needs later public holding-period evidence.",
        }
        response = backend.submit_pre_registration(packet)
        with self.assertRaises(BackendError):
            backend.record_member_benefit_transfer({
                "memberLedgerId": response["memberLedger"]["memberLedgerId"],
                "memberBenefitTransferTx": TRANSFER_TX,
                "recipientWallet": WALLET,
            })

    def test_below_threshold_registration_does_not_create_credit_or_member_records(self):
        backend, store = self.make_backend(9999)
        packet = sample_packet()
        packet["declaredGcaBalance"] = "9999"
        packet["programIntent"] = "holder_bonus"
        response = backend.submit_pre_registration(packet)

        self.assertTrue(response["ok"])
        self.assertFalse(response["walletVerification"]["holderBonusEligible"])
        self.assertEqual(response["walletVerification"]["status"], "below_threshold")
        self.assertIsNone(response["creditLedger"])
        self.assertIsNone(response["memberLedger"])
        self.assertEqual(response["memberReview"]["status"], "below_threshold")
        self.assertEqual(store.read_all("credit_ledger"), [])
        self.assertEqual(store.read_all("member_ledger"), [])

    def test_missing_member_evidence_keeps_member_record_queued(self):
        backend, store = self.make_backend(MEMBER_THRESHOLD_UNITS)
        packet = sample_packet()
        packet["memberBenefitReviewEvidence"] = {
            "holdingStartDate": "",
            "evidenceTxHash": "",
            "evidenceNote": "Needs later public holding-period evidence.",
        }
        response = backend.submit_pre_registration(packet)

        self.assertEqual(response["memberLedger"]["status"], "queued")
        self.assertEqual(response["memberLedger"]["memberBenefitReviewEvidenceStatus"], "needs_more_information")
        self.assertEqual(response["memberReview"]["status"], "needs_more_information")
        self.assertEqual(len(store.read_all("credit_ledger")), 1)
        self.assertEqual(len(store.read_all("member_ledger")), 1)

    def test_rejects_sensitive_key_names(self):
        with self.assertRaises(BackendError):
            read_json_request(json.dumps({"seedPhrase": "do not accept this"}).encode())

    def test_http_api_serves_pre_registration_and_ledger_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = root / "site"
            site.mkdir()
            (site / "members.html").write_text("<html>members</html>")
            store = JsonlLedgerStore(root / "data")
            backend = GcaMemberBackend(store=store, balance_reader=FixedBalanceReader(MEMBER_THRESHOLD_UNITS))
            server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(site, backend))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            base_url = f"http://127.0.0.1:{server.server_address[1]}"

            email_request = Request(
                f"{base_url}/gca/email-registrations",
                data=json.dumps({
                    "email": "waitlist@example.com",
                    "source": "register.html",
                    "acknowledgements": {
                        "emailContactConsent": True,
                        "noSecretsNoCustody": True,
                    },
                }).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(email_request, timeout=10) as response:
                email_payload = json.loads(response.read().decode())
            self.assertTrue(email_payload["ok"])
            self.assertEqual(email_payload["emailRegistration"]["email"], "waitlist@example.com")
            self.assertFalse(email_payload["emailRegistration"]["walletRequired"])

            with urlopen(f"{base_url}/gca/email-registrations?email=waitlist@example.com", timeout=10) as response:
                email_ledger = json.loads(response.read().decode())
            self.assertTrue(email_ledger["ok"])
            self.assertEqual(email_ledger["count"], 1)
            self.assertEqual(email_ledger["records"][0]["email"], "waitlist@example.com")

            request = Request(
                f"{base_url}/gca/pre-registrations",
                data=json.dumps(sample_packet()).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode())
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["creditLedger"]["status"], "ledger_recorded")

            with urlopen(f"{base_url}/gca/member-ledger?walletAddress={WALLET}", timeout=10) as response:
                ledger = json.loads(response.read().decode())
            self.assertTrue(ledger["ok"])
            self.assertEqual(ledger["count"], 1)
            self.assertEqual(ledger["records"][0]["walletAddress"], WALLET.lower())

            with urlopen(f"{base_url}/gca/operator-summary", timeout=10) as response:
                summary = json.loads(response.read().decode())
            self.assertTrue(summary["ok"])
            self.assertEqual(summary["totals"]["memberLedgerRecords"], 1)
            self.assertEqual(summary["totals"]["emailRegistrations"], 1)
            self.assertEqual(summary["dataLedgers"]["pre_registrations"]["count"], 1)
            self.assertEqual(summary["dataLedgers"]["email_registrations"]["count"], 1)
            self.assertFalse(summary["publicSelfServiceClaim"])
            self.assertFalse(summary["automaticTokenTransfer"])

            (store.data_dir / "gca_operator_digest.json").write_text(json.dumps({
                "ok": True,
                "packetVersion": "gca_operator_digest_v1",
                "generatedAt": "2026-05-20T16:38:07Z",
                "dailyOps": {
                    "available": True,
                    "ok": True,
                    "generatedAt": "2026-05-20T16:38:07Z",
                    "steps": [{"id": "public-site", "ok": True, "returnCode": 0}],
                    "baseScanPreflight": {
                        "available": True,
                        "readyForBaseScanResubmission": False,
                        "status": "blocked-before-basescan-resubmission",
                        "publicEmailSwitchStatus": "public-email-switch-pending",
                        "filesStillUsingOldEmail": 14,
                        "missingOrBlockedRequirements": ["official-domain-email"],
                    },
                },
                "memberOps": {
                    "available": True,
                    "ok": True,
                    "recordCount": 2,
                    "supportQueue": {"rows": 1, "replyReadyRows": 1},
                },
                "supportQueue": {"available": True, "ok": True, "rows": 1, "replyReadyRows": 1},
                "holdingPeriod": {"available": False, "ok": False, "counts": {}},
                "nextActions": ["Review one support queue row."],
                "outputs": {"markdown": "gca_operator_digest.md", "json": "gca_operator_digest.json"},
            }), encoding="utf-8")
            with urlopen(f"{base_url}/gca/operator-digest", timeout=10) as response:
                digest = json.loads(response.read().decode())
            self.assertTrue(digest["ok"])
            self.assertTrue(digest["available"])
            self.assertEqual(digest["status"], "loaded")
            self.assertEqual(digest["dailyOps"]["steps"][0]["id"], "public-site")
            self.assertEqual(digest["dailyOps"]["baseScanPreflight"]["status"], "blocked-before-basescan-resubmission")
            self.assertEqual(digest["supportQueue"]["replyReadyRows"], 1)
            self.assertFalse(digest["boundaries"]["automaticTokenTransfer"])

            with urlopen(f"{base_url}/gca/operator-action-plan?limit=5", timeout=10) as response:
                action_plan = json.loads(response.read().decode())
            self.assertTrue(action_plan["ok"])
            self.assertEqual(action_plan["packetVersion"], "gca_operator_action_plan_v1")
            self.assertTrue(action_plan["sourceStatus"]["operatorDigestAvailable"])
            self.assertTrue(any(item["id"] == "review-support-replies" for item in action_plan["items"]))
            self.assertTrue(any(item["id"] == "complete-basescan-preflight" for item in action_plan["items"]))
            self.assertFalse(action_plan["boundaries"]["automaticTokenTransfer"])

            review_request = Request(
                f"{base_url}/gca/member-review",
                data=json.dumps({
                    "reviewId": payload["memberReview"]["reviewId"],
                    "memberLedgerId": payload["memberLedger"]["memberLedgerId"],
                    "status": "contacted",
                    "nextStep": "Support contacted the member and is waiting for public evidence confirmation.",
                    "supportNote": "Local HTTP API status update.",
                }).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(review_request, timeout=10) as response:
                review_update = json.loads(response.read().decode())
            self.assertTrue(review_update["ok"])
            self.assertEqual(review_update["supportReview"]["status"], "contacted")
            self.assertFalse(review_update["supportReview"]["automaticUserReply"])
            self.assertFalse(review_update["boundaries"]["automaticTokenTransfer"])

            with urlopen(f"{base_url}/gca/member-review?parentReviewId={payload['memberReview']['reviewId']}", timeout=10) as response:
                review_ledger = json.loads(response.read().decode())
            self.assertTrue(review_ledger["ok"])
            self.assertEqual(review_ledger["count"], 1)
            self.assertEqual(review_ledger["records"][0]["status"], "contacted")

            with urlopen(f"{base_url}/gca/review-package?limit=5", timeout=10) as response:
                review_package = json.loads(response.read().decode())
            self.assertTrue(review_package["ok"])
            self.assertEqual(review_package["packageType"], "gca-local-review-package")
            self.assertEqual(review_package["localEndpoint"], "/gca/review-package")
            self.assertEqual(review_package["operatorSummary"]["dataLedgers"]["pre_registrations"]["count"], 1)
            self.assertEqual(review_package["operatorSummary"]["dataLedgers"]["email_registrations"]["count"], 1)
            self.assertFalse(review_package["publicSelfServiceClaim"])
            self.assertFalse(review_package["automaticTokenTransfer"])
            self.assertTrue(review_package["exportBoundaries"]["localhostOnly"])
            self.assertRegex(review_package["packageDigestSha256"], r"^[a-f0-9]{64}$")
            self.assertEqual(review_package["recordManifest"]["ledgerCounts"]["pre_registrations"], 1)
            self.assertEqual(review_package["recordManifest"]["ledgerCounts"]["email_registrations"], 1)
            self.assertTrue(review_package["fullLocalExportWarning"]["operatorConfirmationRequired"])
            self.assertEqual(review_package["handoffInstructions"]["externalSharingMode"], "redacted-public")
            self.assertIn("tools/verify_gca_review_package.py", review_package["handoffInstructions"]["verifyCommand"])

            with urlopen(f"{base_url}/gca/review-package?limit=5&redact=public", timeout=10) as response:
                redacted_package = json.loads(response.read().decode())
            redacted_text = json.dumps(redacted_package)
            self.assertTrue(redacted_package["redactedForExternalSharing"])
            self.assertEqual(redacted_package["redactionPolicy"]["mode"], "redacted-public")
            self.assertRegex(redacted_package["packageDigestSha256"], r"^[a-f0-9]{64}$")
            self.assertNotIn("member@example.com", redacted_text)
            self.assertNotIn("waitlist@example.com", redacted_text)
            self.assertNotIn("@member", redacted_text)
            self.assertIn(WALLET.lower(), redacted_text)

            transfer_request = Request(
                f"{base_url}/gca/member-benefit-transfers",
                data=json.dumps({
                    "memberLedgerId": payload["memberLedger"]["memberLedgerId"],
                    "memberBenefitTransferTx": TRANSFER_TX,
                    "sourceWallet": SOURCE_WALLET,
                    "recipientWallet": WALLET,
                    "reviewerNote": "Manual transfer recorded through local HTTP API.",
                }).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(transfer_request, timeout=10) as response:
                transfer = json.loads(response.read().decode())
            self.assertTrue(transfer["ok"])
            self.assertEqual(transfer["transferRecord"]["status"], "transferred")
            self.assertEqual(transfer["memberLedger"]["memberBenefitClaimStatus"], "transferred")

            with urlopen(f"{base_url}/gca/member-benefit-transfers?memberLedgerId={payload['memberLedger']['memberLedgerId']}", timeout=10) as response:
                transfer_ledger = json.loads(response.read().decode())
            self.assertTrue(transfer_ledger["ok"])
            self.assertEqual(transfer_ledger["count"], 1)

            bad_request = Request(
                f"{base_url}/gca/pre-registrations",
                data=json.dumps({"walletAddress": WALLET, "privateKey": "bad"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(HTTPError) as ctx:
                urlopen(bad_request, timeout=10)
            self.assertEqual(ctx.exception.code, 400)
            ctx.exception.close()


if __name__ == "__main__":
    unittest.main()
