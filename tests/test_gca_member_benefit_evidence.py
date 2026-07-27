import json
import shutil
import sqlite3
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER_DIR = ROOT / "cloudflare" / "gca-registration-worker"
WORKER_SOURCE = WORKER_DIR / "src" / "worker.mjs"
EVIDENCE_MODULE = WORKER_DIR / "src" / "member-benefit-evidence.mjs"
MIGRATIONS = [
    WORKER_DIR / "migrations" / "0003_member_access_ledgers.sql",
    WORKER_DIR / "migrations" / "0006_member_reviews.sql",
    WORKER_DIR / "migrations" / "0007_holding_history_verifications.sql",
    WORKER_DIR / "migrations" / "0008_member_benefit_transfer_evidence.sql",
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


class GcaMemberBenefitEvidenceTests(unittest.TestCase):
    def test_migration_adds_unique_transfer_evidence_and_member_links(self):
        database = sqlite3.connect(":memory:")
        try:
            for migration in MIGRATIONS:
                database.executescript(migration.read_text(encoding="utf-8"))

            transfer_columns = {
                row[1]
                for row in database.execute(
                    "PRAGMA table_info(gca_member_benefit_transfers)"
                ).fetchall()
            }
            member_columns = {
                row[1]
                for row in database.execute("PRAGMA table_info(gca_member_ledger)").fetchall()
            }
            transfer_indexes = {
                row[1]: bool(row[2])
                for row in database.execute(
                    "PRAGMA index_list(gca_member_benefit_transfers)"
                ).fetchall()
            }

            self.assertIn("transaction_hash", transfer_columns)
            self.assertIn("safe_snapshot_block_number", transfer_columns)
            self.assertIn("amount_raw", transfer_columns)
            self.assertIn("verification_status", transfer_columns)
            self.assertIn("automatic_token_transfer", transfer_columns)
            self.assertIn("member_benefit_transfer_record_id", member_columns)
            self.assertIn("member_benefit_transfer_verified_at", member_columns)
            self.assertIn("member_benefit_transfer_verification_status", member_columns)
            self.assertTrue(any(transfer_indexes.values()))
        finally:
            database.close()

    def test_receipt_verifier_requires_exact_safe_reserve_transfer(self):
        node = shutil.which("node") or (str(BUNDLED_NODE) if BUNDLED_NODE.exists() else "")
        if not node:
            self.skipTest("Node.js is not available")
        script = r"""
import { pathToFileURL } from "node:url";
const evidence = await import(pathToFileURL(process.argv[1]).href);
const contract = "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6";
const source = "0x5e8f84748612b913aacc937492ac25dc5630e246";
const recipient = "0x1111111111111111111111111111111111111111";
const other = "0x2222222222222222222222222222222222222222";
const txHash = `0x${"a".repeat(64)}`;
const blockHash = `0x${"b".repeat(64)}`;
const topic = (address) => `0x${address.slice(2).padStart(64, "0")}`;
const amount = 10000n * 10n ** 18n;
const makeLog = (overrides = {}) => ({
  address: contract,
  topics: [
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
    topic(source),
    topic(recipient)
  ],
  data: `0x${amount.toString(16)}`,
  blockNumber: "0x64",
  logIndex: "0x2",
  transactionHash: txHash,
  ...overrides
});
const makeReceipt = (overrides = {}) => ({
  transactionHash: txHash,
  status: "0x1",
  blockNumber: "0x64",
  blockHash,
  from: source,
  to: contract,
  logs: [makeLog()],
  ...overrides
});
const verify = (receipt, safeBlockNumber = 110) => evidence.verifyMemberBenefitTransferReceipt({
  receipt,
  transactionHash: txHash,
  expectedContractAddress: contract,
  expectedSourceWallet: source,
  expectedRecipientWallet: recipient,
  expectedAmountUnits: amount.toString(),
  safeBlockNumber
});
const valid = verify(makeReceipt());
const wrongAmount = verify(makeReceipt({
  logs: [makeLog({data: `0x${(amount - 1n).toString(16)}`})]
}));
const wrongSource = verify(makeReceipt({from: other}));
const unsafe = verify(makeReceipt(), 99);
const failed = verify(makeReceipt({status: "0x0"}));
const duplicate = verify(makeReceipt({logs: [makeLog(), makeLog({logIndex: "0x3"})]}));
console.log(JSON.stringify({valid, wrongAmount, wrongSource, unsafe, failed, duplicate}));
"""
        completed = subprocess.run(
            [node, "--input-type=module", "-e", script, str(EVIDENCE_MODULE)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)

        self.assertTrue(result["valid"]["matchedTransfer"])
        self.assertEqual(result["valid"]["status"], "verified")
        self.assertEqual(result["valid"]["transferLogIndex"], 2)
        self.assertFalse(result["wrongAmount"]["matchedTransfer"])
        self.assertEqual(result["wrongAmount"]["status"], "transfer_log_mismatch")
        self.assertEqual(result["wrongSource"]["status"], "source_wallet_mismatch")
        self.assertEqual(result["unsafe"]["status"], "awaiting_safe_confirmation")
        self.assertEqual(result["failed"]["status"], "transaction_failed")
        self.assertEqual(result["duplicate"]["status"], "ambiguous_transfer_logs")

    def test_worker_records_evidence_without_wallet_actions(self):
        source = WORKER_SOURCE.read_text(encoding="utf-8")

        self.assertIn(
            'const MEMBER_BENEFIT_TRANSFER_VERSION = "gca_member_benefit_transfer_v1";',
            source,
        )
        self.assertIn(
            'const MEMBER_BENEFIT_SOURCE_WALLET = "0x5e8f84748612b913aacc937492ac25dc5630e246";',
            source,
        )
        self.assertIn("verifyMemberBenefitTransferReceipt", source)
        self.assertIn('baseRpcRequest("eth_getTransactionReceipt"', source)
        self.assertIn("safeBlockConfirmationRequired: true", source)
        self.assertIn("exactTransferAmountRequired: MEMBER_BENEFIT_AMOUNT", source)
        self.assertIn("gca_member_benefit_transfers", source)
        self.assertIn('url.pathname === "/gca/member-benefit-transfers"', source)
        self.assertIn("verifiesExistingTransactionOnly: true", source)
        self.assertIn("automaticTokenTransfer: false", source)
        self.assertIn("writesWallet: false", source)
        self.assertIn("authorizesAdditionalTransfer: false", source)
        self.assertNotIn("eth_sendTransaction", source)
        self.assertNotIn("personal_sign", source)


if __name__ == "__main__":
    unittest.main()
