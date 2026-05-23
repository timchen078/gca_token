import json
import unittest
from contextlib import redirect_stderr
from io import StringIO

from tools.check_domain_email_dns import DomainEmailDnsError, main, normalize_txt_line, run_checks


class FakeCompleted:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


def fake_runner_factory(records):
    calls = []

    def runner(command, **kwargs):
        calls.append((tuple(command), kwargs))
        record_type = command[2]
        name = command[3]
        return FakeCompleted(records.get((record_type, name), ""))

    runner.calls = calls
    return runner


class DomainEmailDnsCheckTests(unittest.TestCase):
    def test_normalize_txt_line_joins_dig_chunks(self):
        self.assertEqual(
            normalize_txt_line('"v=spf1 include:_spf.example.com " "-all"'),
            "v=spf1 include:_spf.example.com -all",
        )

    def test_run_checks_reports_ready_when_required_records_exist(self):
        runner = fake_runner_factory({
            ("MX", "gcagochina.com"): "10 mail.example.com.\n",
            ("TXT", "gcagochina.com"): '"v=spf1 include:_spf.example.com -all"\n"google-site-verification=abc"\n',
            ("TXT", "_dmarc.gcagochina.com"): '"v=DMARC1; p=none; rua=mailto:support@gcagochina.com"\n',
            ("TXT", "selector1._domainkey.gcagochina.com"): '"v=DKIM1; k=rsa; p=abc123"\n',
        })

        result = run_checks(dkim_selector="selector1", runner=runner)

        self.assertTrue(result["readyForBaseScanEmailEvidence"])
        self.assertEqual(result["targetMailbox"], "support@gcagochina.com")
        self.assertEqual(result["checks"]["mx"]["status"], "present")
        self.assertEqual(result["checks"]["spf"]["status"], "present")
        self.assertEqual(result["checks"]["dmarc"]["status"], "present")
        self.assertEqual(result["checks"]["dkim"]["status"], "present")
        self.assertEqual(result["missingOrBlockedChecks"], [])
        self.assertTrue(result["boundaries"]["readOnlyDnsCheck"])
        self.assertFalse(result["boundaries"]["sendsEmail"])
        self.assertFalse(result["boundaries"]["submitsBaseScanRequest"])
        self.assertFalse(result["boundaries"]["touchesWalletOrContract"])

    def test_run_checks_requires_dkim_selector_before_ready(self):
        runner = fake_runner_factory({
            ("MX", "gcagochina.com"): "10 mail.example.com.\n",
            ("TXT", "gcagochina.com"): '"v=spf1 include:_spf.example.com -all"\n',
            ("TXT", "_dmarc.gcagochina.com"): '"v=DMARC1; p=none"\n',
        })

        result = run_checks(runner=runner)

        self.assertFalse(result["readyForBaseScanEmailEvidence"])
        self.assertEqual(result["checks"]["dkim"]["status"], "selector-required")
        self.assertIn("dkim", result["missingOrBlockedChecks"])

    def test_run_checks_flags_multiple_spf_records(self):
        runner = fake_runner_factory({
            ("MX", "gcagochina.com"): "10 mail.example.com.\n",
            ("TXT", "gcagochina.com"): '"v=spf1 include:a.example -all"\n"v=spf1 include:b.example -all"\n',
            ("TXT", "_dmarc.gcagochina.com"): '"v=DMARC1; p=none"\n',
            ("TXT", "selector1._domainkey.gcagochina.com"): '"v=DKIM1; p=abc"\n',
        })

        result = run_checks(dkim_selector="selector1", runner=runner)

        self.assertFalse(result["readyForBaseScanEmailEvidence"])
        self.assertEqual(result["checks"]["spf"]["status"], "multiple")
        self.assertIn("spf", result["missingOrBlockedChecks"])

    def test_run_checks_rejects_wrong_domain_mailbox(self):
        with self.assertRaises(DomainEmailDnsError):
            run_checks(mailbox="support@example.com", runner=lambda command, **kwargs: FakeCompleted())

    def test_main_json_output_does_not_require_ready_by_default(self):
        records = {
            ("MX", "gcagochina.com"): "",
            ("TXT", "gcagochina.com"): "",
            ("TXT", "_dmarc.gcagochina.com"): "",
        }
        runner = fake_runner_factory(records)

        # Exercise serialization through the core result shape used by main.
        result = run_checks(runner=runner)
        serialized = json.dumps(result)
        self.assertIn("gca-domain-email-dns-check", serialized)
        self.assertFalse(result["readyForBaseScanEmailEvidence"])

    def test_main_rejects_bad_domain(self):
        with redirect_stderr(StringIO()):
            self.assertEqual(main(["--domain", "https://gcagochina.com"]), 2)


if __name__ == "__main__":
    unittest.main()
