# GCA Domain Email Activation Runbook

This runbook is the owner-side checklist for activating a project-domain mailbox before the next BaseScan token profile resubmission. It does not change contracts, wallets, token supply, liquidity, or custody.

## Current State

- Domain: `gcagochina.com`
- Current public contact: `GCAgochina@outlook.com`
- Target BaseScan-ready mailbox: `support@gcagochina.com`
- Current public status: domain email setup plan published, mailbox not active yet
- Public plan: `https://gcagochina.com/domain-email.html`
- Public JSON: `https://gcagochina.com/domain-email.json`
- Public evidence checklist: `https://gcagochina.com/domain-email-evidence.html`
- Public evidence checklist JSON: `https://gcagochina.com/domain-email-evidence.json`
- DNS checker: `tools/check_domain_email_dns.py`

Do not claim that `support@gcagochina.com` is active until inbound mail, outbound authenticated sending, and public DNS authentication checks have all passed.

## Latest Read-Only DNS Snapshot (2026-05-30)

Command run:

```bash
python3 tools/check_domain_email_dns.py --domain gcagochina.com --mailbox support --json
```

Checked at: `2026-05-30T08:13:47Z`.

Result: `readyForBaseScanEmailEvidence` is false. Public DNS currently reports `missingOrBlockedChecks` as `["mx", "spf", "dmarc", "dkim"]`: MX is missing, SPF is missing, DMARC is missing, and DKIM is still `selector-required` because the mail provider selector has not been supplied.

Next owner action: create `support@gcagochina.com` at the chosen mail provider, add the provider MX/SPF/DMARC/DKIM records, rerun the checker with `--dkim-selector <provider-selector>`, then collect inbound and outbound message evidence.

## Owner Action Packet

Use this short order when doing the actual mailbox work. Stop immediately if any item cannot be proven.

1. Enable a full mailbox for `support@gcagochina.com` that receives external mail and sends authenticated replies from the same address.
2. Save `domain-email-provider-active.png` showing the mailbox as active or verified in the provider dashboard.
3. Keep `https://gcagochina.com/domain-email-evidence.html` open while collecting owner proof files so public checklist status and private evidence stay aligned.
4. Build the DNS entry packet with the provider's exact MX, SPF, DKIM, and DMARC values before entering records.
5. Enter MX, one merged SPF TXT record, DKIM with the exact provider selector, and DMARC at `_dmarc`.
6. Run `python3 tools/check_domain_email_dns.py --domain gcagochina.com --mailbox support --dkim-selector <provider-selector> --json` and save `domain-email-dns-mx-spf-dkim-dmarc.txt`.
7. Save inbound and outbound mail evidence as `domain-email-inbound-test.png` and `domain-email-outbound-test.png`.
8. Switch public support/BaseScan email values only after evidence is complete, then save `support-page-domain-email.png`.
9. Run `python3 tools/check_basescan_resubmission_readiness.py --json --require-ready`. BaseScan can be resubmitted only when the preflight reports `readyForBaseScanResubmission` as true.

Stop conditions: any required evidence file is missing; DNS is not ready; outbound visible sender is not `support@gcagochina.com`; public files still publish `GCAgochina@outlook.com` after the switch; or BaseScan preflight fails.

## Mail Provider Selection

Choose a full hosted mailbox or mail service, not receive-only forwarding alone. BaseScan's practical requirement is that the website contact email, sender email, and domain ownership path match. That means the mailbox must receive external mail and send authenticated outbound mail as `support@gcagochina.com`.

Minimum acceptable provider capability:

- Inbound mail for `support@gcagochina.com`
- Outbound sending or replies where the visible sender is `support@gcagochina.com`
- MX records for inbound routing
- SPF, DKIM, and DMARC records for sender authentication
- A provider dashboard or mail UI that can be screenshotted for owner evidence

Cloudflare Email Routing can be useful for inbound forwarding, but receive-only forwarding by itself is not enough for the next clean BaseScan resubmission because it does not prove outbound sender alignment. If using Cloudflare, pair it with a real outbound sending path or choose a full mailbox provider instead.

Common full-mailbox paths include Google Workspace, Microsoft 365, Zoho Mail, or another hosted mailbox provider. The brand is less important than passing the evidence gates: DNS ready, inbound test received, outbound reply sent from the domain email, and public site email aligned.

