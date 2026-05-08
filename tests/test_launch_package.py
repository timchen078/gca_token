import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAINNET_ADDRESS = "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6"


class LaunchPackageTests(unittest.TestCase):
    def test_logo_matches_basescan_size_target(self):
        logo = (ROOT / "brand" / "gca-logo.svg").read_text()
        self.assertIn('width="32"', logo)
        self.assertIn('height="32"', logo)
        self.assertIn("GCA token logo", logo)

    def test_public_site_uses_mainnet_identity(self):
        site = (ROOT / "site" / "index.html").read_text()
        self.assertIn("Base Mainnet", site)
        self.assertIn("chainId 8453", site)
        self.assertIn(MAINNET_ADDRESS, site)
        self.assertIn("https://basescan.org/address/", site)
        self.assertNotIn("sepolia.basescan.org", site)

    def test_public_materials_avoid_investment_promises(self):
        paths = [
            ROOT / "site" / "index.html",
            ROOT / "docs" / "whitepaper.md",
            ROOT / "docs" / "mainnet_public_profile.md",
            ROOT / "launch" / "basescan_token_submission.md",
            ROOT / "launch" / "liquidity_pool_runbook.md",
            ROOT / "launch" / "launch_status.md",
        ]
        forbidden = re.compile(r"\b(guaranteed returns?|profit sharing|risk[- ]?free|稳赚|保本)\b", re.I)
        for path in paths:
            with self.subTest(path=path.name):
                self.assertIsNone(forbidden.search(path.read_text()))

    def test_basescan_submission_has_required_public_placeholders(self):
        submission = (ROOT / "launch" / "basescan_token_submission.md").read_text()
        self.assertIn("Official website URL", submission)
        self.assertIn("Official domain email address", submission)
        self.assertIn("Public logo download URL", submission)
        self.assertIn("https://basescan.org/tokenupdate/", submission)
        self.assertIn(MAINNET_ADDRESS, submission)

    def test_liquidity_runbook_is_prepared_but_not_executed(self):
        runbook = (ROOT / "launch" / "liquidity_pool_runbook.md").read_text()
        self.assertIn("Prepared. Not executed.", runbook)
        self.assertIn("Blocked on the owner's chosen pair asset", runbook)
        self.assertIn(MAINNET_ADDRESS, runbook)

    def test_launch_status_separates_done_from_external_blockers(self):
        status = (ROOT / "launch" / "launch_status.md").read_text()
        self.assertIn("## Done", status)
        self.assertIn("## Needs Owner Input Or External Service", status)
        self.assertIn("Base Mainnet / chainId 8453", status)
        self.assertIn("Base Sepolia / chainId 84532", status)


if __name__ == "__main__":
    unittest.main()
