import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "deployments" / "base-sepolia-gca.json"
STANDARD_JSON_INPUT = ROOT / "verification" / "GCAToken.standard-json-input.json"
ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
TX_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")


class DeploymentRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())

    def test_record_is_base_sepolia_gca(self):
        self.assertEqual(self.record["network"], "Base Sepolia")
        self.assertEqual(self.record["chainId"], 84532)
        self.assertEqual(self.record["name"], "GCA")
        self.assertEqual(self.record["symbol"], "GCA")
        self.assertEqual(self.record["decimals"], 18)
        self.assertEqual(self.record["totalSupply"], "1000000000")

    def test_record_has_valid_identifiers(self):
        self.assertRegex(self.record["contractAddress"], ADDRESS_RE)
        self.assertRegex(self.record["deployer"], ADDRESS_RE)
        self.assertRegex(self.record["transactionHash"], TX_RE)
        self.assertIn(self.record["contractAddress"], self.record["explorer"]["contract"])
        self.assertIn(self.record["transactionHash"], self.record["explorer"]["transaction"])

    def test_record_tracks_source_verification(self):
        verification = self.record["sourceVerification"]
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