## Provider Decision Matrix

Before buying a mailbox plan, generate the local provider decision matrix:

```bash
python3 tools/build_domain_email_provider_matrix.py --markdown
```

For a copyable owner artifact:

```bash
python3 tools/build_domain_email_provider_matrix.py \
  --output-json launch/domain_email_provider_matrix.json \
  --output-md launch/domain_email_provider_matrix.md
```

Use the matrix to separate full mailbox options from incomplete paths. The recommended first check is Zoho Mail or an equivalent low-cost hosted mailbox, only if it creates `support@gcagochina.com`, receives external mail, sends authenticated outbound mail, and provides MX, SPF, DKIM, and DMARC setup. Google Workspace and Microsoft 365 are also acceptable if those gates pass. Cloudflare Email Routing only, or send-only SMTP/API without inbound mail for `support@gcagochina.com`, is not enough by itself for a clean BaseScan resubmission.

The matrix does not fetch live prices, write DNS records, send email, submit BaseScan requests, store secrets, or touch wallets/contracts.

## DNS Entry Packet Builder

After the provider dashboard shows the exact DNS records, generate a local copyable packet before entering records at the DNS host:

```bash
python3 tools/build_domain_email_dns_entry_packet.py \
  --provider <provider-name> \
  --mx "10 <provider-mx>" \
  --spf "v=spf1 include:<provider> ~all" \
  --dkim-selector <provider-selector> \
  --dkim-type TXT \
  --dkim-value "<provider-dkim-value>" \
  --dmarc "v=DMARC1; p=none;" \
  --output-json launch/domain_email_dns_entry_packet.json \
  --output-md launch/domain_email_dns_entry_packet.md
```

Use the provider's exact values. The packet builder validates basic format, creates `launch/domain_email_dns_entry_packet.json` and `launch/domain_email_dns_entry_packet.md`, and still does not write DNS records, send email, submit BaseScan requests, store secrets, or touch wallets/contracts.

## DNS Entry Worksheet

Use this worksheet when the mail provider shows DNS setup instructions. Copy provider values exactly; do not guess mail server hosts, DKIM selectors, verification strings, or record types.

| Record | Type | Name / Host | Value Source | Ready Check | Common Mistake |
| --- | --- | --- | --- | --- | --- |
| MX | `MX` | `@` or `gcagochina.com` | Provider mail server host and priority | `tools/check_domain_email_dns.py` reports MX present | Adding MX under `support.gcagochina.com` instead of the root domain |
| SPF | `TXT` | `@` or `gcagochina.com` | Provider SPF string merged into one root-domain `v=spf1` TXT record | Checker reports a single SPF record | Publishing multiple SPF TXT records |
| DKIM | Provider-required `TXT` or `CNAME` | Provider selector, usually `<provider-selector>._domainkey` | Provider DKIM value and exact selector | Checker reports DKIM present with `--dkim-selector <provider-selector>` | Guessing the selector or omitting `_domainkey` |
| DMARC | `TXT` | `_dmarc` | Provider recommendation or starter monitoring value such as `v=DMARC1; p=none;` | Checker reports DMARC present at `_dmarc.gcagochina.com` | Adding DMARC at the root domain |

After records propagate, save provider status, DNS lookup proof, inbound mail proof, outbound mail proof, and updated support-page proof before BaseScan resubmission.

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
11. Cross-check the public evidence checklist at `https://gcagochina.com/domain-email-evidence.html`.
12. Save the activation evidence packet before changing public BaseScan form values.

## Local Evidence Packet Builder

The public-safe checklist for this stage is committed at:

- `launch/domain_email_evidence_checklist.md`
- `launch/domain_email_evidence_checklist.json`

It lists the five proof files to collect and the stop conditions without storing private mailbox screenshots in git.

Initialize the ignored local evidence directory first:

```bash
python3 tools/build_domain_email_evidence_packet.py \
  --init-evidence-dir \
  --evidence-dir launch/domain_email_evidence
```

After DNS and manual email tests are complete, save the five proof files under `launch/domain_email_evidence`, then build a local packet for owner records:

```bash
python3 tools/build_domain_email_evidence_packet.py \
  --dkim-selector <provider-selector> \
  --evidence-dir launch/domain_email_evidence \
  --website-email-updated \
  --output-json launch/domain_email_evidence_packet.json \
  --output-md launch/domain_email_evidence_packet.md
```

