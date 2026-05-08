import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEPOLIA_RECORD = ROOT / "deployments" / "base-sepolia-gca.json"
MAINNET_RECORD = ROOT / "deployments" / "base-mainnet-gca.json"
STANDARD_JSON_INPUT = ROOT / "verification" / "GCAToken.standard-json-input.json"
ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
TX_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")


class DeploymentRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = {
            "sepolia": json.loads(SEPOLIA_RECORD.read_text()),
            "mainnet": json.loads(MAINNET_RECORD.read_text()),
        }

    def test_record_is_base_sepolia_gca(self):
        record = self.records["sepolia"]
        self.assertEqual(record["network"], "Base Sepolia")
        self.assertEqual(record["chainId"], 84532)
        self.assertEqual(record["name"], "GCA")
        self.assertEqual(record["symbol"], "GCA")
        self.assertEqual(record["decimals"], 18)
        self.assertEqual(record["totalSupply"], "1000000000")

    def test_record_is_base_mainnet_gca(self):
        record = self.records["mainnet"]
        self.assertEqual(record["network"], "Base Mainnet")
        self.assertEqual(record["chainId"], 8453)
        self.assertEqual(record["name"], "GCA")
        self.assertEqual(record["symbol"], "GCA")
        self.assertEqual(record["decimals"], 18)
        self.assertEqual(record["totalSupply"], "1000000000")

    def test_record_has_valid_identifiers(self):
        for record in self.records.values():
            with self.subTest(network=record["network"]):
                self.assertRegex(record["contractAddress"], ADDRESS_RE)
                self.assertRegex(record["deployer"], ADDRESS_RE)
                self.assertRegex(record["transactionHash"], TX_RE)
                self.assertIn(record["contractAddress"], record["explorer"]["contract"])
                self.assertIn(record["transactionHash"], record["explorer"]["transaction"])

    def test_records_use_distinct_explorers(self):
        self.assertIn("sepolia.basescan.org", self.records["sepolia"]["explorer"]["contract"])
        self.assertIn("basescan.org", self.records["mainnet"]["explorer"]["contract"])
        self.assertNotIn("sepolia.basescan.org", self.records["mainnet"]["explorer"]["contract"])

    def test_record_tracks_source_verification(self):
        for record in self.records.values():
            with self.subTest(network=record["network"]):
                verification = record["sourceVerification"]
                self.assertEqual(verification["status"], "verified")
                self.assertEqual(verification["compilerType"], "Solidity (Standard-Json-Input)")
                self.assertEqual(verification["compilerVersion"], "v0.8.24+commit.e11b9ed9")
                self.assertTrue(verification["optimizerEnabled"])
                self.assertEqual(verification["optimizerRuns"], 200)
                self.assertEqual(verification["license"], "MIT")
                self.assertEqual(verification["standardJsonInput"], "verification/GCAToken.standard-json-input.json")
        self.assertTrue(STANDARD_JSON_INPUT.exists())


if __name__ == "__main__":
    unittest.main()
