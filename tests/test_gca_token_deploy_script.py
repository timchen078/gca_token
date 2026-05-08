import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "token" / "scripts" / "deploy_base_sepolia.py"
ENV_EXAMPLE = ROOT / ".env.example"


class GCATokenDeployScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text()
        cls.env_example = ENV_EXAMPLE.read_text()

    def test_deploy_script_is_testnet_locked(self):
        self.assertIn("BASE_SEPOLIA_CHAIN_ID = 84532", self.source)
        self.assertIn("Refusing to deploy to chain", self.source)
        self.assertIn("CONFIRM_TESTNET_DEPLOY", self.source)
        self.assertIn("I_UNDERSTAND_THIS_IS_TESTNET", self.source)

    def test_deploy_script_reads_secret_only_from_environment(self):
        self.assertIn('required_env("DEPLOYER_PRIVATE_KEY")', self.source)
        self.assertNotRegex(
            self.source,
            re.compile(r"0x[a-fA-F0-9]{64}"),
        )
        self.assertNotRegex(self.source, re.compile(r"print\([^\n]*private_key"))
        self.assertNotRegex(self.source, re.compile(r"f[\"'][^\"']*\{private_key\}"))

    def test_env_example_uses_placeholder_key(self):
        self.assertIn("BASE_SEPOLIA_RPC_URL=https://sepolia.base.org", self.env_example)
        self.assertIn("DEPLOYER_PRIVATE_KEY=", self.env_example)
        self.assertIn("CONFIRM_TESTNET_DEPLOY=I_UNDERSTAND_THIS_IS_TESTNET", self.env_example)


if __name__ == "__main__":
    unittest.main()
