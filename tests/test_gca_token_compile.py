import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "token" / "scripts" / "build_gca_artifact.py"
CONFIG = ROOT / "token" / "config" / "gca_token.json"
ABI_ARTIFACT = ROOT / "token" / "build" / "GCAToken.abi.json"
DEPLOY_ARTIFACT = ROOT / "token" / "build" / "GCAToken.artifact.json"


def load_build_script():
    spec = importlib.util.spec_from_file_location("build_gca_artifact", BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GCATokenCompileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_build_script()
        cls.abi, cls.artifact = cls.builder.build_artifact()

    def test_contract_compiles_with_expected_public_surface(self):
        function_names = {
            item["name"] for item in self.abi if item.get("type") == "function"
        }

        self.assertGreater(len(self.artifact["bytecode"]), 2)
        self.assertEqual(self.artifact["constructorArgs"], [])
        self.assertEqual(self.artifact["compiler"]["version"], "0.8.24")
        self.assertTrue(
            {
                "name",
                "symbol",
                "decimals",
                "totalSupply",
                "balanceOf",
                "allowance",
                "transfer",
                "approve",
                "transferFrom",
            }.issubset(function_names)
        )

    def test_config_matches_fixed_supply_policy(self):
        config = json.loads(CONFIG.read_text())
        self.assertEqual(config["name"], "GCA")
        self.assertEqual(config["symbol"], "GCA")
        self.assertEqual(config["decimals"], 18)
        self.assertEqual(config["totalSupplyTokens"], "1000000000")
        self.assertEqual(config["totalSupplyBaseUnits"], "1000000000000000000000000000")
        self.assertFalse(config["mintingEnabled"])
        self.assertEqual(config["recommendedFirstNetwork"]["chainId"], 84532)

    def test_committed_artifacts_match_compiler_output(self):
        committed_abi = json.loads(ABI_ARTIFACT.read_text())
        committed_artifact = json.loads(DEPLOY_ARTIFACT.read_text())

        self.assertEqual(committed_abi, self.abi)
        self.assertEqual(committed_artifact["abi"], self.abi)
        self.assertEqual(
            committed_artifact["bytecodeSha256"],
            self.artifact["bytecodeSha256"],
        )
        self.assertEqual(committed_artifact["token"], self.artifact["token"])


if __name__ == "__main__":
    unittest.main()
