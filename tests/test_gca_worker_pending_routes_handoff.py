import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GcaWorkerRoutesDeploymentTests(unittest.TestCase):
    def test_deployment_record_keeps_safe_ordered_gates_and_result(self):
        record = (ROOT / "docs" / "gca_worker_pending_routes_deploy_handoff.md").read_text(encoding="utf-8")

        expected_fragments = [
            "Production Verification",
            "2026-07-23T17:55:52Z",
            "fa923065-dd72-472e-9c28-04ef4a08c34e",
            "Anonymous reads for both operator routes return HTTP `401`",
            "Authentication error [code: 10000]",
            "cloudflare-auth-session",
            "authRecovery.status: cloudflare-auth-or-permission-blocked",
            "python3 tools/check_gca_worker_deploy_readiness.py --run-wrangler --run-cloudflare --require-deploy-auth",
            "npx wrangler d1 migrations apply gca_registration --remote",
            "0005_service_requests.sql",
            "npx wrangler deploy",
            "python3 tools/check_gca_registration_api.py --public-only --timeout 30 --include-pending-routes",
            "python3 tools/check_gca_registration_api.py --token-file cloudflare/gca-registration-worker/.env.admin.local --limit 5 --include-pending-routes",
            "Do not publish full user records.",
        ]
        for expected in expected_fragments:
            self.assertIn(expected, record)

        readiness_index = record.index("python3 tools/check_gca_worker_deploy_readiness.py --run-wrangler --run-cloudflare --require-deploy-auth")
        migration_index = record.index("npx wrangler d1 migrations apply gca_registration --remote")
        deploy_index = record.index("\nnpx wrangler deploy\n")
        public_smoke_index = record.index("python3 tools/check_gca_registration_api.py --public-only --timeout 30 --include-pending-routes")
        admin_smoke_index = record.index("python3 tools/check_gca_registration_api.py --token-file cloudflare/gca-registration-worker/.env.admin.local --limit 5 --include-pending-routes")

        self.assertLess(readiness_index, migration_index)
        self.assertLess(migration_index, deploy_index)
        self.assertLess(deploy_index, public_smoke_index)
        self.assertLess(public_smoke_index, admin_smoke_index)

        for boundary in (
            "they do not connect wallets",
            "they do not request wallet signatures",
            "they do not send transactions",
            "they do not transfer GCA",
            "they do not create live trading permission",
        ):
            self.assertIn(boundary, record)
        self.assertNotIn("ADMIN_READ_TOKEN=", record)

    def test_public_api_status_records_live_protected_routes(self):
        api = json.loads((ROOT / "site" / "api-status.json").read_text(encoding="utf-8"))
        handoff = api["pendingRoutesDeployHandoff"]

        self.assertEqual(handoff["document"], "docs/gca_worker_pending_routes_deploy_handoff.md")
        self.assertEqual(handoff["status"], "production-live-verified")
        self.assertIsNone(handoff["blockedBy"])
        self.assertEqual(handoff["workerVersionId"], "fa923065-dd72-472e-9c28-04ef4a08c34e")
        self.assertCountEqual(handoff["routes"], ["/gca/service-requests", "/gca/credit-usage"])

        boundaries = handoff["boundaries"]
        for key in (
            "operatorOnly",
            "requiresAdminReadToken",
            "serviceRequestsDoNotDeductCredits",
            "noWalletConnection",
            "noWalletSignature",
            "noTransaction",
            "noAutomaticTokenTransfer",
            "noTradingPermission",
            "doNotClaimLiveBeforeSmokeChecks",
        ):
            self.assertIs(boundaries[key], True)
        self.assertIs(boundaries["publicLedgerReadable"], False)

        routes = {
            endpoint["path"]: endpoint
            for endpoint in api["adminEndpoints"]
            if endpoint["path"] in {"/gca/service-requests", "/gca/credit-usage"}
        }
        for route in routes.values():
            self.assertEqual(route["status"], "live-token-protected")
            self.assertEqual(route["lastObservedAnonymousGetStatus"], 401)
            self.assertTrue(route["productionLive"])
            self.assertNotIn("blockedBy", route)

    def test_api_status_page_and_backend_doc_publish_deployment_record(self):
        page = (ROOT / "site" / "api-status.html").read_text(encoding="utf-8")
        backend_doc = (ROOT / "docs" / "gca_registration_backend.md").read_text(encoding="utf-8")

        for expected in (
            "Service Routes Deployment",
            "Worker Routes Deployment Record",
            "production-live",
            "HTTP 401",
            "--include-pending-routes",
            "/gca/service-requests",
            "/gca/credit-usage",
        ):
            self.assertIn(expected, page)

        self.assertIn("docs/gca_worker_pending_routes_deploy_handoff.md", backend_doc)
        self.assertIn("Admin service request endpoint: `GET/POST /gca/service-requests` live and token-protected", backend_doc)
        self.assertIn("Service request D1 migration: `cloudflare/gca-registration-worker/migrations/0005_service_requests.sql`", backend_doc)
        self.assertIn("Anonymous reads return HTTP 401", backend_doc)


if __name__ == "__main__":
    unittest.main()
