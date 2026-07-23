import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.check_basescan_public_profile import (
    BaseScanProfileCheckError,
    check_profile,
    classify_profile,
)


UNKNOWN_TOKEN_HTML = """
<html><head>
<meta content="https://basescan.org/assets/base/images/og-preview-sm.jpg?v=" property="og:image">
<meta name="Description" content="Token Rep: Unknown | Holders: 10 | As at Jul-23-2026">
<meta property="og:title" content="ERC-20 Token | Address: 0x3197c42f...f0ff682c6 | BaseScan">
</head><body>GCA</body></html>
"""

PUBLISHED_TOKEN_HTML = """
<html><head>
<meta name="description" content="Token Rep: GCA Team | Holders: 1,234">
<meta property="og:title" content="GCA (Go China Access) Token Tracker | BaseScan">
<meta property="og:image" content="https://gcagochina.com/assets/gca-logo.svg">
</head><body><a href="https://gcagochina.com/">Official Website</a></body></html>
"""

VERIFIED_ADDRESS_HTML = """
<html><body><strong>Source Code Verified</strong><span>Exact Match</span></body></html>
"""


class BaseScanPublicProfileTests(unittest.TestCase):
    def test_classifies_current_unknown_profile_without_confusing_source_verification(self):
        payload = classify_profile(
            UNKNOWN_TOKEN_HTML,
            VERIFIED_ADDRESS_HTML,
            checked_at="2026-07-23T12:00:00Z",
        )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "token-profile-not-published")
        self.assertFalse(payload["profilePublished"])
        self.assertEqual(payload["tokenRep"], "Unknown")
        self.assertEqual(payload["holders"], 10)
        self.assertTrue(payload["sourceVerificationObserved"])
        self.assertFalse(payload["signals"]["officialDomainPresent"])
        self.assertTrue(payload["signals"]["genericAddressTitle"])
        self.assertTrue(payload["signals"]["defaultPreviewImage"])
        self.assertFalse(payload["boundaries"]["claimsSourceVerificationImpliesSafety"])

    def test_classifies_complete_public_profile(self):
        payload = classify_profile(PUBLISHED_TOKEN_HTML, VERIFIED_ADDRESS_HTML)

        self.assertEqual(payload["status"], "profile-published")
        self.assertTrue(payload["profilePublished"])
        self.assertEqual(payload["tokenRep"], "GCA Team")
        self.assertEqual(payload["holders"], 1234)
        self.assertTrue(payload["signals"]["officialDomainPresent"])
        self.assertFalse(payload["signals"]["genericAddressTitle"])
        self.assertFalse(payload["signals"]["defaultPreviewImage"])

    def test_classifies_partial_signals_as_ambiguous(self):
        token_html = UNKNOWN_TOKEN_HTML.replace(
            "</body>",
            '<a href="https://gcagochina.com/">Website</a></body>',
        )
        payload = classify_profile(token_html, "<html></html>")

        self.assertEqual(payload["status"], "partial-or-ambiguous")
        self.assertFalse(payload["profilePublished"])
        self.assertFalse(payload["sourceVerificationObserved"])

    def test_fixture_mode_requires_both_html_files(self):
        with self.assertRaises(BaseScanProfileCheckError):
            check_profile(token_html_file=Path("token.html"))

    def test_cli_fixture_mode_and_require_published_exit_codes(self):
        root = Path(__file__).resolve().parents[1]
        script = root / "tools" / "check_basescan_public_profile.py"
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            token_file = temp_root / "token.html"
            address_file = temp_root / "address.html"
            token_file.write_text(UNKNOWN_TOKEN_HTML, encoding="utf-8")
            address_file.write_text(VERIFIED_ADDRESS_HTML, encoding="utf-8")
            command = [
                sys.executable,
                str(script),
                "--token-html-file",
                str(token_file),
                "--address-html-file",
                str(address_file),
                "--checked-at",
                "2026-07-23T12:00:00Z",
                "--json",
            ]

            completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
            required = subprocess.run(
                [*command, "--require-published"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["checkedAt"], "2026-07-23T12:00:00Z")
        self.assertEqual(payload["status"], "token-profile-not-published")
        self.assertEqual(required.returncode, 1)


if __name__ == "__main__":
    unittest.main()
