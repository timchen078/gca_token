import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tools.build_basescan_submission_package import build_submission_package, main, render_markdown


READY_VALUES = {
    "packageStatus": "ready-for-resubmission",
    "nextSubmissionReady": True,
    "network": "Base Mainnet",
    "chainId": 8453,
    "contractAddress": "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6",
    "tokenName": "GCA",
    "tokenSymbol": "GCA",
    "decimals": 18,
    "totalSupply": "1000000000",
    "website": "https://gcagochina.com/",
    "verifyUrl": "https://gcagochina.com/verify.html",
    "statusPageUrl": "https://gcagochina.com/status.html",
    "teamPageUrl": "https://gcagochina.com/team.html",
    "timChenProfessionalProfileUrl": "https://gcagochina.com/tim-chen.html",
    "domainEmailSetupPlanUrl": "https://gcagochina.com/domain-email.html",
    "domainEmailSetupPlanDataUrl": "https://gcagochina.com/domain-email.json",
    "baseScanRemediationPageUrl": "https://gcagochina.com/basescan-remediation.html",
    "baseScanRemediationUrl": "https://gcagochina.com/basescan-remediation.json",
    "githubRepoUrl": "https://github.com/timchen078/gca_token",
    "listingKitUrl": "https://gcagochina.com/listing-kit.html",
    "brandKitPageUrl": "https://gcagochina.com/brand-kit.html",
    "brandKitUrl": "https://gcagochina.com/brand-kit.json",
    "communityPageUrl": "https://gcagochina.com/community.html",
    "communityUrl": "https://gcagochina.com/community.json",
    "externalReviewStatusPageUrl": "https://gcagochina.com/external-reviews.html",
    "externalReviewStatusUrl": "https://gcagochina.com/external-reviews.json",
    "projectJsonUrl": "https://gcagochina.com/project.json",
    "tokenListUrl": "https://gcagochina.com/tokenlist.json",
    "wellKnownTokenIdentityUrl": "https://gcagochina.com/.well-known/gca-token.json",
    "whitepaperUrl": "https://gcagochina.com/whitepaper.html",
    "logoSvgUrl": "https://gcagochina.com/assets/gca-logo.svg",
    "logoPngUrl": "https://gcagochina.com/assets/gca-logo.png",
    "officialEmail": "support@gcagochina.com",
    "officialTelegram": "https://t.me/gcagochinaofficial",
    "officialX": "https://x.com/GCAAIGoChina",
    "descriptionLong": "GCA is a fixed-supply ERC-20 token deployed on Base Mainnet.",
    "officialMarketPool": {
        "pair": "GCA/USDT",
        "dex": "Uniswap v4",
        "poolAddress": "0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0",
        "geckoTerminalUrl": "https://www.geckoterminal.com/base/pools/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0",
        "dexScreenerUrl": "https://dexscreener.com/base/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0",
    },
    "supplyDisclosure": {
        "targetPublicAllocation": "400000000",
        "ownerHeldReserve": "600000000",
        "ownerReserveWallet": "0x5e8F84748612B913aAcC937492AC25dc5630E246",
        "supplyDisclosureUrl": "https://gcagochina.com/supply.json",
    },
    "doNotClaim": ["BaseScan token profile approval before publication"],
}

READY_PREFLIGHT = {
    "generatedAt": "2026-05-26T00:00:00Z",
    "status": "ready-for-owner-resubmission",
    "readyForBaseScanResubmission": True,
    "missingOrBlockedRequirements": [],
}

BLOCKED_PREFLIGHT = {
    "generatedAt": "2026-05-26T00:00:00Z",
    "status": "blocked-before-basescan-resubmission",
    "readyForBaseScanResubmission": False,
    "missingOrBlockedRequirements": ["official-domain-email", "domain-email-evidence-packet"],
}

READY_EVIDENCE = {
    "readyForBaseScanResubmission": True,
    "targetDomainEmail": "support@gcagochina.com",
    "dnsReadiness": {"readyForBaseScanEmailEvidence": True},
    "websiteEmailUpdatedToTarget": True,
}


