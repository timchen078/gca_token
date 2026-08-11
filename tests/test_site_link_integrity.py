import ssl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.check_site_links import build_ssl_context, scan_site


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class SiteLinkIntegrityTests(unittest.TestCase):
    def test_live_tls_context_uses_certifi_when_available(self):
        try:
            import certifi
        except ImportError:
            expected_arguments = {}
        else:
            expected_arguments = {"cafile": certifi.where()}

        with patch("tools.check_site_links.ssl.create_default_context", wraps=ssl.create_default_context) as create_context:
            context = build_ssl_context()

        self.assertIsInstance(context, ssl.SSLContext)
        create_context.assert_called_once_with(**expected_arguments)

    def test_current_public_site_has_no_broken_links_or_fragments(self):
        report = scan_site(SITE)

        self.assertTrue(report.ok, "\n".join(report.errors))
        self.assertGreaterEqual(report.page_count, 120)
        self.assertGreaterEqual(report.reference_count, 5000)
        self.assertGreaterEqual(report.internal_reference_count, 5000)
        self.assertGreaterEqual(report.fragment_reference_count, 100)
        self.assertGreaterEqual(len(report.internal_urls), 200)
        self.assertIn("/", report.internal_urls)
        self.assertIn("/verify.html", report.internal_urls)
        self.assertIn("/assets/gca-logo.svg", report.internal_urls)

        data_viewer = (SITE / "data-viewer.html").read_text(encoding="utf-8")
        self.assertIn('id="rawLink" href="data.html"', data_viewer)
        self.assertNotIn('id="rawLink" href="#"', data_viewer)

    def test_valid_internal_assets_fragments_and_safe_external_links_pass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            site = Path(temp_dir)
            (site / "assets").mkdir()
            (site / "assets" / "app.js").write_text("console.log('fixture');\n", encoding="utf-8")
            (site / "index.html").write_text(
                """<!doctype html><html><head>
                <link rel="canonical" href="https://gcagochina.com/">
                <script src="assets/app.js"></script>
                </head><body id="top">
                <a href="page.html#section">Section</a>
                <a href="page.html#source=journal">Client state</a>
                <a href="https://basescan.org/address/0x1" target="_blank" rel="noreferrer">Explorer</a>
                <a href="mailto:support@gcagochina.com">Email</a>
                </body></html>""",
                encoding="utf-8",
            )
            (site / "page.html").write_text(
                """<!doctype html><html><body>
                <section id="section">Evidence</section>
                <a href="index.html#top">Home</a>
                </body></html>""",
                encoding="utf-8",
            )

            report = scan_site(site)

        self.assertTrue(report.ok, "\n".join(report.errors))
        self.assertEqual(report.page_count, 2)
        self.assertIn("/assets/app.js", report.internal_urls)
        self.assertIn("/page.html", report.internal_urls)

    def test_broken_targets_placeholders_and_unsafe_links_fail(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            site = Path(temp_dir)
            (site / "index.html").write_text(
                """<!doctype html><html><body>
                <div id="duplicate"></div><div id="duplicate"></div>
                <a href="#">Placeholder</a>
                <a href="#missing-fragment">Missing fragment</a>
                <a href="missing.html">Missing page</a>
                <a href="javascript:alert(1)">Script URL</a>
                <a href="http://preview.example.com/path" target="_blank">Unsafe placeholder</a>
                <a href="https://basescan.org/address/0x1" target="_blank">Missing rel</a>
                </body></html>""",
                encoding="utf-8",
            )

            report = scan_site(site)

        self.assertFalse(report.ok)
        errors = "\n".join(report.errors)
        self.assertIn("duplicate id 'duplicate'", errors)
        self.assertIn("placeholder fragment", errors)
        self.assertIn("missing fragment target #missing-fragment", errors)
        self.assertIn("missing internal target /missing.html", errors)
        self.assertIn("unsupported URL scheme 'javascript'", errors)
        self.assertIn("external URL must use HTTPS", errors)
        self.assertIn("placeholder or local-only host is not allowed", errors)
        self.assertIn("target=_blank requires rel=noopener or noreferrer", errors)


if __name__ == "__main__":
    unittest.main()
