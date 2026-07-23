import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READINESS_AT = "2026-07-20T10:34:06Z"
PUBLIC_ROUTE_AT = "2026-07-20T10:33:02Z"
BLOCKED_BY = (
    "Latest 2026-07-20 readiness check passed Worker dry-run but found Wrangler not logged in; "
    "Cloudflare account authentication, D1 visibility, remote migration, deploy permission, and "
    "post-deploy smoke checks remain blocked"
)
ROUTE_OBSERVATIONS = {
    "/gca/service-requests": 404,
    "/gca/credit-usage": 404,
}
READINESS_SUMMARY = {
    "wranglerDeployDryRun": "passed",
    "cloudflareD1Visibility": "not-verified-auth-required",
    "cloudflareAuthSession": "failed-not-logged-in",
    "cloudflareWorkerDeployPermission": "not-verified-auth-required",
    "code10000Seen": False,
    "writesD1Records": False,
    "deploysWorker": False,
}


def load_site_json(name: str) -> dict:
    return json.loads((ROOT / "site" / name).read_text(encoding="utf-8"))


class GcaWorkerStatusConsistencyTests(unittest.TestCase):
    def assert_readiness_summary(self, summary: dict) -> None:
        for key, expected in READINESS_SUMMARY.items():
            self.assertEqual(summary.get(key), expected, key)

    def test_machine_readable_worker_status_is_consistent(self):
        api_status = load_site_json("api-status.json")
        access_api = load_site_json("access-api.json")
        operations = load_site_json("operations.json")
        credits = load_site_json("credits.json")
        playbook = load_site_json("service-delivery-playbook.json")
        handoff = load_site_json("worker-routes-handoff.json")

        for payload in (api_status, access_api, operations, credits, playbook, handoff):
            self.assertEqual(payload["lastUpdated"], "2026-07-20")

        self.assertEqual(api_status["latestDeployReadinessCheckAt"], READINESS_AT)
        self.assert_readiness_summary(api_status["latestDeployReadinessSummary"])
        self.assertEqual(api_status["pendingRoutesDeployHandoff"]["blockedBy"], BLOCKED_BY)

        access_backend = access_api["productionEmailRegistrationBackend"]
        self.assertEqual(access_backend["latestDeployReadinessCheckAt"], READINESS_AT)
        self.assert_readiness_summary(access_backend["latestDeployReadinessSummary"])
        self.assertEqual(access_backend["pendingRoutesLastObservedAt"], PUBLIC_ROUTE_AT)
        self.assertEqual(access_backend["pendingRouteAnonymousGetStatus"], ROUTE_OBSERVATIONS)

        operations_pipeline = operations["memberAccessOpsPipeline"]
        self.assertEqual(operations_pipeline["latestDeployReadinessCheckAt"], READINESS_AT)
        self.assert_readiness_summary(operations_pipeline["latestDeployReadinessSummary"])
        self.assertEqual(operations_pipeline["pendingRoutesLastObservedAt"], PUBLIC_ROUTE_AT)
        self.assertEqual(operations_pipeline["pendingRouteAnonymousGetStatus"], ROUTE_OBSERVATIONS)

        for ledger_key in ("usageLedger", "serviceRequestQueue"):
            ledger = credits[ledger_key]
            self.assertEqual(ledger["latestDeployReadinessCheckAt"], READINESS_AT)
            self.assert_readiness_summary(ledger["latestDeployReadinessSummary"])
            self.assertEqual(ledger["lastObservedAt"], PUBLIC_ROUTE_AT)
            self.assertEqual(ledger["lastObservedAnonymousGetStatus"], 404)

        route_status = playbook["routeStatus"]
        self.assertTrue(route_status["workerDryRunPassed"])
        self.assertFalse(route_status["d1VisibilityPassed"])
        self.assertEqual(route_status["d1VisibilityStatus"], "not-verified-auth-required")
        self.assertEqual(route_status["cloudflareAuthSession"], "failed-not-logged-in")
        self.assertEqual(route_status["workerDeployPermission"], "not-verified-auth-required")
        self.assertFalse(route_status["code10000Seen"])
        self.assertEqual(route_status["latestReadinessCheckAt"], READINESS_AT)
        self.assertEqual(route_status["latestPublicRouteCheckAt"], PUBLIC_ROUTE_AT)
        self.assertEqual(route_status["pendingRouteAnonymousGetStatus"], ROUTE_OBSERVATIONS)
        self.assertEqual(route_status["blockedBy"], BLOCKED_BY)

        current = handoff["currentStatus"]
        self.assertEqual(current["latestReadinessCheckAt"], READINESS_AT)
        self.assertEqual(current["latestPublicRouteCheckAt"], PUBLIC_ROUTE_AT)
        self.assertEqual(current["workerDryRun"], "passed-2026-07-20")
        self.assertEqual(current["d1Visibility"], "not-verified-auth-required")
        self.assertEqual(current["cloudflareAuthSession"], "failed-not-logged-in")
        self.assertEqual(current["workerDeployPermission"], "not-verified-auth-required")
        self.assertFalse(current["code10000Seen"])
        self.assertEqual(current["pendingRouteAnonymousGetStatus"], ROUTE_OBSERVATIONS)

    def test_blocker_sentence_is_consistent_across_public_contracts(self):
        api_status = load_site_json("api-status.json")
        access_api = load_site_json("access-api.json")
        operations = load_site_json("operations.json")
        credits = load_site_json("credits.json")

        self.assertEqual(access_api["currentState"]["creditUsageWorkerDeployBlockedBy"], BLOCKED_BY)
        self.assertEqual(access_api["currentState"]["serviceRequestQueueWorkerDeployBlockedBy"], BLOCKED_BY)
        self.assertEqual(operations["currentState"]["creditUsageWorkerDeployBlockedBy"], BLOCKED_BY)
        self.assertEqual(operations["currentState"]["serviceRequestQueueWorkerDeployBlockedBy"], BLOCKED_BY)
        self.assertEqual(credits["currentState"]["creditUsageWorkerDeployBlockedBy"], BLOCKED_BY)
        self.assertEqual(credits["currentState"]["serviceRequestQueueWorkerDeployBlockedBy"], BLOCKED_BY)

        pending_endpoints = {
            endpoint["path"]: endpoint
            for endpoint in api_status["adminEndpoints"]
            if endpoint["path"] in ROUTE_OBSERVATIONS
        }
        self.assertEqual(set(pending_endpoints), set(ROUTE_OBSERVATIONS))
        for endpoint in pending_endpoints.values():
            self.assertEqual(endpoint["blockedBy"], BLOCKED_BY)

    def test_public_pages_show_current_status_and_remove_stale_claims(self):
        public_pages = {
            "access-api.html": ("2026-07-20 readiness check found Wrangler logged out", "HTTP 404"),
            "operations.html": ("2026-07-20 check passed Worker bundling but found Wrangler logged out", "HTTP 404 for both routes"),
            "credits.html": ("Wrangler logged out", "production HTTP 404"),
            "service-delivery-playbook.html": ("Wrangler is logged out", "Both prepared Worker routes returned HTTP 404"),
            "worker-routes-handoff.html": ("Wrangler not logged in", "HTTP 404 for both prepared routes"),
            "release-gates.html": ("Wrangler not logged in", "both routes returned HTTP 404 on 2026-07-20"),
            "zh-release-gates.html": ("Wrangler 未登录", "两个公开路由均返回 HTTP 404"),
            "market-quality.html": ("Account and eligible ledger path live", "Live and iterating"),
        }
        for name, expected_fragments in public_pages.items():
            text = (ROOT / "site" / name).read_text(encoding="utf-8")
            for expected in expected_fragments:
                self.assertIn(expected, text, name)

        checked_paths = [
            ROOT / "docs" / "gca_registration_backend.md",
            ROOT / "docs" / "gca_worker_pending_routes_deploy_handoff.md",
            ROOT / "launch" / "launch_status.md",
            *[ROOT / "site" / name for name in public_pages],
            *[
                ROOT / "site" / name
                for name in (
                    "access-api.json",
                    "operations.json",
                    "credits.json",
                    "service-delivery-playbook.json",
                    "worker-routes-handoff.json",
                    "release-gates.json",
                    "market-quality.json",
                )
            ],
        ]
        stale_claims = (
            "D1 visibility passed on 2026-06-18",
            "Worker dry-run and D1 visibility passed",
            "Latest 2026-06-18 readiness",
            "passed-2026-06-18",
            "blocked-error-10000",
            "Cloudflare error 10000",
            "current Cloudflare authorization can see D1",
            "D1 可见性已在 2026-06-10 检查中通过",
            "Controlled account UI in progress",
            "Connect the GCA member and 100-credit workflows to controlled HTTPS account UI",
            "contract only until controlled HTTPS backend and account UI are live",
            "draft service catalog only until controlled account UI and ledgers are live",
            "public product spec only until controlled account UI is released",
        )
        for path in checked_paths:
            text = path.read_text(encoding="utf-8")
            for stale in stale_claims:
                self.assertNotIn(stale, text, str(path.relative_to(ROOT)))


if __name__ == "__main__":
    unittest.main()
