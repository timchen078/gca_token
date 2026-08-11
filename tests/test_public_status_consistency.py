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
MEMBER_PAGE_LAST_UPDATED = "2026-08-11"


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
        credits = self.load_json("site/credits.json")
        utility = self.load_json("site/utility.json")
        narrative = self.load_json("site/narrative.json")
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

        service_catalog = {item["id"]: item for item in credits["serviceCatalog"]}
        for service_id in (
            "liquidation-replay-report",
            "risk-warning-review",
            "backtest-lab-run",
            "entry-ready-review",
            "position-size-calculator",
            "portfolio-risk-map",
            "risk-control-training",
        ):
            self.assertEqual(service_catalog[service_id]["status"], "live-manual-review-service-unit")
            self.assertEqual(service_catalog[service_id]["unitType"], "reviewed service credit unit")
        self.assertEqual(
            service_catalog["member-research-notes"]["status"],
            "live-member-manual-review-service-unit",
        )
        self.assertEqual(
            service_catalog["member-research-notes"]["unitType"],
            "reviewed member service credit unit",
        )
        self.assertEqual(
            service_catalog["support-review-queue"]["status"],
            "live-member-priority-review-workflow",
        )

        self.assertEqual(
            utility["positioning"]["publicStatus"],
            "account-ledger-and-reviewed-services-live-connected-market-data-and-trading-staged",
        )
        utility_flow = {item["step"]: item for item in utility["accessFlow"]}
        self.assertEqual(utility_flow["product_access"]["status"], "live-manual-review-service-access")
        self.assertEqual(utility["ledgerContracts"]["serviceRequestEndpoint"], SERVICE_REQUEST_ENDPOINT)
        self.assertEqual(
            utility["ledgerContracts"]["serviceRequestFollowupEndpoint"],
            "/gca/account-service-requests/follow-ups",
        )

        narrative_workflows = {item["id"]: item for item in narrative["liveWorkflows"]}
        self.assertEqual(
            narrative_workflows["account-service-requests"]["status"],
            "live-manual-review-and-delivery",
        )
        self.assertIn(
            "at most once per request",
            narrative_workflows["account-service-requests"]["claimBoundary"],
        )

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
            "site/credits.html",
            "site/credits.json",
            "site/utility.html",
            "site/utility.json",
            "site/narrative.html",
            "site/narrative.json",
            "site/listing-kit.html",
            "site/team.html",
            "site/tim-chen.html",
            "site/tim-chen.json",
            "site/whitepaper.html",
            "docs/whitepaper.md",
            "docs/mainnet_public_profile.md",
            "launch/basescan_token_submission.md",
            "launch/data_platform_package.md",
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
            "staged access to non-custodial quant risk tools",
            "ledger-eligible-service-unit-staged",
            "member-ledger-eligible-service-unit-staged",
            "member-ledger-eligible-service-workflow-staged",
            "Draft Service Units",
            "service tier planned",
            "Draft credits catalog",
            "It is not a live public submission queue",
        )

        for path in paths:
            text = (ROOT / path).read_text()
            for marker in stale_markers:
                self.assertNotIn(marker, text, f"{path} contains stale marker: {marker}")

    def test_member_pages_match_live_account_and_manual_review_status(self):
        members = (SITE / "members.html").read_text()
        zh_members = (SITE / "zh-members.html").read_text()

        for marker in (
            "GCA Members | Live Account Access",
            "Live account intake",
            "One controlled account per email and verified wallet",
            "The current holder benefit",
            "The current GCA Member review",
            "/gca/member-reviews",
        ):
            self.assertIn(marker, members)
        for marker in (
            "GCA Members | Pre-Registration",
            "Planned holder programs",
            "The planned holder bonus",
            "The planned GCA Member tier",
            "When a reviewed HTTPS endpoint is connected",
            "After controlled HTTPS intake is live",
            "<strong>Planned</strong>",
        ):
            self.assertNotIn(marker, members)

        for marker in ("当前规则", "受控流程", "会员账户入口"):
            self.assertIn(marker, zh_members)
        for marker in (
            "未来 100 GCA AI Quant Access credits",
            "计划规则",
            "未来流程",
            "会员预登记",
        ):
            self.assertNotIn(marker, zh_members)

    def test_weekly_radar_current_pointer_matches_issue_006_archive(self):
        radar = self.load_json("site/radar.json")
        archive = self.load_json("site/radar-issue-006.json")
        narrative = self.load_json("site/narrative.json")
        project = self.load_json("site/project.json")
        tokenlist = self.load_json("site/tokenlist.json")
        current_page = (SITE / "radar.html").read_text()

        self.assertEqual(radar["status"], "weekly-go-china-radar-issue-006-published")
        self.assertEqual(radar["issue"], "issue-006")
        self.assertEqual(radar["issueDate"], "2026-08-11")
        self.assertEqual(radar["archivePageUrl"], archive["pageUrl"])
        self.assertEqual(radar["archiveUrl"], archive["schema"])
        self.assertEqual(archive["status"], radar["status"])
        self.assertEqual(archive["issue"], radar["issue"])
        self.assertEqual(archive["issueDate"], radar["issueDate"])
        self.assertEqual(narrative["weeklyRadar"]["status"], radar["status"])
        self.assertEqual(narrative["weeklyRadar"]["issue"], radar["issue"])
        self.assertEqual(project["weeklyGoChinaRadar"]["status"], radar["status"])
        self.assertEqual(project["weeklyGoChinaRadar"]["issue"], radar["issue"])
        self.assertEqual(
            tokenlist["tokens"][0]["extensions"]["weeklyRadarStatus"],
            radar["status"],
        )

        for stale_marker in (
            "Issue 003 / 2026-05-16",
            "member pre-registration and read-only balance preview as preparation only",
            "Member utility readiness",
        ):
            self.assertNotIn(stale_marker, current_page)
            self.assertNotIn(stale_marker, json.dumps(radar))

        self.assertTrue(radar["copyReadyPost"]["requiresOperatorReview"])
        self.assertIn("automatic token claim", radar["publicClaimBoundaries"]["doNotClaim"])
        self.assertEqual(radar["officialMarket"]["snapshotStatus"], "live-browser-read-only")

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
            "credits.json",
            "utility.json",
            "narrative.json",
            "tim-chen.json",
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
            "credits.html",
            "credits.json",
            "listing-kit.html",
            "narrative.html",
            "narrative.json",
            "team.html",
            "tim-chen.html",
            "tim-chen.json",
            "utility.html",
            "utility.json",
            "whitepaper.html",
            "support.html",
            "support.json",
            "terms.html",
            "terms.json",
        )
        for path in updated_paths:
            url = f"https://gcagochina.com/{path}"
            self.assertEqual(sitemap.get(url), LAST_UPDATED, url)

        for path in ("members.html", "zh-members.html"):
            url = f"https://gcagochina.com/{path}"
            self.assertEqual(sitemap.get(url), MEMBER_PAGE_LAST_UPDATED, url)


if __name__ == "__main__":
    unittest.main()
