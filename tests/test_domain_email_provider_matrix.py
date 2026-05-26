import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tools.build_domain_email_provider_matrix import build_matrix, main, render_markdown


CONFIG = {
    "domain": "gcagochina.com",
    "currentPublicEmail": "GCAgochina@outlook.com",
    "targetDomainEmail": "support@gcagochina.com",
}


class DomainEmailProviderMatrixTests(unittest.TestCase):
    def test_matrix_recommends_full_mailbox_and_blocks_receive_only_paths(self):
        matrix = build_matrix(CONFIG, generated_at="2026-05-26T00:00:00Z")

        self.assertEqual(matrix["schema"], "gca-domain-email-provider-matrix-v1")
        self.assertEqual(matrix["currentPublicEmail"], "GCAgochina@outlook.com")
        self.assertEqual(matrix["targetDomainEmail"], "support@gcagochina.com")
        self.assertEqual(matrix["status"], "choose-full-mailbox-before-basescan-resubmission")
        self.assertTrue(matrix["noLivePricing"])
        self.assertIn("lowest-cost full mailbox", matrix["decisionRule"])
        self.assertIn("Zoho Mail", matrix["recommendedDefault"])

        options = {option["key"]: option for option in matrix["providerOptions"]}
        self.assertEqual(options["zoho-mail"]["fit"], "recommended-first-check")
        self.assertEqual(options["google-workspace"]["fit"], "acceptable-full-mailbox")
        self.assertEqual(options["microsoft-365"]["fit"], "acceptable-full-mailbox")
        self.assertEqual(options["cloudflare-email-routing-only"]["fit"], "not-sufficient-alone")
        self.assertEqual(options["smtp-or-api-send-only"]["fit"], "not-sufficient-alone")
        self.assertTrue(any("only forwarding inbound mail" in item for item in options["zoho-mail"]["notEnoughIf"]))
        self.assertTrue(any("BaseScan replies are still sent from GCAgochina@outlook.com" in item for item in options["cloudflare-email-routing-only"]["notEnoughIf"]))

        records = {record["record"]: record for record in matrix["recordsToCollectFromProvider"]}
        self.assertTrue(records["MX"]["doNotGuess"])
        self.assertTrue(records["SPF"]["doNotGuess"])
        self.assertTrue(records["DKIM"]["doNotGuess"])
        self.assertIn("provider-selector", matrix["nextCommandsAfterProviderSetup"][0])
        self.assertFalse(matrix["boundaries"]["writesDnsRecords"])
        self.assertFalse(matrix["boundaries"]["sendsEmail"])
        self.assertFalse(matrix["boundaries"]["submitsBaseScanRequest"])
        self.assertFalse(matrix["boundaries"]["touchesWalletsOrContracts"])

    def test_markdown_is_copyable_and_explicit_about_boundaries(self):
        markdown = render_markdown(build_matrix(CONFIG, generated_at="2026-05-26T00:00:00Z"))

        self.assertIn("# GCA Domain Email Provider Decision Matrix", markdown)
        self.assertIn("Target domain email: `support@gcagochina.com`", markdown)
        self.assertIn("Zoho Mail or equivalent low-cost hosted mailbox", markdown)
        self.assertIn("Cloudflare Email Routing only", markdown)
        self.assertIn("not-sufficient-alone", markdown)
        self.assertIn("do not guess", markdown)
        self.assertIn("tools/check_domain_email_dns.py", markdown)
        self.assertIn("does not write DNS records, send email, submit BaseScan requests", markdown)

    def test_cli_can_write_optional_owner_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            config_path = temp_path / "domain-email.json"
            json_path = temp_path / "provider-matrix.json"
            md_path = temp_path / "provider-matrix.md"
            config_path.write_text(json.dumps(CONFIG), encoding="utf-8")

            output = StringIO()
            with redirect_stdout(output):
                exit_code = main([
                    "--config",
                    str(config_path),
                    "--output-json",
                    str(json_path),
                    "--output-md",
                    str(md_path),
                    "--json",
                ])

            self.assertEqual(exit_code, 0)
            self.assertIn("gca-domain-email-provider-matrix-v1", json_path.read_text(encoding="utf-8"))
            self.assertIn("GCA Domain Email Provider Decision Matrix", md_path.read_text(encoding="utf-8"))
            self.assertIn("not-sufficient-alone", output.getvalue())


if __name__ == "__main__":
    unittest.main()
