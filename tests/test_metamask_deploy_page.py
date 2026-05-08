import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "tools" / "metamask_deploy.html"
MAINNET_PAGE = ROOT / "tools" / "metamask_deploy_base_mainnet.html"


class MetaMaskDeployPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = PAGE.read_text()

    def test_page_is_locked_to_base_sepolia(self):
        self.assertIn('BASE_SEPOLIA_CHAIN_ID = "0x14a34"', self.source)
        self.assertIn('chainName: "Base Sepolia"', self.source)
        self.assertIn('"https://sepolia.base.org"', self.source)
        self.assertIn('"https://sepolia.basescan.org"', self.source)

    def test_page_uses_metamask_without_private_keys(self):
        self.assertIn('method: "eth_requestAccounts"', self.source)
        self.assertIn('method: "eth_sendTransaction"', self.source)
        self.assertNotIn("privateKey", self.source)
        self.assertNotIn("mnemonic", self.source)
        self.assertNotIn("seed phrase", self.source)

    def test_page_deploys_compiled_artifact_bytecode(self):
        self.assertIn("../token/build/GCAToken.artifact.json", self.source)
        self.assertIn("data: artifact.bytecode", self.source)

    def test_page_waits_for_receipt_and_can_add_token(self):
        self.assertIn('method: "eth_getTransactionReceipt"', self.source)
        self.assertIn('method: "wallet_watchAsset"', self.source)
        self.assertIn("0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6", self.source)


class MetaMaskMainnetDeployPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MAINNET_PAGE.read_text()

    def test_page_is_locked_to_base_mainnet(self):
        self.assertIn('BASE_MAINNET_CHAIN_ID = "0x2105"', self.source)
        self.assertIn('chainName: "Base Mainnet"', self.source)
        self.assertIn('"https://mainnet.base.org"', self.source)
        self.assertIn('"https://basescan.org"', self.source)
        self.assertNotIn("BASE_SEPOLIA_CHAIN_ID", self.source)

    def test_page_requires_mainnet_confirmation_phrase(self):
        self.assertIn('CONFIRMATION_PHRASE = "DEPLOY GCA MAINNET"', self.source)
        self.assertIn("confirmationInput.value !== CONFIRMATION_PHRASE", self.source)
        self.assertIn("MAINNET transaction confirmation", self.source)

    def test_page_uses_metamask_without_private_keys(self):
        self.assertIn('method: "eth_requestAccounts"', self.source)
        self.assertIn('method: "eth_sendTransaction"', self.source)
        self.assertIn('method: "eth_estimateGas"', self.source)
        self.assertNotIn("privateKey", self.source)
        self.assertNotIn("mnemonic", self.source)
        self.assertNotIn("seed phrase", self.source)


if __name__ == "__main__":
    unittest.main()
