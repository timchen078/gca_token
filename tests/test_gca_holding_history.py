import json
import shutil
import sqlite3
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER_DIR = ROOT / "cloudflare" / "gca-registration-worker"
WORKER_SOURCE = WORKER_DIR / "src" / "worker.mjs"
HISTORY_MODULE = WORKER_DIR / "src" / "holding-history.mjs"
MIGRATIONS = [
    WORKER_DIR / "migrations" / "0003_member_access_ledgers.sql",
    WORKER_DIR / "migrations" / "0006_member_reviews.sql",
    WORKER_DIR / "migrations" / "0007_holding_history_verifications.sql",
]
BUNDLED_NODE = (
    Path.home()
    / ".cache"
    / "codex-runtimes"
    / "codex-primary-runtime"
    / "dependencies"
    / "node"
    / "bin"
    / "node"
)


class GcaHoldingHistoryTests(unittest.TestCase):
    def test_migration_adds_append_only_holding_evidence_and_member_links(self):
        database = sqlite3.connect(":memory:")
        try:
            for migration in MIGRATIONS:
                database.executescript(migration.read_text(encoding="utf-8"))

            holding_columns = {
                row[1]
                for row in database.execute(
                    "PRAGMA table_info(gca_holding_verifications)"
                ).fetchall()
            }
            member_columns = {
                row[1]
                for row in database.execute("PRAGMA table_info(gca_member_ledger)").fetchall()
            }
            review_columns = {
                row[1]
                for row in database.execute("PRAGMA table_info(gca_member_reviews)").fetchall()
            }

            self.assertIn("minimum_raw_balance", holding_columns)
            self.assertIn("observed_continuous_eligible", holding_columns)
            self.assertIn("history_complete", holding_columns)
            self.assertIn("reconstruction_consistent", holding_columns)
            self.assertIn("automatic_token_transfer", holding_columns)
            self.assertIn("latest_holding_verification_id", member_columns)
            self.assertIn("onchain_holding_verified", member_columns)
            self.assertIn("holding_verification_id", review_columns)
            self.assertIn("onchain_minimum_balance", review_columns)
        finally:
            database.close()

    def test_holding_history_module_reconstructs_minimum_balance(self):
        node = shutil.which("node") or (str(BUNDLED_NODE) if BUNDLED_NODE.exists() else "")
        if not node:
            self.skipTest("Node.js is not available")
        script = r"""
import { pathToFileURL } from "node:url";
const history = await import(pathToFileURL(process.argv[1]).href);
const wallet = "0x1111111111111111111111111111111111111111";
const other = "0x2222222222222222222222222222222222222222";
const eligible = history.reconstructHoldingWindow({
  walletAddress: wallet,
  currentBalanceUnits: "1500000",
  thresholdUnits: "1000000",
  events: [
    {key:"0x01:1",blockNumber:30,logIndex:1,fromAddress:wallet,toAddress:other,amountUnits:"200000",source:"base-blockscout-v2"},
    {key:"0x02:1",blockNumber:20,logIndex:1,fromAddress:other,toAddress:wallet,amountUnits:"700000",source:"base-blockscout-v2"}
  ]
});
const below = history.reconstructHoldingWindow({
  walletAddress: wallet,
  currentBalanceUnits: "1200000",
  thresholdUnits: "1000000",
  events: [
    {key:"0x03:1",blockNumber:20,logIndex:1,fromAddress:other,toAddress:wallet,amountUnits:"400000",source:"base-blockscout-v2"}
  ]
});
const inconsistent = history.reconstructHoldingWindow({
  walletAddress: wallet,
  currentBalanceUnits: "100",
  thresholdUnits: "50",
  events: [
    {key:"0x04:1",blockNumber:20,logIndex:1,fromAddress:other,toAddress:wallet,amountUnits:"200",source:"base-public-rpc"}
  ]
});
const deduped = history.dedupeTransferEvents([
  {key:"0x05:1",source:"base-blockscout-v2"},
  {key:"0x05:1",source:"base-public-rpc"}
]);
console.log(JSON.stringify({eligible, below, inconsistent, deduped}));
"""
        completed = subprocess.run(
            [node, "--input-type=module", "-e", script, str(HISTORY_MODULE)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)

        self.assertTrue(result["eligible"]["reconstructionConsistent"])
        self.assertTrue(result["eligible"]["observedContinuousEligible"])
        self.assertEqual(result["eligible"]["windowStartRawBalance"], "1000000")
        self.assertEqual(result["eligible"]["minimumRawBalance"], "1000000")
        self.assertFalse(result["below"]["observedContinuousEligible"])
        self.assertEqual(result["below"]["minimumRawBalance"], "800000")
        self.assertFalse(result["inconsistent"]["reconstructionConsistent"])
        self.assertEqual(
            result["inconsistent"]["failureReason"],
            "negative_reconstructed_balance",
        )
        self.assertEqual(len(result["deduped"]), 1)
        self.assertEqual(result["deduped"][0]["source"], "base-public-rpc")

    def test_worker_requires_observed_chain_history_for_approval(self):
        source = WORKER_SOURCE.read_text(encoding="utf-8")

        self.assertIn(
            'const HOLDING_VERIFICATION_VERSION = "gca_holding_verification_v1";',
            source,
        )
        self.assertIn(
            'const WORKER_RELEASE =\n  "gca-registration-worker-2026-07-30-delivery-receipt-v1";',
            source,
        )
        self.assertIn("verifyGcaHoldingWindow(memberRow, env)", source)
        self.assertIn("topics: [TRANSFER_EVENT_TOPIC, walletTopic]", source)
        self.assertIn("topics: [TRANSFER_EVENT_TOPIC, null, walletTopic]", source)
        self.assertIn("return dedupeTransferEvents(events)", source)
        self.assertIn("!holdingVerification.historyComplete", source)
        self.assertIn("!holdingVerification.reconstructionConsistent", source)
        self.assertIn("!holdingVerification.observedContinuousEligible", source)
        self.assertIn("gca_holding_verifications", source)
        self.assertIn('url.pathname === "/gca/holding-verifications"', source)
        self.assertIn("reviewBatch.unshift(preparedHoldingVerification.statement)", source)
        self.assertIn("readOnlyHoldingHistoryVerification: true", source)
        self.assertIn("automaticTokenTransfer: false", source)
        self.assertIn("authorizesMemberBenefitTransfer: false", source)


if __name__ == "__main__":
    unittest.main()
