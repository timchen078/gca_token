# BaseScan Review Follow-Up

## Current Status

- Network: Base Mainnet
- Chain ID: 8453
- Contract: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- Submission date: 2026-05-09
- Resubmission date: 2026-05-13
- Submission status: returned again; remediation required before next submission
- Review status: remediation-required-before-next-submission
- Return notice date: 2026-05-13
- Latest return notice date: 2026-05-23
- Last checked: 2026-05-30; BaseScan return remains open and the latest DNS snapshot shows the domain email evidence gate is not ready
- Reply inbox: `cxy070800@gmail.com`

Do not describe the BaseScan token profile as complete, published, or accepted until BaseScan confirms the update and the public contract page shows the submitted token information.

## Why It Was Returned

BaseScan replied that it could not process the token update request because the submitted information about the token/project was insufficient. A cleaner resubmission was sent on 2026-05-13, but BaseScan returned the update again on 2026-05-23. Tim Chen official-domain professional profile evidence is now published; the current remaining blocker is the project-domain email evidence gate. The 2026-05-30 DNS snapshot shows MX/SPF/DMARC missing and DKIM selector required, so `readyForBaseScanEmailEvidence` is false.

## Waiting Checklist

- Create and test a working `gcagochina.com` domain email such as `support@gcagochina.com`
- Use the domain email activation runbook at `launch/domain_email_activation_runbook.md`
- Review the current DNS snapshot at `https://gcagochina.com/domain-email.html#snapshotTitle`: MX/SPF/DMARC missing and DKIM selector required as of 2026-05-30
- Run `python3 tools/check_domain_email_dns.py --domain gcagochina.com --mailbox support --dkim-selector <provider-selector> --json` and confirm `readyForBaseScanEmailEvidence` is true
- Archive the domain email activation evidence packet: provider active screenshot, DNS proof, inbound test, outbound test, and updated support-page screenshot
- Tim Chen professional profile remains live: `https://gcagochina.com/tim-chen.html`
- Tim Chen profile data remains live: `https://gcagochina.com/tim-chen.json`
- Team founder anchor remains live: `https://gcagochina.com/team.html#tim-chen`
- Domain email setup plan remains live: `https://gcagochina.com/domain-email.html`
- Domain email setup JSON remains live: `https://gcagochina.com/domain-email.json`
- Domain email DNS worksheet remains live: `https://gcagochina.com/domain-email.html#worksheetTitle`
- Domain email evidence checklist remains live: `https://gcagochina.com/domain-email-evidence.html`
- Domain email evidence checklist JSON remains live: `https://gcagochina.com/domain-email-evidence.json`
- Add LinkedIn later only if BaseScan specifically requires a third-party social-network profile
- Public team profile remains live: `https://gcagochina.com/team.html`
- BaseScan remediation page remains live: `https://gcagochina.com/basescan-remediation.html`
- Public GitHub repository remains live: `https://github.com/timchen078/gca_token`
- Gmail inbox and spam folder for `cxy070800@gmail.com`
- BaseScan account notifications
- Contract page: `https://basescan.org/address/0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- Public website remains live: `https://gcagochina.com/`
- Official verify page remains live: `https://gcagochina.com/verify.html`
- Public status page remains live: `https://gcagochina.com/status.html`
- Product spec remains live: `https://gcagochina.com/product.html`
- Credits catalog remains live: `https://gcagochina.com/credits.html`
- Product release gates remain live: `https://gcagochina.com/release-gates.html`
- Public logo remains live: `https://gcagochina.com/assets/gca-logo.svg`
- Public whitepaper remains live: `https://gcagochina.com/whitepaper.html`
- Brand kit remains live: `https://gcagochina.com/brand-kit.html`
- Community kit remains live: `https://gcagochina.com/community.html`
- External review status remains live: `https://gcagochina.com/external-reviews.html`
- Official GCA/USDT pool remains live: `https://www.geckoterminal.com/base/pools/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- Official Telegram remains live: `https://t.me/gcagochinaofficial`
- Official X remains live: `https://x.com/GCAAIGoChina`
- HTTPS remains active for the website, logo, and whitepaper URLs.
- Use official public email: `GCAgochina@outlook.com`
- If BaseScan asks for ownership verification again, sign with the deployer wallet.
- Do not submit duplicate token update requests unless BaseScan asks for corrections.

