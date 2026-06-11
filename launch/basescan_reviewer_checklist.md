# GCA BaseScan Reviewer Checklist

- Status: `ready-for-owner-review`
- Ready for clean resubmission: `true`
- Latest return notice: `2026-05-23`
- Final submission package: `2026-06-06T11:10:54Z`
- Daily public status: `2026-06-11T12:01:21Z`
- Current official email: `support@gcagochina.com`
- Target domain email: `support@gcagochina.com`

## Checklist

| Item | Status | Evidence | Action |
| --- | --- | --- | --- |
| Website accessible and safe to visit | `implemented` | Public HTTPS website, start page, verification page, sitemap, and robots file are published and checked by tools/check_public_site.py. | Keep public site checks passing before every resubmission. |
| Clear token and project information | `implemented` | About, status, whitepaper, product, trust, and reviewer pages describe GCA without claiming approval, audit completion, or guaranteed market outcomes. | Use the readable pages first; raw JSON only when a reviewer asks for machine-readable data. |
| No obvious placeholders or broken reviewer links | `implemented-with-automated-check` | The public site checker validates canonical identity, current GCA/USDT route, public pages, raw JSON routing, sitemap, and robots. | Run .venv/bin/python tools/check_public_site.py after each public-material change. |
| Founder and team transparency | `implemented-official-domain-equivalent` | Tim Chen is published on the team page and standalone official-domain professional profile with GitHub, X, Telegram, and role scope. | Add LinkedIn only if BaseScan specifically requires a third-party social-network profile. |
| Sender email matches project domain | `implemented-domain-email-evidence-ready` | The official project-domain mailbox support@gcagochina.com is active, public DNS records pass MX/SPF/DKIM/DMARC checks, inbound and outbound tests are archived privately, and public support/BaseScan materials publish the same domain email. | Submit one clean BaseScan token-profile update from support@gcagochina.com, attaching the public evidence links and retaining private mailbox screenshots for reviewer follow-up. |
| Verified source and fixed-supply token facts | `implemented` | BaseScan source verification and deployer-wallet ownership verification are complete; the contract has fixed supply and no post-deployment mint function. | Keep the chain as Base Mainnet / chainId 8453 and contract address unchanged. |
| Logo, brand kit, and whitepaper | `implemented` | SVG/PNG logos, social card, brand kit, and whitepaper are published over HTTPS. | Use the same 32x32 SVG logo URL and whitepaper URL in BaseScan. |
| Official social links and market route | `implemented` | Telegram, X, GitHub, and the official Base Mainnet GCA/USDT market route are published. GeckoTerminal token information is approved. | Keep all public materials pointed to the GCA/USDT route, not the older WETH pilot pool. |

## Preflight Commands

- `python3 tools/check_domain_email_dns.py --domain gcagochina.com --mailbox support --dkim-selector <provider-selector> --json`
- `python3 tools/build_domain_email_evidence_packet.py --dkim-selector <provider-selector> --evidence-dir launch/domain_email_evidence --website-email-updated --output-json launch/domain_email_evidence_packet.json --output-md launch/domain_email_evidence_packet.md`
- `python3 tools/build_domain_email_switch_plan.py --json`
- `python3 tools/check_basescan_resubmission_readiness.py --json --require-ready`
- `python3 tools/build_basescan_submission_package.py --json --require-ready --output-json launch/basescan_final_submission_package.json --output-md launch/basescan_final_submission_package.md`

## Boundaries

- This checklist does not submit BaseScan requests.
- This checklist does not send email, write DNS, sign wallet messages, or touch wallets/contracts.