The packet builder marks `readyForBaseScanResubmission` as true only when DNS is ready, all five evidence references are present, and the website email has been switched to the target domain email. It does not send email, submit BaseScan requests, write to DNS, or touch wallets/contracts.

Before opening the BaseScan form, run the final read-only preflight:

```bash
python3 tools/check_basescan_resubmission_readiness.py --json --require-ready
```

Only proceed when the preflight reports `readyForBaseScanResubmission` as true. The preflight checks the BaseScan values packet, domain email evidence packet, public email switch alignment, domain email snapshot alignment, and public reviewer URLs; it does not submit anything.

After the preflight passes, generate the final copyable BaseScan draft:

```bash
python3 tools/build_basescan_submission_package.py --json --require-ready --output-json launch/basescan_final_submission_package.json --output-md launch/basescan_final_submission_package.md
```

The final draft builder still does not submit the form. It only produces the local package the owner can copy into one clean BaseScan update. The package includes copy/paste blocks for the reviewer comment, BaseScan basic information, reviewer evidence links, and market/supply context. If any preflight gate is still blocked, the reviewer comment is clearly marked `DRAFT ONLY - DO NOT SUBMIT BASESCAN YET.`.

## Public Email Switch Planner

Before replacing `GCAgochina@outlook.com` across public files, run the read-only switch planner:

```bash
python3 tools/build_domain_email_switch_plan.py --json
```

For a copyable owner artifact:

```bash
python3 tools/build_domain_email_switch_plan.py \
  --output-json launch/domain_email_switch_plan.json \
  --output-md launch/domain_email_switch_plan.md
```

To preview exact old-email replacements before editing public files:

```bash
python3 tools/build_domain_email_switch_plan.py --patch
```

For a saved diff preview:

```bash
python3 tools/build_domain_email_switch_plan.py \
  --output-patch launch/domain_email_switch_preview.patch
```

The planner scans public site files, launch materials, docs, and the member backend contact constant for old-email references. The patch preview is an exact replacement diff only and is not applied by the tool. It does not edit files, send email, write DNS records, submit BaseScan requests, or touch wallets/contracts. Use it after the evidence packet and BaseScan preflight are ready, then update public support pages first, structured project/listing/reviewer JSON second, BaseScan launch values third, and platform reply templates last.

After the manual switch is done, run the read-only public switch checker:

```bash
python3 tools/check_domain_email_public_switch.py --json --require-switched
```

The checker uses the critical file list from `site/domain-email.json` and blocks if any listed public/support/BaseScan file still contains `GCAgochina@outlook.com`, if the target domain email is missing, or if a critical file is missing. It does not edit files, send email, write DNS records, submit BaseScan requests, or touch wallets/contracts.
Before reusing platform copy after a new DNS check, run the read-only snapshot alignment checker:

```bash
python3 tools/check_domain_email_snapshot_alignment.py --json --require-aligned
```

This checker compares public site, launch, and docs materials against the canonical `liveDnsSnapshot` in `site/domain-email.json`; it blocks stale DNS snapshot dates or monitored files that no longer cite the current snapshot. It does not edit files, send email, write DNS records, submit BaseScan requests, or touch wallets/contracts.
The same public switch gate and snapshot alignment gate are now included in `tools/check_basescan_resubmission_readiness.py` and `tools/build_basescan_submission_package.py`, so the final BaseScan package cannot be marked ready while critical files still publish the old Outlook email or public packets cite stale DNS snapshot dates.

## Evidence Packet

Save these owner records before the next BaseScan submission:

Save all five files in `launch/domain_email_evidence`:

- `launch/domain_email_evidence/domain-email-provider-active.png`: provider dashboard showing `support@gcagochina.com` as active or verified.
- `launch/domain_email_evidence/domain-email-dns-mx-spf-dkim-dmarc.txt`: output from the DNS checker or equivalent DNS lookup proof.
- `launch/domain_email_evidence/domain-email-inbound-test.png`: inbound message received at `support@gcagochina.com`.
- `launch/domain_email_evidence/domain-email-outbound-test.png`: outbound reply from `support@gcagochina.com` showing the visible sender.
- `launch/domain_email_evidence/support-page-domain-email.png`: official support page showing the same domain email used in the BaseScan form.

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
