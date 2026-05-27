import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "build_domain_email_dns_entry_packet.py"

spec = importlib.util.spec_from_file_location("build_domain_email_dns_entry_packet", TOOL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DomainEmailDnsEntryPacketTests(unittest.TestCase):
    def test_packet_normalizes_provider_records_and_boundaries(self):
        packet = module.build_packet(
            provider="Zoho Mail",
            mx_records=["10 mx.zoho.com.", "20 mx2.zoho.com"],
            spf="v=spf1 include:zoho.com ~all",
            dkim_selector="zmail",
            dkim_type="TXT",
            dkim_value="v=DKIM1; k=rsa; p=abc123",
            dmarc="v=DMARC1; p=none;",
            generated_at="2026-05-27T00:00:00Z",
        )

        self.assertTrue(packet["readyForOwnerDnsEntryReview"])
        self.assertEqual(packet["targetDomainEmail"], "support@gcagochina.com")
        self.assertEqual(packet["missingOrBlockedRequirements"], [])
        self.assertEqual([record["record"] for record in packet["records"]], ["MX", "MX", "SPF", "DKIM", "DMARC"])
        self.assertEqual(packet["records"][0]["value"], "mx.zoho.com")
        self.assertEqual(packet["records"][3]["nameOrHost"], "zmail._domainkey")
        self.assertFalse(packet["boundaries"]["writesDnsRecords"])
        self.assertFalse(packet["boundaries"]["submitsBaseScanRequest"])
        self.assertFalse(packet["boundaries"]["touchesWalletsOrContracts"])

    def test_packet_blocks_missing_values(self):
        packet = module.build_packet(provider="Provider", generated_at="2026-05-27T00:00:00Z")

        self.assertFalse(packet["readyForOwnerDnsEntryReview"])
        self.assertEqual(packet["status"], "missing-provider-dns-values")
        self.assertCountEqual(packet["missingOrBlockedRequirements"], ["mx", "spf", "dkim", "dmarc"])

    def test_invalid_provider_values_fail_fast(self):
        with self.assertRaises(module.DnsEntryPacketError):
            module.build_packet(provider="Provider", mx_records=["mx.example.com"], spf="v=spf1 include:example.com ~all")
        with self.assertRaises(module.DnsEntryPacketError):
            module.build_packet(provider="Provider", spf="include:example.com ~all")
        with self.assertRaises(module.DnsEntryPacketError):
            module.build_packet(provider="Provider", dkim_selector="bad selector", dkim_type="TXT", dkim_value="abc")
        with self.assertRaises(module.DnsEntryPacketError):
            module.build_packet(provider="Provider", dmarc="p=none")

    def test_markdown_is_copyable_and_explicit(self):
        packet = module.build_packet(
            provider="Zoho Mail",
            mx_records=["10 mx.zoho.com"],
            spf="v=spf1 include:zoho.com ~all",
            dkim_selector="zmail",
            dkim_type="TXT",
            dkim_value="v=DKIM1; p=abc123",
            dmarc="v=DMARC1; p=none;",
            generated_at="2026-05-27T00:00:00Z",
        )
        markdown = module.render_markdown(packet)

        self.assertIn("# GCA Domain Email DNS Entry Packet", markdown)
        self.assertIn("Ready for owner DNS entry review: `true`", markdown)
        self.assertIn("support@gcagochina.com", markdown)
        self.assertIn("This packet does not write DNS records.", markdown)
        self.assertIn("tools/check_domain_email_dns.py", markdown)

    def test_cli_can_write_optional_owner_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "dns-entry.json"
            md_path = Path(tmp) / "dns-entry.md"
            result = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--provider",
                    "Zoho Mail",
                    "--mx",
                    "10 mx.zoho.com",
                    "--spf",
                    "v=spf1 include:zoho.com ~all",
                    "--dkim-selector",
                    "zmail",
                    "--dkim-type",
                    "TXT",
                    "--dkim-value",
                    "v=DKIM1; p=abc123",
                    "--dmarc",
                    "v=DMARC1; p=none;",
                    "--output-json",
                    str(json_path),
                    "--output-md",
                    str(md_path),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.stdout, "")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["readyForOwnerDnsEntryReview"])
            self.assertIn("GCA Domain Email DNS Entry Packet", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
