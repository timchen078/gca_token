import tempfile
import unittest
from pathlib import Path

from tools.submit_indexnow import BASE_URL, KEY_FILE, SITE, build_payload, public_html_urls, read_key


class IndexNowTests(unittest.TestCase):
    def test_public_url_set_includes_current_and_previously_stale_pages(self):
        urls = public_html_urls(SITE)

        self.assertGreater(len(urls), 100)
        self.assertEqual(len(urls), len(set(urls)))
        self.assertIn(f"{BASE_URL}/", urls)
        self.assertIn(f"{BASE_URL}/about.html", urls)
        self.assertIn(f"{BASE_URL}/team.html", urls)
        self.assertIn(f"{BASE_URL}/community.html", urls)
        self.assertIn(f"{BASE_URL}/project-profile.html", urls)
        self.assertNotIn(f"{BASE_URL}/404.html", urls)

    def test_payload_uses_public_key_location_and_only_official_urls(self):
        payload = build_payload()

        self.assertEqual(payload["host"], "gcagochina.com")
        self.assertEqual(payload["keyLocation"], f"{BASE_URL}/{read_key(KEY_FILE)}.txt")
        self.assertTrue(all(url.startswith(f"{BASE_URL}/") for url in payload["urlList"]))

    def test_rejects_invalid_or_mismatched_key_file(self):
        with tempfile.TemporaryDirectory() as temp:
            key_file = Path(temp) / "wrong-name.txt"
            key_file.write_text("valid-key-123", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "filename must match"):
                read_key(key_file)

    def test_cache_control_metadata_is_present_on_identity_pages(self):
        for relative in ("about.html", "team.html", "zh-about.html", "zh-team.html"):
            page = (SITE / relative).read_text(encoding="utf-8")
            self.assertIn('<meta name="robots" content="index,follow,noarchive">', page)

        for relative in ("community.html", "project-profile.html"):
            page = (SITE / relative).read_text(encoding="utf-8")
            self.assertIn('<meta name="robots" content="noindex,follow,noarchive">', page)

    def test_publish_workflow_notifies_indexnow_after_site_push(self):
        workflow = (SITE.parent / ".github" / "workflows" / "publish-site.yml").read_text(
            encoding="utf-8"
        )

        publish_position = workflow.index("git push origin HEAD:gh-pages")
        notify_position = workflow.index("Notify IndexNow after deployment")
        self.assertGreater(notify_position, publish_position)
        self.assertIn("python tools/submit_indexnow.py --submit --json", workflow)


if __name__ == "__main__":
    unittest.main()
