import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

PRODUCT_STAGE = (
    "account-ledger-browser-tools-and-reviewed-services-live-"
    "connected-market-data-and-trading-staged"
)
SUPPORT_STATUS = "live-structured-account-service-intake-and-manual-email-support"
SERVICE_REQUEST_ENDPOINT = "/gca/account-service-requests"
LAST_UPDATED = "2026-08-10"


class PublicStatusConsistencyTests(unittest.TestCase):
    def load_json(self, relative_path):
        return json.loads((ROOT / relative_path).read_text())

    def test_live_account_and_service_statuses_match(self):
        access = self.load_json("site/access.json")
        member_program = self.load_json("site/member-program.json")
        privacy = self.load_json("site/privacy.json")
        support = self.load_json("site/support.json")
        terms = self.load_json("site/terms.json")
        project = self.load_json("site/project.json")
        product = self.load_json("site/product.json")
        roadmap = self.load_json("site/roadmap.json")
        data_platform = self.load_json("launch/data_platform_form_values.json")

        self.assertEqual(
            access["currentState"]["currentStage"],
            "controlled-account-ui-device-status-and-reviewed-services-live",
        )
        self.assertTrue(access["currentState"]["accountServiceRequestProductionLive"])
        self.assertTrue(access["currentState"]["serviceRequestCreditsDeductedOnlyAfterDeliveredReview"])

        self.assertEqual(member_program["status"], "member-account-and-reviewed-service-workflow-live")
        self.assertTrue(member_program["verification"]["directSubmissionEndpointConfigured"])
        self.assertEqual(
            member_program["verification"]["liveAccountServiceRequestEndpoint"],
            SERVICE_REQUEST_ENDPOINT,
        )
        self.assertEqual(member_program["supportIntake"]["status"], SUPPORT_STATUS)

        self.assertTrue(privacy["currentStaticSiteBehavior"]["controlledAccountDirectSubmissionEndpointConfigured"])
        self.assertTrue(privacy["currentStaticSiteBehavior"]["accountServiceRequestDirectSubmissionEndpointConfigured"])
        self.assertEqual(
            privacy["controlledAccountIntake"]["serviceRequestEndpoint"],
            SERVICE_REQUEST_ENDPOINT,
        )
        self.assertFalse(privacy["securityBoundary"]["accountServiceHistoryReturnsFollowupResponseText"])

        self.assertTrue(support["currentSubmissionMode"]["controlledHttpsAccountUiLive"])
        self.assertEqual(
            support["currentSubmissionMode"]["accountServiceRequestEndpoint"],
            SERVICE_REQUEST_ENDPOINT,
        )
        self.assertEqual(support["supportWorkflow"]["publicIntakeStatus"], SUPPORT_STATUS)

        self.assertTrue(terms["participationBoundaries"]["controlledAccountUiLive"])
        self.assertTrue(terms["participationBoundaries"]["reviewedServiceRequestsLive"])
        self.assertEqual(terms["reviewedServiceTerms"]["status"], "live-manual-review-and-delivery")
        self.assertFalse(terms["programTerms"]["gcaMember"]["memberBenefitAutomatic"])

        self.assertEqual(project["productSpec"]["currentStage"], PRODUCT_STAGE)
        self.assertEqual(project["memberProgram"]["supportIntake"]["status"], SUPPORT_STATUS)
        self.assertEqual(product["positioning"]["currentStage"], PRODUCT_STAGE)
        self.assertEqual(roadmap["currentStage"], PRODUCT_STAGE)
        self.assertEqual(data_platform["productSpecPositioning"]["currentStage"], PRODUCT_STAGE)
        self.assertEqual(data_platform["utilityPositioning"]["supportIntake"]["status"], SUPPORT_STATUS)

    def test_stale_public_status_markers_do_not_return(self):
        paths = (
            "site/index.html",
            "site/access.html",
            "site/access.json",
            "site/member-program.html",
            "site/member-program.json",
            "site/privacy.html",
            "site/privacy.json",
            "site/support.html",
            "site/support.json",
            "site/terms.html",
            "site/terms.json",
            "site/liquidation-replay-001.html",
            "site/liquidation-replay-001.json",
            "site/market-quality.html",
            "site/market-quality.json",
            "site/project.json",
            "site/product.html",
            "site/product.json",
            "site/roadmap.html",
            "site/roadmap.json",
            "launch/data_platform_form_values.json",
        )
        stale_markers = (
            "rules-published-public-claim-not-connected",
            "backend-ledger-ready-public-claim-not-connected",
            "prepared-not-publicly-connected",
            "copy-download-email",
            "planned-after-ledger",
            "live-account-and-ledger-workflows-service-delivery-staged",
            "Cloudflare deploy permission",
            "Account and eligible ledger path live; reviewed service delivery staged",
            "Email API live / member packet local",
            "Not connected",
            "planned 100 credits",
            "planned GCA Member status",
            "staged non-custodial quant risk tools",
        )

        for path in paths:
            text = (ROOT / path).read_text()
            for marker in stale_markers:
                self.assertNotIn(marker, text, f"{path} contains stale marker: {marker}")

    def test_updated_public_documents_share_current_date_and_sitemap(self):
        json_paths = (
            "access.json",
            "member-program.json",
            "privacy.json",
            "support.json",
            "terms.json",
            "liquidation-replay-001.json",
            "market-quality.json",
            "project.json",
            "product.json",
            "roadmap.json",
        )
        for path in json_paths:
            payload = json.loads((SITE / path).read_text())
            self.assertEqual(payload["lastUpdated"], LAST_UPDATED, path)

        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        root = ET.fromstring((SITE / "sitemap.xml").read_text())
        sitemap = {
            item.findtext("sm:loc", namespaces=namespace): item.findtext(
                "sm:lastmod", namespaces=namespace
            )
            for item in root.findall("sm:url", namespace)
        }
        updated_paths = (
            "",
            "access.html",
            "access.json",
            "liquidation-replay-001.html",
            "liquidation-replay-001.json",
            "market-quality.html",
            "market-quality.json",
            "member-program.html",
            "member-program.json",
            "privacy.html",
            "privacy.json",
            "product.html",
            "product.json",
            "project.json",
            "roadmap.html",
            "roadmap.json",
            "support.html",
            "support.json",
            "terms.html",
            "terms.json",
        )
        for path in updated_paths:
            url = f"https://gcagochina.com/{path}"
            self.assertEqual(sitemap.get(url), LAST_UPDATED, url)


if __name__ == "__main__":
    unittest.main()
