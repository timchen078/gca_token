# BaseScan Token Profile Remediation Package

This package records the current BaseScan token information remediation state. The previous request was submitted on 2026-05-09, returned by BaseScan as information-insufficient on 2026-05-13, resubmitted on 2026-05-13, and returned again as information-insufficient on 2026-05-23.

## Required Status

- Network: Base Mainnet
- Chain ID: 8453
- Contract: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- Token name: GCA
- Token symbol: GCA
- Decimals: 18
- Total supply: 1,000,000,000 GCA
- Contract source: verified on BaseScan
- Deployer-wallet ownership: previously verified; sign again if BaseScan asks
- BaseScan profile status: ready-for-owner-resubmission
- Latest return notice: 2026-05-23
- Final owner package: generated 2026-06-06T11:10:54Z
- Latest daily public status: refreshed 2026-06-06T12:13:21Z
- Next submission ready: yes; Tim Chen professional profile is published, the 2026-05-30 DNS snapshot shows MX/SPF/DKIM/DMARC present, readyForBaseScanEmailEvidence is true, the BaseScan Handoff copy blocks are ready, and the daily public status snapshot confirms readyForBaseScanResubmission is true

## Official Links

- Website: `https://gcagochina.com/`
- Verify page: `https://gcagochina.com/verify.html`
- Project status: `https://gcagochina.com/status.html`
- Team profile: `https://gcagochina.com/team.html`
- Tim Chen professional profile: `https://gcagochina.com/tim-chen.html`
- Tim Chen profile data: `https://gcagochina.com/tim-chen.json`
- Domain email setup plan: `https://gcagochina.com/domain-email.html`
- Domain email setup JSON and evidence packet: `https://gcagochina.com/domain-email.json`
- Domain email DNS worksheet: `https://gcagochina.com/domain-email.html#worksheetTitle`
- Domain email activation evidence: `https://gcagochina.com/domain-email.html#evidenceTitle`
- Domain email evidence checklist: `https://gcagochina.com/domain-email-evidence.html`
- Domain email evidence checklist JSON: `https://gcagochina.com/domain-email-evidence.json`
- Domain email DNS snapshot: `https://gcagochina.com/domain-email.html#snapshotTitle`
- BaseScan remediation: `https://gcagochina.com/basescan-remediation.html`
- BaseScan remediation JSON: `https://gcagochina.com/basescan-remediation.json`
- BaseScan preflight gate: `https://gcagochina.com/basescan-preflight.html`
- BaseScan preflight JSON: `https://gcagochina.com/basescan-preflight.json`
- BaseScan Handoff: `https://gcagochina.com/basescan-handoff.html`
- BaseScan Handoff JSON: `https://gcagochina.com/basescan-handoff.json`
- Daily public status: `https://gcagochina.com/daily-status.html`
- Daily public status JSON: `https://gcagochina.com/daily-status.json`
- Public GitHub repository: `https://github.com/timchen078/gca_token`
- Listing kit: `https://gcagochina.com/listing-kit.html`
- Brand kit: `https://gcagochina.com/brand-kit.html`
- Brand kit JSON: `https://gcagochina.com/brand-kit.json`
- Community kit: `https://gcagochina.com/community.html`
- Community JSON: `https://gcagochina.com/community.json`
- Product spec: `https://gcagochina.com/product.html`
- Credits catalog: `https://gcagochina.com/credits.html`
- Release gates: `https://gcagochina.com/release-gates.html`
- External review status: `https://gcagochina.com/external-reviews.html`
- Project JSON: `https://gcagochina.com/project.json`
- Token list JSON: `https://gcagochina.com/tokenlist.json`
- Well-known token identity: `https://gcagochina.com/.well-known/gca-token.json`
- Whitepaper: `https://gcagochina.com/whitepaper.html`
- Logo SVG: `https://gcagochina.com/assets/gca-logo.svg`
- Logo PNG: `https://gcagochina.com/assets/gca-logo.png`
- Official Telegram: `https://t.me/gcagochinaofficial`
- Official X: `https://x.com/GCAAIGoChina`
- Official email: `support@gcagochina.com`

## Owner-Required Fixes Before The Next Submission

1. Use the published domain email setup plan at `https://gcagochina.com/domain-email.html` and the DNS Entry Worksheet at `https://gcagochina.com/domain-email.html#worksheetTitle`; keep the working project-domain email `support@gcagochina.com` active for BaseScan reviewer replies.
2. Follow `launch/domain_email_activation_runbook.md`.
3. Keep the current 2026-05-30 DNS evidence available: MX/SPF/DKIM/DMARC present.
4. Run `python3 tools/check_domain_email_dns.py --domain gcagochina.com --mailbox support --dkim-selector <provider-selector> --json` and confirm `readyForBaseScanEmailEvidence` is true.
5. Archive the domain email activation evidence packet: provider active screenshot, MX/SPF/DKIM/DMARC lookup proof, inbound test, outbound test, and updated support-page screenshot.
6. Confirm the public support, about, team, BaseScan Handoff, and daily status pages still publish `support@gcagochina.com`.
7. Submit to BaseScan from the domain email `support@gcagochina.com`, and keep previous contact emails only as historical owner context if needed.
8. Include the Tim Chen professional profile URL `https://gcagochina.com/tim-chen.html`, the team anchor `https://gcagochina.com/team.html#tim-chen`, the public source repository `https://github.com/timchen078/gca_token`, the BaseScan Handoff `https://gcagochina.com/basescan-handoff.html`, and the daily status snapshot `https://gcagochina.com/daily-status.html` in the next submission. Add LinkedIn later only if BaseScan specifically requires a third-party social-network profile.
9. Re-run the public site checker after any public evidence change and before submitting.
10. Run the read-only BaseScan preflight checker before opening the form:

