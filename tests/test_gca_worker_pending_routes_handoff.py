import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GcaWorkerPendingRoutesHandoffTests(unittest.TestCase):
    def test_pending_routes_deploy_handoff_has_safe_ordered_gates(self):
        handoff = (ROOT / "docs" / "gca_worker_pending_routes_deploy_handoff.md").read_text(encoding="utf-8")

        expected_fragments = [
            "Authentication error [code: 10000]",
            "Do not run `wrangler deploy` until the read-only deploy permission gate passes.",
            "cloudflare-auth-session",
            "authRecovery.status: cloudflare-auth-or-permission-blocked",
            "python3 tools/check_gca_worker_deploy_readiness.py --run-wrangler --run-cloudflare --require-deploy-auth",
            "npx wrangler d1 migrations apply gca_registration --remote",
            "0005_service_requests.sql",
            "npx wrangler deploy",
            "python3 tools/check_gca_registration_api.py --public-only --timeout 30 --include-pending-routes",
            "python3 tools/check_gca_registration_api.py --token-file cloudflare/gca-registration-worker/.env.admin.local --limit 5 --include-pending-routes",
            "tools/export_cloudflare_member_access.py",
            "Do not publish full user records.",
        ]
        for expected in expected_fragments:
            self.assertIn(expected, handoff)

        readiness_index = handoff.index("python3 tools/check_gca_worker_deploy_readiness.py --run-wrangler --run-cloudflare --require-deploy-auth")
        migration_index = handoff.index("npx wrangler d1 migrations apply gca_registration --remote")
        deploy_index = handoff.index("\nnpx wrangler deploy\n")
        public_smoke_index = handoff.index("python3 tools/check_gca_registration_api.py --public-only --timeout 30 --include-pending-routes")
        admin_smoke_index = handoff.index("python3 tools/check_gca_registration_api.py --token-file cloudflare/gca-registration-worker/.env.admin.local --limit 5 --include-pending-routes")

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
            self.assertIn(boundary, handoff)
        self.assertNotIn("ADMIN_READ_TOKEN=", handoff)

    def test_public_api_status_records_pending_handoff_without_live_claim(self):
        api = json.loads((ROOT / "site" / "api-status.json").read_text(encoding="utf-8"))
        handoff = api["pendingRoutesDeployHandoff"]

        self.assertEqual(handoff["document"], "docs/gca_worker_pending_routes_deploy_handoff.md")
        self.assertEqual(handoff["status"], "prepared-not-production-live")
        self.assertEqual(
            handoff["blockedBy"],
            "Latest 2026-07-20 readiness check passed Worker dry-run but found Wrangler not logged in; Cloudflare account authentication, D1 visibility, remote migration, deploy permission, and post-deploy smoke checks remain blocked",
        )
        self.assertCountEqual(handoff["routes"], ["/gca/service-requests", "/gca/credit-usage"])
        self.assertEqual(
            handoff["readOnlyGateCommand"],
            "python3 tools/check_gca_worker_deploy_readiness.py --run-wrangler --run-cloudflare --require-deploy-auth",
        )
        self.assertEqual(api["checks"]["workerDeployReadinessAuthSessionCheck"], "cloudflare-auth-session")
        self.assertEqual(api["checks"]["workerDeployReadinessAuthRecoveryField"], "authRecovery")
        self.assertEqual(
            handoff["remoteMigrationCommand"],
            "cd cloudflare/gca-registration-worker && npx wrangler d1 migrations apply gca_registration --remote",
        )
        self.assertEqual(
            handoff["deployCommand"],
            "cd cloudflare/gca-registration-worker && npx wrangler deploy",
        )
        self.assertEqual(
            handoff["postDeployPublicSmokeCommand"],
            "python3 tools/check_gca_registration_api.py --public-only --timeout 30 --include-pending-routes",
        )
        self.assertEqual(
            handoff["postDeployAdminSmokeCommand"],
            "python3 tools/check_gca_registration_api.py --token-file cloudflare/gca-registration-worker/.env.admin.local --limit 5 --include-pending-routes",
        )
        self.assertIn("cloudflare-auth-session passes", handoff["statusUpdateAllowedAfter"])
        self.assertIn("D1 visibility passes", handoff["statusUpdateAllowedAfter"])
        self.assertIn("Worker deploy permission passes", handoff["statusUpdateAllowedAfter"])
        self.assertIn("remote D1 migrations apply successfully", handoff["statusUpdateAllowedAfter"])
        self.assertIn("admin smoke check passes with --include-pending-routes", handoff["statusUpdateAllowedAfter"])

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

        route_statuses = {
            endpoint["path"]: endpoint["status"]
            for endpoint in api["adminEndpoints"]
            if endpoint["path"] in {"/gca/service-requests", "/gca/credit-usage"}
        }
        blocked_by = {
            endpoint["path"]: endpoint["blockedBy"]
            for endpoint in api["adminEndpoints"]
            if endpoint["path"] in {"/gca/service-requests", "/gca/credit-usage"}
        }
        self.assertEqual(route_statuses["/gca/service-requests"], "prepared-worker-deploy-permission-pending")
        self.assertEqual(route_statuses["/gca/credit-usage"], "prepared-worker-deploy-permission-pending")
        self.assertIn("Cloudflare account authentication", blocked_by["/gca/service-requests"])
        self.assertIn("D1 visibility", blocked_by["/gca/credit-usage"])

    def test_api_status_page_and_backend_doc_point_to_handoff(self):
        page = (ROOT / "site" / "api-status.html").read_text(encoding="utf-8")
        backend_doc = (ROOT / "docs" / "gca_registration_backend.md").read_text(encoding="utf-8")

        for expected in (
            "Pending Routes Handoff",
            "docs/gca_worker_pending_routes_deploy_handoff.md",
            "Cloudflare account authentication",
            "D1 visibility",
            "Worker deploy permission",
            "authRecovery.status",
            "remote D1 migrations, deploy",
            "--include-pending-routes",
            "/gca/service-requests",
            "/gca/credit-usage",
        ):
            self.assertIn(expected, page)

        self.assertIn("docs/gca_worker_pending_routes_deploy_handoff.md", backend_doc)
        self.assertIn("Admin service request endpoint: `GET/POST /gca/service-requests` prepared in source", backend_doc)
        self.assertIn("Service request D1 migration: `cloudflare/gca-registration-worker/migrations/0005_service_requests.sql`", backend_doc)
        self.assertIn("remote D1 migrations are applied", backend_doc)
        self.assertIn("cloudflare-auth-session", backend_doc)
        self.assertIn("authRecovery.safeNextActions", backend_doc)


if __name__ == "__main__":
    unittest.main()
