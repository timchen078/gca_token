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
    CONTRACT_ADDRESS,
    HOLDER_THRESHOLD_UNITS,
    MEMBER_THRESHOLD_UNITS,
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


class FixedBalanceReader:
    def __init__(self, balance_units):
        self.balance_units = balance_units
        self.wallets = []

    def get_balance_units(self, wallet):
        self.wallets.append(wallet)
        return self.balance_units


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
    def make_backend(self, balance_units):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = JsonlLedgerStore(Path(temp.name))
        backend = GcaMemberBackend(store=store, balance_reader=FixedBalanceReader(balance_units))
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
        self.assertEqual(summary["dataLedgers"]["support_reviews"]["count"], 1)
        self.assertTrue(summary["operatorBoundaries"]["readOnlyWalletVerification"])

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
