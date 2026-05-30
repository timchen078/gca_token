# GCA Domain Email Evidence Checklist

- Status: `blocked-until-domain-email-evidence-collected`
- Current public email: `support@gcagochina.com`
- Target domain email: `support@gcagochina.com`
- Evidence directory: `launch/domain_email_evidence`
- Evidence directory ignored by git: `true`

## Required Evidence Files

- `domain-email-provider-active.png`: Mail provider dashboard shows support@gcagochina.com as verified or active. Keep private: `true`.
- `domain-email-dns-mx-spf-dkim-dmarc.txt`: MX, SPF, DKIM, and DMARC lookup proof is saved after propagation. Keep private: `true`.
- `domain-email-inbound-test.png`: Inbound test from Gmail or Outlook to support@gcagochina.com is received. Keep private: `true`.
- `domain-email-outbound-test.png`: Outbound reply from support@gcagochina.com shows the visible domain sender. Keep private: `true`.
- `support-page-domain-email.png`: Updated support page shows the same domain email used in the BaseScan form. Keep private: `true`.

## Steps In Order

1. Choose a full mailbox provider that can receive and send as support@gcagochina.com.
2. Initialize the local evidence directory with the evidence packet tool.
3. Save provider proof showing support@gcagochina.com active or verified.
4. Add provider MX, SPF, DKIM, and DMARC DNS records exactly as supplied by the provider.
5. Save DNS proof after the read-only DNS checker reports readyForBaseScanEmailEvidence true.
6. Send an inbound test from Gmail or Outlook to support@gcagochina.com and save the received-message proof.
7. Reply from support@gcagochina.com back to Gmail or Outlook and save visible-sender proof.
8. Switch public support/BaseScan email values only after DNS and mail-flow evidence are complete.
9. Save support-page-domain-email.png showing the same domain email used in the BaseScan form.
10. Build launch/domain_email_evidence_packet.json and run the BaseScan resubmission preflight.

## Commands

- `initEvidenceDirectory`: `python3 tools/build_domain_email_evidence_packet.py --init-evidence-dir --evidence-dir launch/domain_email_evidence`
- `dnsCheck`: `python3 tools/check_domain_email_dns.py --domain gcagochina.com --mailbox support --dkim-selector <provider-selector> --json`
- `buildEvidencePacket`: `python3 tools/build_domain_email_evidence_packet.py --dkim-selector <provider-selector> --evidence-dir launch/domain_email_evidence --website-email-updated --output-json launch/domain_email_evidence_packet.json --output-md launch/domain_email_evidence_packet.md --json`
- `finalPreflight`: `python3 tools/check_basescan_resubmission_readiness.py --json --require-ready`

## Stop Conditions

- support@gcagochina.com cannot receive external email.
- support@gcagochina.com cannot send authenticated replies with the visible sender set to the domain email.
- MX/SPF/DKIM/DMARC DNS checks stop reporting ready.
- Any required evidence file is missing.
- Public support/BaseScan files still publish support@gcagochina.com after the switch.
- BaseScan resubmission preflight reports readyForBaseScanResubmission false.

## Boundaries

- This checklist does not write DNS records.
- This checklist does not send email.
- This checklist does not submit BaseScan requests.
- This checklist does not touch wallets, contracts, liquidity, or private keys.
- Private mailbox screenshots and proof files must stay in the git-ignored evidence directory.
