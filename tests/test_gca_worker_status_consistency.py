import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAST_UPDATED = "2026-07-24"
READINESS_AT = "2026-07-23T17:55:52Z"
PUBLIC_ROUTE_AT = "2026-07-23T17:53:42Z"
ADMIN_ROUTE_AT = "2026-07-23T17:53:54Z"
WORKER_VERSION_ID = "8988fc75-bbe0-403e-960a-832bf83da20f"
ROUTE_OBSERVATIONS = {
    "/gca/service-requests": 401,
    "/gca/credit-usage": 401,
}
READINESS_SUMMARY = {
    "wranglerDeployDryRun": "passed",
    "cloudflareD1Visibility": "passed",
    "cloudflareAuthSession": "passed",
    "cloudflareWorkerDeployPermission": "passed",
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
            self.assertEqual(payload["lastUpdated"], LAST_UPDATED)

        self.assertEqual(api_status["latestDeployReadinessCheckAt"], READINESS_AT)
        self.assertEqual(api_status["latestDeployReadinessStatus"], "passed-cloudflare-permissions")
        self.assert_readiness_summary(api_status["latestDeployReadinessSummary"])
        self.assertEqual(api_status["pendingRoutesDeployHandoff"]["status"], "production-live-verified")
        self.assertIsNone(api_status["pendingRoutesDeployHandoff"]["blockedBy"])
        self.assertEqual(api_status["pendingRoutesDeployHandoff"]["workerVersionId"], WORKER_VERSION_ID)

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
            self.assertEqual(ledger["lastObservedAnonymousGetStatus"], 401)
            self.assertTrue(ledger["productionWorkerEndpointLive"])
            self.assertEqual(ledger["adminSmokePassedAt"], ADMIN_ROUTE_AT)

        route_status = playbook["routeStatus"]
        self.assertTrue(route_status["productionRoutesLive"])
        self.assertTrue(route_status["workerDryRunPassed"])
        self.assertTrue(route_status["d1VisibilityPassed"])
        self.assertEqual(route_status["d1VisibilityStatus"], "passed")
        self.assertEqual(route_status["cloudflareAuthSession"], "passed")
        self.assertEqual(route_status["workerDeployPermission"], "passed")
        self.assertEqual(route_status["pendingRouteAnonymousGetStatus"], ROUTE_OBSERVATIONS)
        self.assertIsNone(route_status["blockedBy"])
        self.assertEqual(route_status["workerVersionId"], WORKER_VERSION_ID)

        current = handoff["currentStatus"]
        self.assertEqual(current["latestReadinessCheckAt"], READINESS_AT)
        self.assertEqual(current["latestPublicRouteCheckAt"], PUBLIC_ROUTE_AT)
        self.assertEqual(current["latestAdminRouteCheckAt"], ADMIN_ROUTE_AT)
        self.assertEqual(current["workerDryRun"], "passed-2026-07-23")
        self.assertEqual(current["d1Visibility"], "passed")
        self.assertEqual(current["cloudflareAuthSession"], "passed")
        self.assertEqual(current["workerDeployPermission"], "passed")
        self.assertEqual(current["pendingRouteAnonymousGetStatus"], ROUTE_OBSERVATIONS)
        self.assertEqual(current["productionRouteStatus"], "live-token-protected")

    def test_live_route_and_safety_claims_are_consistent(self):
        api_status = load_site_json("api-status.json")
        access_api = load_site_json("access-api.json")
        operations = load_site_json("operations.json")
        credits = load_site_json("credits.json")

        for state in (access_api["currentState"], operations["currentState"], credits["currentState"]):
            self.assertTrue(state["creditUsageLedgerWritesLive"])
            self.assertFalse(state["creditUsageWorkerDeployBlocked"])
            self.assertIsNone(state["creditUsageWorkerDeployBlockedBy"])
            self.assertTrue(state["serviceRequestQueueProductionLive"])
            self.assertFalse(state["serviceRequestQueueWorkerDeployBlocked"])
            self.assertIsNone(state["serviceRequestQueueWorkerDeployBlockedBy"])

        live_endpoints = {
            endpoint["path"]: endpoint
            for endpoint in api_status["adminEndpoints"]
            if endpoint["path"] in ROUTE_OBSERVATIONS
        }
        self.assertEqual(set(live_endpoints), set(ROUTE_OBSERVATIONS))
        for endpoint in live_endpoints.values():
            self.assertEqual(endpoint["status"], "live-token-protected")
            self.assertEqual(endpoint["lastObservedAnonymousGetStatus"], 401)
            self.assertTrue(endpoint["productionLive"])
            self.assertNotIn("blockedBy", endpoint)

    def test_public_pages_show_live_protected_status_and_remove_stale_claims(self):
        public_pages = {
            "access-api.html": ("Live token-protected operator queue", "HTTP 401"),
            "operations.html": ("production-live", "Anonymous reads return HTTP 401"),
            "credits.html": ("production Worker route live", "token-protected"),
            "service-delivery-playbook.html": ("routes are live and token-protected", "HTTP 401"),
            "worker-routes-handoff.html": ("Production-live and protected", "HTTP 401"),
            "release-gates.html": ("Production-live and token-protected", "2026-07-23"),
            "zh-release-gates.html": ("已经正式上线", "HTTP 401"),
            "market-quality.html": ("Account and eligible ledger path live", "Live and iterating"),
        }
        for name, expected_fragments in public_pages.items():
            text = (ROOT / "site" / name).read_text(encoding="utf-8")
            for expected in expected_fragments:
                self.assertIn(expected, text, name)

        checked_paths = [
            ROOT / "docs" / "gca_registration_backend.md",
            ROOT / "docs" / "gca_worker_pending_routes_deploy_handoff.md",
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
                )
            ],
        ]
        stale_claims = (
            "production returned HTTP 404",
            "Prepared, not production-live",
            "Worker routes remain non-live",
            "Wrangler logged out",
            "Wrangler is logged out",
            "Wrangler not logged in",
            "Wrangler 未登录",
            "prepared-worker-deploy-permission-pending",
            "prepared-worker-deploy-pending",
            "准备中路由尚未部署",
        )
        for path in checked_paths:
            text = path.read_text(encoding="utf-8")
            for stale in stale_claims:
                self.assertNotIn(stale, text, str(path.relative_to(ROOT)))


if __name__ == "__main__":
    unittest.main()
