import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class PublicSiteExperienceTests(unittest.TestCase):
    def test_shared_experience_assets_exist(self):
        stylesheet = (SITE / "assets" / "gca-site.css").read_text()
        script = (SITE / "assets" / "gca-site.js").read_text()

        self.assertIn(".gca-menu-button", stylesheet)
        self.assertIn(".gca-back-to-top", stylesheet)
        self.assertIn("prefers-reduced-motion", stylesheet)
        self.assertIn("Skip to main content", script)
        self.assertIn("跳到主要内容", script)
        self.assertIn('viewer.searchParams.set("source", target.href)', script)
        self.assertIn('rel = "noopener noreferrer"', script)

    def test_public_pages_load_shared_experience_layer(self):
        missing = []
        for path in sorted(SITE.rglob("*.html")):
            relative = path.relative_to(SITE)
            if relative.as_posix() == "operator.html":
                continue

            depth = len(relative.parts) - 1
            prefix = "../" * depth
            page = path.read_text()
            expected_css = f'href="{prefix}assets/gca-site.css?v=20260711"'
            expected_js = f'src="{prefix}assets/gca-site.js?v=20260711" defer'
            if expected_css not in page or expected_js not in page:
                missing.append(relative.as_posix())

        self.assertEqual([], missing)

    def test_data_viewer_is_human_readable_and_does_not_publish_raw_json_href(self):
        page = (SITE / "data-viewer.html").read_text()

        self.assertIn("GCA Data Viewer", page)
        self.assertIn('id="dataRoot"', page)
        self.assertIn('id="readablePage"', page)
        self.assertIn('id="rawLink"', page)
        self.assertIn('["/project.json", "project-profile.html"]', page)
        self.assertIn('["/.well-known/gca-token.json", "trust.html"]', page)
        self.assertIn('["/.well-known/wallet-security.json", "token-safety.html"]', page)
        self.assertIn("relatedPages.get(source.pathname)", page)
        self.assertIn('textContent = String(value)', page)
        self.assertNotRegex(page, re.compile(r'href="[^"]+\.json"'))

    def test_global_navigation_keeps_primary_user_paths_small(self):
        script = (SITE / "assets" / "gca-site.js").read_text()

        for path in (
            "index.html",
            "verify.html",
            "buy.html",
            "product.html",
            "gca/member-access/",
            "trust.html",
            "zh-cn.html",
        ):
            self.assertIn(f'"{path}"', script)

        self.assertIn('navLinks.replaceChildren()', script)
        self.assertIn('aria-current", "page"', script)


if __name__ == "__main__":
    unittest.main()
