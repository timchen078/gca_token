import re
import unittest
from pathlib import Path


CONTRACT = Path(__file__).resolve().parents[1] / "token" / "contracts" / "GCAToken.sol"


class GCATokenContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = CONTRACT.read_text()
        cls.code = re.sub(r"//.*", "", cls.source)

    def test_token_identity_and_supply_are_fixed(self):
        self.assertIn('string public constant name = "GCA";', self.source)
        self.assertIn('string public constant symbol = "GCA";', self.source)
        self.assertIn("uint8 public constant decimals = 18;", self.source)
        self.assertIn("1_000_000_000 * 10 ** uint256(decimals)", self.source)

    def test_constructor_assigns_entire_supply_to_deployer(self):
        self.assertRegex(
            self.source,
            r"constructor\(\)\s*\{\s*_balances\[msg\.sender\]\s*=\s*totalSupply;",
        )
        self.assertIn("emit Transfer(address(0), msg.sender, totalSupply);", self.source)

    def test_no_post_deploy_supply_mutation_or_admin_hooks(self):
        forbidden_patterns = [
            r"\bfunction\s+mint\b",
            r"\bfunction\s+burn\b",
            r"\baddress\s+public\s+owner\b",
            r"\baddress\s+private\s+owner\b",
            r"\baddress\s+internal\s+owner\b",
            r"\bonlyOwner\b",
            r"\bOwnable\b",
            r"\bAccessControl\b",
            r"\bpause\b",
            r"\bblacklist\b",
            r"\btax\b",
            r"\bfee\b",
            r"\bwithdraw\b",
        ]
        for pattern in forbidden_patterns:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.code, flags=re.IGNORECASE))

    def test_standard_erc20_surface_exists(self):
        for signature in [
            "function balanceOf(address account) external view returns (uint256)",
            "function allowance(address owner, address spender) external view returns (uint256)",
            "function transfer(address to, uint256 value) external returns (bool)",
            "function approve(address spender, uint256 value) external returns (bool)",
            "function transferFrom(address from, address to, uint256 value) external returns (bool)",
        ]:
            with self.subTest(signature=signature):
                self.assertIn(signature, self.source)


if __name__ == "__main__":
    unittest.main()