## If BaseScan Approves

1. Confirm the contract page displays the GCA logo, website, whitepaper, and contact details.
2. Update `launch/launch_status.md`, `docs/mainnet_public_profile.md`, `docs/whitepaper.md`, `site/index.html`, and `site/whitepaper.html` from "remediation-required-before-next-submission" to "accepted and published".
3. Keep the third-party audit disclosure unchanged unless an independent auditor provides a report or public verification page.
4. Run the full test suite before publishing the updated site.

## If BaseScan Requests More Changes

1. Record the requested changes in this file or a dated follow-up note.
2. Fix only the requested fields unless there is a clear factual error elsewhere.
3. Recheck that all public URLs are reachable before resubmitting.
4. Avoid duplicate submissions while a BaseScan review is still open.

## Public Status Copy

Use this until approval:

`BaseScan source verification and deployer-wallet ownership verification are complete. The public BaseScan token profile update was returned again as information-insufficient on 2026-05-23. The profile is not approved or published. Tim Chen public professional profile evidence is now published at https://gcagochina.com/tim-chen.html with team, GitHub, X, Telegram, and structured profile-data links for reviewer due diligence; the latest 2026-05-30 DNS snapshot at https://gcagochina.com/domain-email.html#snapshotTitle shows MX/SPF/DMARC missing and DKIM selector required, so readyForBaseScanEmailEvidence is false; the domain email activation evidence packet is defined at https://gcagochina.com/domain-email.html#evidenceTitle. The next submission should wait until a working project-domain email is ready.`

Do not use:

- `BaseScan profile complete`
- `BaseScan approved`
- `Externally audited`
- `Guaranteed liquidity`
- `Stable price`

## Reply Template

Subject:

`GCA Token Profile Update - Base Mainnet Contract 0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`

Body:

```text
Hello BaseScan team,

Thank you for reviewing the GCA token profile submission.

Network: Base Mainnet / chainId 8453
Contract: 0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6
Official website: https://gcagochina.com/
Official verify page: https://gcagochina.com/verify.html
Project status: https://gcagochina.com/status.html
Product spec: https://gcagochina.com/product.html
Product release gates: https://gcagochina.com/release-gates.html
Official logo: https://gcagochina.com/assets/gca-logo.svg
Brand kit: https://gcagochina.com/brand-kit.html
Whitepaper: https://gcagochina.com/whitepaper.html
External review status: https://gcagochina.com/external-reviews.html
Tim Chen professional profile: https://gcagochina.com/tim-chen.html
Tim Chen profile data: https://gcagochina.com/tim-chen.json
Domain email setup plan: https://gcagochina.com/domain-email.html
Domain email setup data: https://gcagochina.com/domain-email.json
Domain email DNS worksheet: https://gcagochina.com/domain-email.html#worksheetTitle
Domain email evidence checklist: https://gcagochina.com/domain-email-evidence.html
Domain email evidence checklist data: https://gcagochina.com/domain-email-evidence.json
Latest DNS snapshot: https://gcagochina.com/domain-email.html#snapshotTitle
Domain email activation evidence packet: https://gcagochina.com/domain-email.html#evidenceTitle
Community kit: https://gcagochina.com/community.html
Official GCA/USDT pool: https://www.geckoterminal.com/base/pools/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0
Official Telegram: https://t.me/gcagochinaofficial
Official X: https://x.com/GCAAIGoChina
Official contact email: GCAgochina@outlook.com

The official website now centralizes the verify page, project status, product spec, release gates, listing kit, brand kit, community kit, support page, token list, and machine-readable project JSON. The latest 2026-05-30 DNS snapshot shows MX/SPF/DMARC missing and DKIM selector required, so readyForBaseScanEmailEvidence is false until support@gcagochina.com is active and tested. Please let us know if any additional field correction or owner-wallet signature is required.
```
