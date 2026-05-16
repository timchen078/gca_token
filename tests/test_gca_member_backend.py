import json
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
    HOLDER_THRESHOLD_UNITS,
    MEMBER_BENEFIT_UNITS,
    MEMBER_THRESHOLD_UNITS,
    TRANSFER_TOPIC,
    GcaMemberBackend,
    JsonlLedgerStore,
    BackendError,
    balance_of_calldata,
    build_handler,
    holding_days_from_date,
    read_json_request,
    units_to_gca,
)


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
            self.assertEqual(summary["dataLedgers"]["pre_registrations"]["count"], 1)
            self.assertFalse(summary["publicSelfServiceClaim"])
            self.assertFalse(summary["automaticTokenTransfer"])

            with urlopen(f"{base_url}/gca/review-package?limit=5", timeout=10) as response:
                review_package = json.loads(response.read().decode())
            self.assertTrue(review_package["ok"])
            self.assertEqual(review_package["packageType"], "gca-local-review-package")
            self.assertEqual(review_package["localEndpoint"], "/gca/review-package")
            self.assertEqual(review_package["operatorSummary"]["dataLedgers"]["pre_registrations"]["count"], 1)
            self.assertFalse(review_package["publicSelfServiceClaim"])
            self.assertFalse(review_package["automaticTokenTransfer"])
            self.assertTrue(review_package["exportBoundaries"]["localhostOnly"])

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