```bash
python3 tools/check_basescan_resubmission_readiness.py --json --require-ready
```

The preflight reports `readyForBaseScanResubmission: true`, so the owner may send one clean resubmission. It validates the local BaseScan values packet, the domain email evidence packet, and reviewer URLs only; it does not submit BaseScan forms, send email, write DNS records, or touch wallets/contracts.

11. After the preflight passes, generate the final local submission draft:

```bash
python3 tools/build_basescan_submission_package.py \
  --json \
  --require-ready \
  --output-json launch/basescan_final_submission_package.json \
  --output-md launch/basescan_final_submission_package.md
```

The submission package builder is also gated by the same preflight. It writes a local JSON/Markdown draft only and does not submit BaseScan forms, sign wallet messages, send email, write DNS records, or touch wallets/contracts.

The final package generated at `2026-06-06T11:10:54Z` includes copy/paste blocks for the BaseScan reviewer comment, basic information, evidence links, market route, and supply context. The daily public status snapshot refreshed at `2026-06-06T12:13:21Z` confirms the public site check, public registration API check, and BaseScan preflight status are passing. If the preflight is still blocked in a future run, the reviewer comment begins with `DRAFT ONLY - DO NOT SUBMIT BASESCAN YET.` so the owner does not accidentally paste an unready package into the live form.

## Description

Short description:

```text
GCA, short for Go China Access, is a fixed-supply ERC-20 token on Base Mainnet.
```

Long description:

```text
GCA is a fixed-supply ERC-20 token deployed on Base Mainnet. GCA currently stands for Go China Access, a concept-stage community direction focused on the Go China macro narrative, bilingual Web3 education, public market research, and planned access to non-custodial quant risk tools. The planned access and membership layer is intended for research reports, risk-warning credits, backtests, ENTRY_READY signal review, position-size calculators, subscription discounts, and risk-control training. The contract created 1,000,000,000 GCA at deployment and includes no post-deployment minting, burning, taxes, blacklist, or admin controls.
```

## Market And Supply Context

- Official public market route: GCA/USDT on Base Mainnet
- DEX: Uniswap v4
- Pool: `0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- GeckoTerminal: `https://www.geckoterminal.com/base/pools/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- DEX Screener: `https://dexscreener.com/base/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- Supply disclosure: `https://gcagochina.com/supply.json`
- Target public allocation: 400,000,000 GCA
- Owner-held reserve: 600,000,000 GCA
- Reserve wallet: `0x5e8F84748612B913aAcC937492AC25dc5630E246`

Do not describe the reserve as locked, vested, or multisig-controlled unless custody changes on-chain.

## 2026-05-13 Submitted Checklist

Used for the 2026-05-13 resubmission:

1. Confirm `https://gcagochina.com/` loads over HTTPS.
2. Confirm `https://gcagochina.com/assets/gca-logo.svg` loads and is the 32x32 SVG logo.
3. Confirm the official email `support@gcagochina.com` is visible on the website support page.
4. Include the official Telegram and X links.
5. Include the whitepaper, listing kit, product spec, and release gates URLs.
6. Include the Base Mainnet chain ID and exact token contract.
7. Include the official GCA/USDT pool only; do not use the old GCA/WETH pilot pool as the main market.
8. Sign the BaseScan ownership message with the deployer wallet if requested.

## Safe Public Claim

`BaseScan source verification and deployer-wallet ownership verification are complete. The public BaseScan token profile update was returned again as information-insufficient on 2026-05-23. The profile is not approved or published. Tim Chen public professional profile evidence is now published at https://gcagochina.com/tim-chen.html with team, GitHub, X, Telegram, and structured profile-data links for reviewer due diligence; the latest 2026-05-30 DNS snapshot at https://gcagochina.com/domain-email.html#snapshotTitle shows MX/SPF/DKIM/DMARC present, so `readyForBaseScanEmailEvidence` is true; the public domain email evidence checklist is published at https://gcagochina.com/domain-email-evidence.html, the domain email activation evidence packet is defined at https://gcagochina.com/domain-email.html#evidenceTitle, the BaseScan Handoff was generated at 2026-06-06T11:10:54Z, and the daily public status snapshot was refreshed at 2026-06-06T12:13:21Z. The owner may submit one clean BaseScan update from support@gcagochina.com and should avoid duplicate follow-ups while BaseScan reviews it.`

Do not say the BaseScan token profile is approved, published, live, complete, or accepted until the public BaseScan token page shows the submitted information.
