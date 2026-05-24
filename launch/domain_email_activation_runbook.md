# GCA Domain Email Activation Runbook

This runbook is the owner-side checklist for activating a project-domain mailbox before the next BaseScan token profile resubmission. It does not change contracts, wallets, token supply, liquidity, or custody.

## Current State

- Domain: `gcagochina.com`
- Current public contact: `GCAgochina@outlook.com`
- Target BaseScan-ready mailbox: `support@gcagochina.com`
- Current public status: domain email setup plan published, mailbox not active yet
- Public plan: `https://gcagochina.com/domain-email.html`
- Public JSON: `https://gcagochina.com/domain-email.json`
- DNS checker: `tools/check_domain_email_dns.py`

Do not claim that `support@gcagochina.com` is active until inbound mail, outbound authenticated sending, and public DNS authentication checks have all passed.

## Activation Steps

1. Create the mailbox at the chosen email provider as `support@gcagochina.com`.
2. Copy the provider's DNS records into the DNS host for `gcagochina.com`.
3. Keep only one SPF TXT record for the root domain. If another SPF record exists, merge provider includes into a single `v=spf1 ...` value.
4. Add the provider's DKIM record. Record the selector name exactly as shown by the provider.
5. Add DMARC at `_dmarc.gcagochina.com`. Monitoring mode is acceptable for first activation.
6. Wait for DNS propagation and provider verification.
7. Run the read-only DNS checker:

```bash
python3 tools/check_domain_email_dns.py --domain gcagochina.com --mailbox support --dkim-selector <provider-selector> --json
```

8. Confirm the JSON output has `"readyForBaseScanEmailEvidence": true` and an empty `missingOrBlockedChecks` array.
9. Send an inbound test from Gmail or Outlook to `support@gcagochina.com`.
10. Reply from `support@gcagochina.com` back to Gmail or Outlook and confirm the visible sender is the domain mailbox.
11. Save the activation evidence packet before changing public BaseScan form values.

## Local Evidence Packet Builder

After DNS and manual email tests are complete, build a local packet for owner records:

```bash
python3 tools/build_domain_email_evidence_packet.py \
  --dkim-selector <provider-selector> \
  --provider-active domain-email-provider-active.png \
  --dns-proof domain-email-dns-mx-spf-dkim-dmarc.txt \
  --inbound-test domain-email-inbound-test.png \
  --outbound-test domain-email-outbound-test.png \
  --support-page-proof support-page-domain-email.png \
  --website-email-updated \
  --output-json launch/domain_email_evidence_packet.json \
  --output-md launch/domain_email_evidence_packet.md
```

The packet builder marks `readyForBaseScanResubmission` as true only when DNS is ready, all five evidence references are present, and the website email has been switched to the target domain email. It does not send email, submit BaseScan requests, write to DNS, or touch wallets/contracts.

Before opening the BaseScan form, run the final read-only preflight:

```bash
python3 tools/check_basescan_resubmission_readiness.py --json --require-ready
```

Only proceed when the preflight reports `readyForBaseScanResubmission` as true. The preflight checks the BaseScan values packet, domain email evidence packet, and public reviewer URLs; it does not submit anything.

## Evidence Packet

Save these owner records before the next BaseScan submission:

- `domain-email-provider-active.png`: provider dashboard showing `support@gcagochina.com` as active or verified.
- `domain-email-dns-mx-spf-dkim-dmarc.txt`: output from the DNS checker or equivalent DNS lookup proof.
- `domain-email-inbound-test.png`: inbound message received at `support@gcagochina.com`.
- `domain-email-outbound-test.png`: outbound reply from `support@gcagochina.com` showing the visible sender.
- `support-page-domain-email.png`: official support page showing the same domain email used in the BaseScan form.

The DNS checker is read-only. It does not send email, submit BaseScan requests, write files by itself, print secrets, or touch wallets/contracts.
The packet builder writes only local owner evidence files when `--output-json` or `--output-md` is provided.

## Public Site Switch Gate

Only after the evidence packet is ready:

1. Replace public contact references from `GCAgochina@outlook.com` to `support@gcagochina.com` where appropriate.
2. Update `site/support.html`, `site/support.json`, `site/zh-support.html`, `site/register.html`, `site/members.html`, `site/project.json`, `site/listing-kit.html`, `site/basescan-remediation.html`, `site/basescan-remediation.json`, `site/external-reviews.json`, `site/reviewer-kit.json`, and BaseScan launch values.
3. Re-run JSON validation, the domain email DNS check, the public site checker, and the full test suite.
4. Submit the next BaseScan profile update from the same domain email where possible.

## BaseScan Submission Gate

Do not submit another clean BaseScan token update until all of these are true:

- `support@gcagochina.com` receives external mail.
- `support@gcagochina.com` sends authenticated external mail.
- MX, SPF, DMARC, and DKIM checks pass through `tools/check_domain_email_dns.py`.
- The public website shows the same domain email as the BaseScan sender/contact email.
- Tim Chen professional profile remains published at `https://gcagochina.com/tim-chen.html`.
- BaseScan remediation links and official market links still load.

## Failure Handling

- If MX is missing, fix inbound routing at the DNS host or provider dashboard.
- If SPF is missing, add the provider TXT record.
- If SPF is marked `multiple`, merge SPF values into one root-domain TXT record.
- If DMARC is missing, add `_dmarc.gcagochina.com`.
- If DKIM is missing, check the provider selector and DNS host record type/value.
- If outbound mail lands in spam, keep the public site on `GCAgochina@outlook.com` until delivery is stable.

## Public Claim Boundary

Safe to say:

- GCA has published a domain email setup plan.
- A working `gcagochina.com` domain email is required before the next clean BaseScan token profile resubmission.
- The DNS checker is a read-only operator tool for MX, SPF, DMARC, and DKIM readiness.

Do not say:

- `support@gcagochina.com` is active before tests pass.
- BaseScan has approved or published the token profile before BaseScan actually publishes it.
- The DNS checker is a third-party audit or security approval.
