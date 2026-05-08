import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "token" / "contracts" / "GCAToken.sol"
STANDARD_JSON_INPUT = ROOT / "verification" / "GCAToken.standard-json-input.json"


class VerificationInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verification_input = json.loads(STANDARD_JSON_INPUT.read_text())

    def test_standard_json_embeds_public_source(self):
        self.assertEqual(self.verification_input["language"], "Solidity")
        self.assertEqual(
            self.verification_input["sources"]["token/contracts/GCAToken.sol"]["content"],
            SOURCE.read_text(),
        )

    def test_standard_json_uses_deployed_compiler_settings(self):
        settings = self.verification_input["settings"]
        self.assertEqual(settings["optimizer"], {"enabled": True, "runs": 200})
        self.assertIn("evm.bytecode.object", settings["outputSelection"]["*"]["*"])
        self.assertIn("evm.deployedBytecode.object", settings["outputSelection"]["*"]["*"])


if __name__ == "__main__":
    unittest.main()
