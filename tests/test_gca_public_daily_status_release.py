import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.prepare_gca_public_daily_status_release import (
    PublicDailyStatusReleaseError,
    prepare_release,
)
from tools.check_public_site import (
    extract_daily_reference,
    normalize_dynamic_daily_reference,
)
from tools.sync_basescan_daily_status_references import PUBLIC_SITE_TARGET_FILES


ROOT = Path(__file__).resolve().parents[1]


class GcaPublicDailyStatusReleaseTests(unittest.TestCase):
    def stage_public_files(self, root: Path) -> None:
        for relative in ("site/daily-status.html", "site/daily-status.json", *PUBLIC_SITE_TARGET_FILES):
            source = ROOT / relative
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def build_summary(self, generated_at: str = "2026-08-12T08:00:00Z") -> dict:
        current = json.loads((ROOT / "site" / "daily-status.json").read_text(encoding="utf-8"))
        steps = []
        for item in current["dailyOps"]["steps"]:
            steps.append({
                "id": item["id"],
                "ok": True,
                "blocksSummaryOk": item.get("blocksSummaryOk", True),
                "command": item["command"],
            })
        profile = copy.deepcopy(current["baseScanPublicProfile"])
        profile.update({
            "available": True,
            "checkedAt": generated_at,
            "signals": {
                "officialDomainPresent": profile["officialDomainPresent"],
                "genericAddressTitle": profile["genericAddressTitle"],
                "defaultPreviewImage": profile["defaultPreviewImage"],
            },
        })
        market = copy.deepcopy(current["marketHealth"])
        market.update({
            "checkedAt": generated_at,
            "sourceProvider": market["sourceProvider"],
            "sourceApiUrl": market["sourceApiUrl"],
            "publicPoolUrl": market["publicPoolUrl"],
        })
        preflight = copy.deepcopy(current["baseScanPreflight"])
        preflight.update({
            "available": True,
            "oldEmailFilePaths": [],
            "forbiddenLegacyEmailFilePaths": [],
            "nextAction": "Keep the owner-controlled reviewer package current.",
        })
        return {
            "ok": True,
            "packetVersion": "gca_daily_ops_summary_v1",
            "generatedAt": generated_at,
            "siteBaseUrl": "https://gcagochina.com/",
            "apiBaseUrl": "https://gca-registration-api.gcagochina.workers.dev",
            "includeMemberOps": False,
            "includeServiceRoutes": False,
            "includeHoldingReport": False,
            "marketHealth": market,
            "baseScanPublicProfile": profile,
            "baseScanPreflight": preflight,
            "steps": steps,
            "boundaries": {
                "publicOnlyByDefault": True,
                "baseScanPublicProfileReadOnly": True,
                "baseScanPreflightStatusOnly": True,
                "marketHealthReadOnly": True,
                "writesProductionData": False,
                "adminTokenPrinted": False,
                "walletCalls": False,
                "requiresSignature": False,
                "requiresTransaction": False,
                "automaticTokenTransfer": False,
                "submitsBaseScanRequest": False,
                "marketHealthBuildsExecutableQuote": False,
                "marketHealthSubmitsTrade": False,
            },
        }

    def write_summary(self, root: Path, payload: dict) -> Path:
        path = root / "summary.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_prepare_release_updates_only_public_allowlist(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.stage_public_files(root)
            summary_path = self.write_summary(root, self.build_summary())

            report = prepare_release(summary_input=summary_path, release_root=root)
            payload = json.loads((root / "site" / "daily-status.json").read_text(encoding="utf-8"))

        self.assertTrue(report["ok"])
        self.assertTrue(report["publishRequired"])
        self.assertEqual(report["status"], "prepared")
        self.assertEqual(payload["snapshotGeneratedAt"], "2026-08-12T08:00:00Z")
        self.assertIn("site/daily-status.html", report["changedFiles"])
        self.assertIn("site/daily-status.json", report["changedFiles"])
        self.assertTrue(set(report["changedFiles"]).issubset(
            {"site/daily-status.html", "site/daily-status.json", *PUBLIC_SITE_TARGET_FILES}
        ))
        self.assertTrue(report["boundaries"]["publicSiteFilesOnly"])
        self.assertFalse(report["boundaries"]["writesMainBranch"])
        self.assertFalse(report["boundaries"]["publishesOperatorDigest"])
        self.assertFalse(report["boundaries"]["touchesWalletsOrContracts"])

    def test_stale_summary_is_skipped_without_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.stage_public_files(root)
            before = (root / "site" / "daily-status.json").read_text(encoding="utf-8")
            summary_path = self.write_summary(
                root,
                self.build_summary("2026-08-11T19:25:21Z"),
            )

            report = prepare_release(summary_input=summary_path, release_root=root)
            after = (root / "site" / "daily-status.json").read_text(encoding="utf-8")

        self.assertTrue(report["ok"])
        self.assertFalse(report["publishRequired"])
        self.assertEqual(report["changedFiles"], [])
        self.assertEqual(before, after)

    def test_member_ops_summary_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.stage_public_files(root)
            summary = self.build_summary()
            summary["includeMemberOps"] = True
            summary_path = self.write_summary(root, summary)

            with self.assertRaises(PublicDailyStatusReleaseError):
                prepare_release(summary_input=summary_path, release_root=root)

    def test_profile_state_change_requires_main_package_update(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.stage_public_files(root)
            summary = self.build_summary()
            summary["baseScanPublicProfile"]["profilePublished"] = True
            summary["baseScanPublicProfile"]["status"] = "profile-published"
            summary_path = self.write_summary(root, summary)

            with self.assertRaises(PublicDailyStatusReleaseError):
                prepare_release(summary_input=summary_path, release_root=root)

    def test_public_checker_normalizes_dynamic_reviewer_references(self):
        reference = extract_daily_reference(json.dumps({
            "snapshotGeneratedAt": "2026-08-12T08:00:00Z",
            "baseScanPublicProfile": {"checkedAt": "2026-08-12T07:59:00Z"},
        }))
        payload = {
            "dailyStatusGeneratedAt": "2026-08-12T08:00:00Z",
            "lastCheckedDate": "2026-08-12",
            "evidence": (
                "Read-only public BaseScan check on 2026-08-12; "
                "daily status 2026-08-12T08:00:00Z."
            ),
            "unrelatedDate": "2026-08-12",
        }

        normalized = json.loads(normalize_dynamic_daily_reference(
            json.dumps(payload),
            "/project.json",
            reference,
        ))

        self.assertEqual(normalized["dailyStatusGeneratedAt"], "2026-08-11T19:25:21Z")
        self.assertEqual(normalized["lastCheckedDate"], "2026-08-11")
        self.assertIn("check on 2026-08-11", normalized["evidence"])
        self.assertIn("2026-08-11T19:25:21Z", normalized["evidence"])
        self.assertEqual(normalized["unrelatedDate"], "2026-08-12")

    def test_daily_status_endpoint_is_not_normalized(self):
        body = json.dumps({
            "snapshotGeneratedAt": "2026-08-12T08:00:00Z",
            "baseScanPublicProfile": {"checkedAt": "2026-08-12T07:59:00Z"},
        })
        reference = extract_daily_reference(body)

        self.assertEqual(
            normalize_dynamic_daily_reference(body, "/daily-status.json", reference),
            body,
        )


if __name__ == "__main__":
    unittest.main()
