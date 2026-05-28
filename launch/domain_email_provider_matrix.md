# GCA Domain Email Provider Decision Matrix

- Status: `choose-full-mailbox-before-basescan-resubmission`
- Current public email: `GCAgochina@outlook.com`
- Target domain email: `support@gcagochina.com`
- No live pricing: `true`

## Decision Rule

Choose the lowest-cost full mailbox path that can receive external mail, send authenticated external mail, publish MX/SPF/DKIM/DMARC, and produce evidence for support@gcagochina.com.

Recommended default: Start by checking a low-cost full hosted mailbox such as Zoho Mail or an equivalent provider, then use Google Workspace or Microsoft 365 if you prefer those ecosystems.

## Provider Options

| Provider path | Fit | Why |
| --- | --- | --- |
| Zoho Mail or equivalent low-cost hosted mailbox | `recommended-first-check` | Often suitable when the owner wants a lower-cost full mailbox path, provided it creates a real mailbox and publishes MX, SPF, DKIM, and DMARC. |
| Google Workspace | `acceptable-full-mailbox` | Acceptable if the custom domain is verified and the mailbox can send and receive as support@gcagochina.com with MX, SPF, DKIM, and DMARC configured. |
| Microsoft 365 | `acceptable-full-mailbox` | Acceptable if the custom domain is verified and Outlook sends and receives as support@gcagochina.com with the required mail DNS records. |
| Cloudflare Email Routing only | `not-sufficient-alone` | Useful for inbound forwarding, but receive-only routing does not prove outbound sender alignment for a clean BaseScan resubmission. |
| Outbound SMTP/API only | `not-sufficient-alone` | Send-only services can help with authenticated outbound mail, but BaseScan also needs a contact path that receives external mail at the same domain address. |

## Records To Collect

- `MX`: copy provider host, value, and priority exactly (do not guess).
- `SPF`: copy provider SPF include and merge into one root-domain v=spf1 record (do not guess).
- `DKIM`: copy provider selector, record type, host, and value exactly (do not guess).
- `DMARC`: add _dmarc.gcagochina.com, starting with monitoring mode if needed (use provider guidance or safe starter policy).

## Owner Questions Before Purchase

- Can the provider create support@gcagochina.com as a real mailbox or send-as identity?
- Can the provider receive external mail at support@gcagochina.com?
- Can the provider send replies where the visible sender is support@gcagochina.com?
- Does the provider expose MX, SPF, DKIM, and DMARC setup steps for custom domains?
- Can the owner access DNS for gcagochina.com to add those records?

## Commands After Provider Setup

- `python3 tools/check_domain_email_dns.py --domain gcagochina.com --mailbox support --dkim-selector <provider-selector> --json`
- `python3 tools/build_domain_email_evidence_packet.py --dkim-selector <provider-selector> --evidence-dir launch/domain_email_evidence --website-email-updated --output-json launch/domain_email_evidence_packet.json --output-md launch/domain_email_evidence_packet.md`
- `python3 tools/build_domain_email_switch_plan.py --json`
- `python3 tools/check_basescan_resubmission_readiness.py --json --require-ready`
- `python3 tools/build_basescan_submission_package.py --json --require-ready --output-json launch/basescan_final_submission_package.json --output-md launch/basescan_final_submission_package.md`

## Boundaries

- This matrix does not fetch live prices.
- This matrix does not write DNS records, send email, submit BaseScan requests, store secrets, or touch wallets/contracts.
