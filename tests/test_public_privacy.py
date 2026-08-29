import tempfile
import unittest
from pathlib import Path

from tools.check_public_privacy import check_public_privacy


ROOT = Path(__file__).resolve().parents[1]


class PublicPrivacyTests(unittest.TestCase):
    def test_current_public_site_contains_no_personal_identity_markers(self):
        report = check_public_privacy(ROOT / "site")

        self.assertTrue(report["ok"], report["findings"])
        self.assertGreater(report["filesChecked"], 100)

    def test_rejects_personal_email_user_path_profile_and_author_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp)
            (site / "index.html").write_text(
                """<meta name="author" content="Example Person">
<a href="mailto:person@personal.test">Mail</a>
<a href="https://github.com/example-person">Code</a>
<pre>cd /Users/example/private-project</pre>
""",
                encoding="utf-8",
            )

            report = check_public_privacy(site)

        self.assertFalse(report["ok"])
        kinds = {finding["kind"] for finding in report["findings"]}
        self.assertIn("non-project email", kinds)
        self.assertIn("macOS user path", kinds)
        self.assertIn("personal GitHub profile", kinds)
        self.assertIn("HTML author metadata", kinds)

    def test_allows_project_email_and_neutral_form_placeholders(self):
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp)
            (site / "index.html").write_text(
                "support@gcagochina.com user@example.com",
                encoding="utf-8",
            )

            report = check_public_privacy(site)

        self.assertTrue(report["ok"], report["findings"])


if __name__ == "__main__":
    unittest.main()
