import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAINNET_ADDRESS = "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6"
RESERVE_WALLET = "0x5e8F84748612B913aAcC937492AC25dc5630E246"
RESERVE_TX = "0x4c342e1f4c969d0a73018637b778d5a76bd05f54749ff1fd2d19327fd5c01c67"


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

    def test_public_site_sets_custom_domain(self):
        cname = (ROOT / "site" / "CNAME").read_text().strip()
        self.assertEqual(cname, "gcagochina.com")

    def test_public_site_discloses_current_operational_status(self):
        site = (ROOT / "site" / "index.html").read_text()
        self.assertIn("BaseScan token profile update has been submitted", site)
        self.assertIn("Go China Access", site)
        self.assertIn("concept phase", site)
        self.assertIn("concept-stage project", site)
        self.assertIn("700,000,000 GCA / 70%", site)
        self.assertIn("300,000,000 GCA / 30%", site)
        self.assertIn("exact circulating supply should still be verified", site)
        self.assertIn(RESERVE_WALLET, site)
        self.assertIn(RESERVE_TX, site)
        self.assertIn("mailto:cxy070800@gmail.com", site)
        self.assertIn("Project contact email", site)
        self.assertNotIn("https://x.com/GCAgochina", site)
        self.assertNotIn("Official X profile", site)
        self.assertIn("No third-party audit has been completed", site)
        self.assertIn("pool is shallow", site)
        self.assertIn("high price impact and slippage", site)
        self.assertIn("https://app.uniswap.org/positions/v3/base/5087977", site)

    def test_public_materials_avoid_investment_promises(self):
        paths = [
            ROOT / "site" / "index.html",
            ROOT / "docs" / "whitepaper.md",
            ROOT / "docs" / "mainnet_public_profile.md",
            ROOT / "launch" / "basescan_token_submission.md",
            ROOT / "launch" / "basescan_review_followup.md",
            ROOT / "launch" / "token_allocation_plan.md",
            ROOT / "launch" / "liquidity_pool_runbook.md",
            ROOT / "launch" / "launch_status.md",
        ]
        forbidden = re.compile(r"\b(guaranteed returns?|profit sharing|risk[- ]?free|稳赚|保本|拉盘|炒币)\b", re.I)
        for path in paths:
            with self.subTest(path=path.name):
                self.assertIsNone(forbidden.search(path.read_text()))

    def test_basescan_submission_has_required_public_placeholders(self):
        submission = (ROOT / "launch" / "basescan_token_submission.md").read_text()
        self.assertIn("https://gcagochina.com/", submission)
        self.assertIn("Official contact email", submission)
        self.assertIn("cxy070800@gmail.com", submission)
        self.assertIn("Gmail address", submission)
        self.assertIn("Submitted from the owner's browser session on 2026-05-09", submission)
        self.assertIn("deployer-wallet ownership verification were included", submission)
        self.assertIn("publicly listed on the official website", submission)
        self.assertIn("Public logo download URL", submission)
        self.assertNotIn("https://x.com/GCAgochina", submission)
        self.assertIn("https://basescan.org/tokenupdate/", submission)
        self.assertIn(MAINNET_ADDRESS, submission)

    def test_basescan_review_followup_is_actionable(self):
        followup = (ROOT / "launch" / "basescan_review_followup.md").read_text()
        self.assertIn("awaiting BaseScan review", followup)
        self.assertIn("cxy070800@gmail.com", followup)
        self.assertIn("Base Mainnet", followup)
        self.assertIn("Chain ID: 8453", followup)
        self.assertIn(MAINNET_ADDRESS, followup)
        self.assertIn("If BaseScan Approves", followup)
        self.assertIn("If BaseScan Requests Changes", followup)
        self.assertIn("Reply Template", followup)
        self.assertIn("Do not describe the BaseScan token profile as complete", followup)

    def test_basescan_form_values_are_copyable(self):
        values = json.loads((ROOT / "launch" / "basescan_form_values.json").read_text())
        self.assertEqual(values["network"], "Base Mainnet")
        self.assertEqual(values["contractAddress"], MAINNET_ADDRESS)
        self.assertEqual(values["website"], "https://gcagochina.com/")
        self.assertEqual(values["logoUrl"], "https://gcagochina.com/assets/gca-logo.svg")
        self.assertEqual(values["whitepaperUrl"], "https://gcagochina.com/whitepaper.html")
        self.assertEqual(values["officialEmail"], "cxy070800@gmail.com")
        self.assertIn("Gmail address", values["officialEmailNote"])
        self.assertEqual(values["targetPublicAllocation"], "700000000")
        self.assertEqual(values["targetPublicAllocationPercent"], 70)
        self.assertEqual(values["ownerHeldReserve"], "300000000")
        self.assertEqual(values["ownerHeldReservePercent"], 30)
        self.assertEqual(values["ownerReserveWallet"], RESERVE_WALLET)
        self.assertEqual(values["ownerReserveTransferTx"], RESERVE_TX)
        self.assertIn("normal owner-controlled wallet", values["ownerReserveCustodyNote"])
        self.assertIn("Go China Access", values["description"])
        self.assertIn("concept-stage community direction", values["description"])
        self.assertEqual(values["submissionStatus"], "submitted")
        self.assertEqual(values["reviewStatus"], "awaiting BaseScan review")
        self.assertEqual(values["socialLinks"], [])

    def test_token_allocation_plan_records_owner_reserve(self):
        plan = json.loads((ROOT / "launch" / "token_allocation_plan.json").read_text())
        doc = (ROOT / "launch" / "token_allocation_plan.md").read_text()
        self.assertEqual(plan["totalSupply"], "1000000000")
        self.assertEqual(plan["allocationPlanStatus"], "owner-reserve-transferred")
        self.assertEqual(plan["allocations"][0]["amount"], "700000000")
        self.assertEqual(plan["allocations"][0]["percent"], 70)
        self.assertEqual(plan["allocations"][1]["amount"], "300000000")
        self.assertEqual(plan["allocations"][1]["percent"], 30)
        self.assertEqual(plan["allocations"][1]["holder"], RESERVE_WALLET)
        self.assertEqual(plan["allocations"][1]["transferTransactionHash"], RESERVE_TX)
        self.assertEqual(plan["executedOwnerReserveTransfer"]["to"], RESERVE_WALLET)
        self.assertEqual(plan["executedOwnerReserveTransfer"]["transactionHash"], RESERVE_TX)
        self.assertIn("owner/founder", plan["allocations"][1]["notes"])
        self.assertIn("target allocation", doc)
        self.assertIn("300,000,000 GCA", doc)
        self.assertIn("not be described as circulating", doc)
        self.assertIn("not a lock, vesting contract, or Safe multisig", doc)
        self.assertIn(RESERVE_WALLET, doc)
        self.assertIn(RESERVE_TX, doc)
        self.assertIn(MAINNET_ADDRESS, doc)

    def test_public_materials_do_not_overstate_basescan_review(self):
        paths = [
            ROOT / "site" / "index.html",
            ROOT / "site" / "whitepaper.html",
            ROOT / "docs" / "whitepaper.md",
            ROOT / "docs" / "mainnet_public_profile.md",
            ROOT / "launch" / "launch_status.md",
        ]
        forbidden = [
            "BaseScan profile complete",
            "BaseScan approved",
            "BaseScan token profile is complete",
            "BaseScan token profile has been accepted",
            "BaseScan token profile is live",
        ]
        for path in paths:
            text = path.read_text()
            with self.subTest(path=path.name):
                for phrase in forbidden:
                    self.assertNotIn(phrase, text)

    def test_liquidity_runbook_records_execution(self):
        runbook = (ROOT / "launch" / "liquidity_pool_runbook.md").read_text()
        self.assertIn("Executed on Base Mainnet.", runbook)
        self.assertIn("5087977", runbook)
        self.assertIn("0xef94e020c8b431151b789ca3e96c45ab0c18d20d15bf8d7d543630f1370fc158", runbook)
        self.assertIn(MAINNET_ADDRESS, runbook)

    def test_liquidity_plan_has_selected_mainnet_defaults(self):
        plan = json.loads((ROOT / "launch" / "liquidity_plan.json").read_text())
        self.assertEqual(plan["status"], "executed")
        self.assertEqual(plan["network"], "Base Mainnet")
        self.assertEqual(plan["chainId"], 8453)
        self.assertEqual(plan["protocolVersion"], "v3")
        self.assertEqual(plan["feeTier"], "1%")
        self.assertEqual(plan["selectedPlan"]["gcaAmount"], "100000")
        self.assertEqual(plan["selectedPlan"]["ethAmount"], "0.001")
        self.assertEqual(plan["selectedPlan"]["impliedFullyDilutedValueEth"], "10")
        self.assertEqual(plan["pair"]["baseToken"]["address"], MAINNET_ADDRESS)
        self.assertEqual(plan["execution"]["positionTokenId"], "5087977")
        self.assertEqual(plan["execution"]["poolAddress"], "0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff")

    def test_liquidity_deployment_record_is_on_base_mainnet(self):
        record = json.loads((ROOT / "deployments" / "base-mainnet-gca-liquidity.json").read_text())
        self.assertEqual(record["status"], "executed")
        self.assertEqual(record["network"], "Base Mainnet")
        self.assertEqual(record["chainId"], 8453)
        self.assertEqual(record["tokenId"], "5087977")
        self.assertEqual(record["transactionHash"], "0xef94e020c8b431151b789ca3e96c45ab0c18d20d15bf8d7d543630f1370fc158")
        self.assertEqual(record["tokens"]["token0"]["address"], MAINNET_ADDRESS)
        self.assertEqual(record["tokens"]["token1"]["symbol"], "WETH")
        self.assertEqual(record["position"]["tickLower"], -887200)
        self.assertEqual(record["position"]["tickUpper"], 887200)

    def test_launch_status_separates_done_from_external_blockers(self):
        status = (ROOT / "launch" / "launch_status.md").read_text()
        self.assertIn("## Done", status)
        self.assertIn("## Needs Owner Input Or External Service", status)
        self.assertIn("https://gcagochina.com/", status)
        self.assertIn("DNS records for `gcagochina.com`", status)
        self.assertIn("GitHub Pages HTTPS certificate issued", status)
        self.assertNotIn("wait for GitHub Pages HTTPS to become active", status)
        self.assertIn("Base Mainnet / chainId 8453", status)
        self.assertIn("Base Sepolia / chainId 84532", status)
        self.assertIn(RESERVE_WALLET, status)
        self.assertIn(RESERVE_TX, status)

    def test_internal_security_review_is_not_third_party_audit(self):
        report = (ROOT / "audit" / "gca_internal_security_review.md").read_text()
        scope = (ROOT / "launch" / "audit_scope.md").read_text()
        self.assertIn("not a third-party audit", report)
        self.assertIn("No third-party audit has been completed", scope)
        self.assertIn("must not say", scope)
        self.assertIn("No mint function exists", report)
        self.assertIn("No owner or admin role exists", report)
        self.assertIn(MAINNET_ADDRESS, report)

    def test_site_has_whitepaper_page(self):
        index = (ROOT / "site" / "index.html").read_text()
        whitepaper = (ROOT / "site" / "whitepaper.html").read_text()
        self.assertIn('href="whitepaper.html"', index)
        self.assertIn("GCA Whitepaper", whitepaper)
        self.assertIn("Version 0.4", whitepaper)
        self.assertIn("Go China Access", index)
        self.assertIn("Go China Access", whitepaper)
        self.assertIn("concept-stage community direction", whitepaper)
        self.assertIn("deployer-wallet ownership verification are complete", whitepaper)
        self.assertIn("Owner-held reserve", whitepaper)
        self.assertIn("300,000,000 GCA", whitepaper)
        self.assertIn(RESERVE_WALLET, whitepaper)
        self.assertIn(RESERVE_TX, whitepaper)
        self.assertIn("not a lock, vesting contract, or Safe multisig", whitepaper)
        self.assertIn("mailto:cxy070800@gmail.com", whitepaper)
        self.assertIn("starter liquidity only", whitepaper)
        self.assertIn(MAINNET_ADDRESS, whitepaper)


if __name__ == "__main__":
    unittest.main()
