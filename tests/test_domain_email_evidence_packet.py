import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tools.build_domain_email_evidence_packet import (
    build_manual_evidence,
    build_packet,
    main,
    render_markdown,
)


DOMAIN_EMAIL_CONFIG = {
    "domain": "gcagochina.com",
    "currentPublicEmail": "GCAgochina@outlook.com",
    "targetDomainEmail": "support@gcagochina.com",
}

READY_DNS_RESULT = {
    "checkedAt": "2026-05-24T00:00:00Z",
    "domain": "gcagochina.com",
    "targetMailbox": "support@gcagochina.com",
    "dkimSelector": "selector1",
    "readyForBaseScanEmailEvidence": True,
    "missingOrBlockedChecks": [],
    "checks": {
        "mx": {"status": "present", "records": ["10 mail.example.com."]},
        "spf": {"status": "present", "records": ["v=spf1 include:example.com -all"]},
        "dmarc": {"status": "present", "records": ["v=DMARC1; p=none"]},
        "dkim": {"status": "present", "records": ["v=DKIM1; p=abc"]},
    },
}

BLOCKED_DNS_RESULT = {
    **READY_DNS_RESULT,
    "readyForBaseScanEmailEvidence": False,
    "dkimSelector": None,
    "missingOrBlockedChecks": ["dkim"],
    "checks": {
        **READY_DNS_RESULT["checks"],
        "dkim": {"status": "selector-required", "records": []},
    },
}

COMPLETE_REFERENCES = {
    "providerActive": "domain-email-provider-active.png",
    "dnsProof": "domain-email-dns-mx-spf-dkim-dmarc.txt",
    "inboundTest": "domain-email-inbound-test.png",
    "outboundTest": "domain-email-outbound-test.png",
    "supportPageProof": "support-page-domain-email.png",
}


class DomainEmailEvidencePacketTests(unittest.TestCase):
    def test_packet_blocks_basescan_when_dns_or_manual_evidence_is_missing(self):
        packet = build_packet(
            domain_email_config=DOMAIN_EMAIL_CONFIG,
            dns_result=BLOCKED_DNS_RESULT,
            manual_evidence=build_manual_evidence({}),
            website_email_updated=False,
            generated_at="2026-05-24T00:00:00Z",
        )

        self.assertFalse(packet["readyForBaseScanResubmission"])
        self.assertEqual(packet["status"], "blocked-before-basescan-resubmission")
        self.assertIn("dns-ready", packet["missingOrBlockedRequirements"])
        self.assertIn("website-email-updated", packet["missingOrBlockedRequirements"])
        self.assertIn("providerActive", packet["missingOrBlockedRequirements"])
        self.assertFalse(packet["boundaries"]["submitsBaseScanRequest"])
        self.assertFalse(packet["boundaries"]["touchesWalletOrContract"])

    def test_packet_is_ready_only_when_dns_manual_evidence_and_website_gate_pass(self):
        packet = build_packet(
            domain_email_config=DOMAIN_EMAIL_CONFIG,
            dns_result=READY_DNS_RESULT,
            manual_evidence=build_manual_evidence(COMPLETE_REFERENCES),
            website_email_updated=True,
            generated_at="2026-05-24T00:00:00Z",
        )

        self.assertTrue(packet["readyForBaseScanResubmission"])
        self.assertEqual(packet["status"], "ready-for-owner-resubmission")
        self.assertEqual(packet["missingOrBlockedRequirements"], [])
        self.assertEqual(packet["baseScanSubmissionPolicy"]["nextCleanSubmissionSender"], "support@gcagochina.com")
        self.assertIn("https://gcagochina.com/tim-chen.html", packet["baseScanSubmissionPolicy"]["includeProfessionalProfile"])

    def test_markdown_packet_is_copyable_and_keeps_boundaries(self):
        packet = build_packet(
            domain_email_config=DOMAIN_EMAIL_CONFIG,
            dns_result=READY_DNS_RESULT,
            manual_evidence=build_manual_evidence(COMPLETE_REFERENCES),
            website_email_updated=True,
            generated_at="2026-05-24T00:00:00Z",
        )

        markdown = render_markdown(packet)

        self.assertIn("GCA Domain Email Evidence Packet", markdown)
        self.assertIn("Ready for BaseScan resubmission: `true`", markdown)
        self.assertIn("support@gcagochina.com", markdown)
        self.assertIn("This packet does not submit a BaseScan request.", markdown)
        self.assertIn("This packet does not touch wallets, contracts, liquidity, or DNS records.", markdown)

    def test_cli_can_write_json_and_markdown_from_saved_dns_result(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            config_path = temp_path / "domain-email.json"
            dns_path = temp_path / "dns.json"
            packet_json = temp_path / "packet.json"
            packet_md = temp_path / "packet.md"
            config_path.write_text(json.dumps(DOMAIN_EMAIL_CONFIG), encoding="utf-8")
            dns_path.write_text(json.dumps(READY_DNS_RESULT), encoding="utf-8")

            output = StringIO()
            with redirect_stdout(output):
                exit_code = main([
                    "--config",
                    str(config_path),
                    "--dns-json",
                    str(dns_path),
                    "--provider-active",
                    "domain-email-provider-active.png",
                    "--dns-proof",
                    "domain-email-dns-mx-spf-dkim-dmarc.txt",
                    "--inbound-test",
                    "domain-email-inbound-test.png",
                    "--outbound-test",
                    "domain-email-outbound-test.png",
                    "--support-page-proof",
                    "support-page-domain-email.png",
                    "--website-email-updated",
                    "--output-json",
                    str(packet_json),
                    "--output-md",
                    str(packet_md),
                    "--json",
                ])

            self.assertEqual(exit_code, 0)
            packet = json.loads(packet_json.read_text(encoding="utf-8"))
            self.assertTrue(packet["readyForBaseScanResubmission"])
            self.assertIn("ready-for-owner-resubmission", packet_md.read_text(encoding="utf-8"))
            self.assertIn("ready-for-owner-resubmission", output.getvalue())


if __name__ == "__main__":
    unittest.main()