class BaseScanSubmissionPackageTests(unittest.TestCase):
    def test_package_blocks_when_preflight_is_not_ready(self):
        package = build_submission_package(
            values=READY_VALUES,
            readiness_report=BLOCKED_PREFLIGHT,
            generated_at="2026-05-26T00:00:00Z",
        )

        self.assertFalse(package["readyForOwnerSubmission"])
        self.assertEqual(package["status"], "blocked-before-basescan-submission")
        self.assertIn("official-domain-email", package["missingOrBlockedRequirements"])
        self.assertIn("DRAFT ONLY - DO NOT SUBMIT BASESCAN YET.", package["copyPasteBlocks"]["baseScanReviewerComment"])
        self.assertIn("domain-email-evidence-packet", package["copyPasteBlocks"]["baseScanReviewerComment"])
        self.assertFalse(package["boundaries"]["submitsBaseScanRequest"])
        self.assertFalse(package["boundaries"]["touchesWalletOrContract"])

    def test_ready_package_contains_copyable_basescan_fields(self):
        package = build_submission_package(
            values=READY_VALUES,
            readiness_report=READY_PREFLIGHT,
            generated_at="2026-05-26T00:00:00Z",
        )

        self.assertTrue(package["readyForOwnerSubmission"])
        self.assertEqual(package["formFields"]["basicInformation"]["projectEmailAddress"], "support@gcagochina.com")
        self.assertEqual(package["formFields"]["socialProfiles"]["timChenProfessionalProfile"], "https://gcagochina.com/tim-chen.html")
        self.assertEqual(package["formFields"]["priceData"]["officialMarketRoute"], "GCA/USDT")
        self.assertEqual(package["formFields"]["saleDetails"]["publicSale"], "Not applicable. No ICO/IEO or public token sale has been conducted.")
        self.assertIn("Please review the updated GCA token profile metadata", package["copyPasteBlocks"]["baseScanReviewerComment"])
        self.assertIn("support@gcagochina.com", package["copyPasteBlocks"]["baseScanReviewerComment"])
        self.assertIn("not claiming BaseScan token profile approval", package["copyPasteBlocks"]["baseScanReviewerComment"])
        self.assertIn("Tim Chen professional profile", package["copyPasteBlocks"]["evidenceLinksPlainText"])
        self.assertIn("GCA/USDT", package["copyPasteBlocks"]["marketAndSupplyPlainText"])

    def test_markdown_includes_submission_boundary(self):
        package = build_submission_package(
            values=READY_VALUES,
            readiness_report=READY_PREFLIGHT,
            generated_at="2026-05-26T00:00:00Z",
        )

        markdown = render_markdown(package)

        self.assertIn("GCA BaseScan Submission Package", markdown)
        self.assertIn("Ready for owner submission: `true`", markdown)
        self.assertIn("Copy/Paste Reviewer Comment", markdown)
        self.assertIn("Copy/Paste Basic Information", markdown)
        self.assertIn("Project Email Address: `support@gcagochina.com`", markdown)
        self.assertIn("This package does not submit a BaseScan request.", markdown)

    def test_cli_blocks_current_unready_values_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            values_path = temp_path / "values.json"
            evidence_path = temp_path / "evidence.json"
            values = {**READY_VALUES, "nextSubmissionReady": False, "officialEmail": "GCAgochina@outlook.com"}
            values_path.write_text(json.dumps(values), encoding="utf-8")
            evidence_path.write_text(json.dumps(READY_EVIDENCE), encoding="utf-8")

            output = StringIO()
            with redirect_stdout(output):
                exit_code = main([
                    "--values",
                    str(values_path),
                    "--evidence-packet",
                    str(evidence_path),
                    "--skip-url-checks",
                    "--json",
                    "--require-ready",
                ])

            self.assertEqual(exit_code, 1)
            payload = json.loads(output.getvalue())
            self.assertFalse(payload["readyForOwnerSubmission"])
            self.assertIn("Do not submit BaseScan yet", payload["nextAction"])
            self.assertIn("DRAFT ONLY - DO NOT SUBMIT BASESCAN YET.", payload["copyPasteBlocks"]["baseScanReviewerComment"])


if __name__ == "__main__":
    unittest.main()
