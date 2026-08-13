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
CORE_PAGE_LAST_UPDATED = "2026-08-12"
MEMBER_PAGE_LAST_UPDATED = "2026-08-11"
CONTENT_CYCLE_LAST_UPDATED = "2026-08-11"


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
            "GCA Membership | Access, Credits and Eligibility",
            "One verified account. Clear member access.",
            "Live account intake",
            "One controlled account per email and verified wallet",
            "100 Credit Rules",
            "Member Rules",
            "gca/member-access/",
        ):
            self.assertIn(marker, members)
        for marker in (
            "GCA Members | Pre-Registration",
            "GCA Members | Live Account Access",
            "Planned holder programs",
            "The planned holder bonus",
            "The planned GCA Member tier",
            "When a reviewed HTTPS endpoint is connected",
            "After controlled HTTPS intake is live",
            "<strong>Planned</strong>",
            "Legacy Packet Builder",
            "tools/gca_member_backend.py",
            "eth_requestAccounts",
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
            "product.json",
            "roadmap.json",
            "credits.json",
            "utility.json",
            "narrative.json",
        )
        for path in json_paths:
            payload = json.loads((SITE / path).read_text())
            self.assertEqual(payload["lastUpdated"], LAST_UPDATED, path)

        self.assertEqual(
            self.load_json("site/project.json")["lastUpdated"],
            CONTENT_CYCLE_LAST_UPDATED,
        )

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
            "privacy.html",
            "whitepaper.html",
            "terms.html",
        )
        for path in updated_paths:
            url = f"https://gcagochina.com/{path}"
            self.assertEqual(sitemap.get(url), LAST_UPDATED, url)

        for path in ("product.html", "support.html", "team.html"):
            url = f"https://gcagochina.com/{path}"
            self.assertEqual(sitemap.get(url), CORE_PAGE_LAST_UPDATED, url)

        self.assertEqual(
            sitemap.get("https://gcagochina.com/members.html"),
            CORE_PAGE_LAST_UPDATED,
        )

        for path in (
            "access.html",
            "project.json",
            "zh-members.html",
            "roadmap.html",
            "credits.html",
        ):
            self.assertNotIn(f"https://gcagochina.com/{path}", sitemap)

    def test_product_operations_content_cycle_is_current_and_aligned(self):
        campaign = self.load_json("site/campaign.json")
        library = self.load_json("site/content-library.json")
        desk = self.load_json("site/publishing-desk.json")
        announcements = self.load_json("site/announcements.json")
        community = self.load_json("site/community.json")
        project = self.load_json("site/project.json")

        self.assertEqual(campaign["campaignCycleId"], "product-operations-002")
        self.assertEqual(library["campaignCycleId"], campaign["campaignCycleId"])
        self.assertEqual(desk["campaignCycleId"], campaign["campaignCycleId"])
        self.assertEqual(announcements["campaignCycleId"], campaign["campaignCycleId"])
        self.assertEqual(community["campaignCycleId"], campaign["campaignCycleId"])
        self.assertEqual(project["contentCampaign"]["campaignCycleId"], campaign["campaignCycleId"])

        self.assertEqual(campaign["campaignWindow"]["startDate"], "2026-08-11")
        self.assertEqual(campaign["campaignWindow"]["endDate"], "2026-09-07")
        self.assertEqual(len(campaign["contentQueue"]), 10)
        self.assertEqual(len(library["drafts"]), 10)
        self.assertEqual(len(library["archivedDrafts"]), 10)
        self.assertEqual(library["previousCampaignWindow"]["status"], "archived-in-this-file")
        self.assertEqual(desk["nextPublishAction"]["sourceDraftId"], library["drafts"][0]["id"])
        self.assertEqual(desk["nextPublishAction"]["targetDate"], "2026-08-11")
        self.assertTrue(desk["nextPublishAction"]["requiresManualPosting"])

        current_pages = (
            "campaign.html",
            "content-library.html",
            "publishing-desk.html",
            "announcements.html",
            "community.html",
        )
        stale_markers = (
            "2026-05-20 to 2026-06-16",
            "Product Utility Intro",
            "Planned modules:",
            "计划中的 GCA Member",
        )
        for path in current_pages:
            text = (SITE / path).read_text()
            for marker in stale_markers:
                self.assertNotIn(marker, text, f"{path} contains stale campaign marker: {marker}")

if __name__ == "__main__":
    unittest.main()
