# GCA Token Workspace

This is the standalone workspace for the GCA fixed-supply token.
It is intentionally separate from `/Users/abc/Desktop/web3_radar`.

See `token/README.md` for token parameters, safety notes, and deployment flow.

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-token-dev.txt
.venv/bin/python token/scripts/build_gca_artifact.py
.venv/bin/python -m unittest tests.test_gca_token_contract tests.test_gca_token_compile tests.test_gca_token_deploy_script -v
```

Deployment notes are in `docs/deploy_base_sepolia.md` and `docs/deploy_base_mainnet.md`.

## Local Member Backend

Run the local-only member backend for operator testing:

```bash
.venv/bin/python tools/gca_member_backend.py --host 127.0.0.1 --port 8787
```

Then open `http://127.0.0.1:8787/members.html` for intake or `http://127.0.0.1:8787/operator.html` for the local operator console. The backend serves `site/`, accepts `POST /gca/pre-registrations`, verifies GCA with read-only Base Mainnet `eth_call`, exposes `GET /gca/operator-summary`, exposes the latest local redacted daily digest at `GET /gca/operator-digest`, ranks manual next actions at `GET /gca/operator-action-plan`, exports a localhost-only reviewer evidence package at `GET /gca/review-package` with `recordManifest` and `packageDigestSha256`, supports `GET /gca/review-package?redact=public` for external-sharing redaction, and writes append-only JSONL records under `.gca_access_data/`. The operator console displays the last exported package mode, digest, local verify command, daily operator digest, action plan, a local support review update form, and a copyable handoff reply for public-redacted reviewer packages; full-local packages remain internal only and require an explicit browser confirmation before download. Operators can append manual support status updates with `POST /gca/member-review` and record a manually completed 10,000 GCA member benefit transfer with `POST /gca/member-benefit-transfers`; before recording a transfer, the backend verifies the public transaction hash with read-only Base Mainnet `eth_getTransactionReceipt` and confirms a matching GCA `Transfer` log to the member wallet. It does not send tokens or ask for private keys, seed phrases, signatures, withdrawal permission, custody, or exchange API secrets.

Verify an exported review package digest locally:

```bash
.venv/bin/python tools/verify_gca_review_package.py path/to/gca-review-package.json
```

Export the same review package directly from local JSONL data without starting the backend server:

```bash
.venv/bin/python tools/export_gca_review_package.py --output gca-full-local-review-package.json
.venv/bin/python tools/export_gca_review_package.py --redact public --output gca-public-redacted-review-package.json
.venv/bin/python tools/verify_gca_review_package.py gca-public-redacted-review-package.json
```

## Mainnet Launch Package

- Canonical public facts: `docs/mainnet_public_profile.md`
- Draft whitepaper: `docs/whitepaper.md`
- BaseScan submission package: `launch/basescan_token_submission.md`
- BaseScan form values: `launch/basescan_form_values.json`
- BaseScan review follow-up: `launch/basescan_review_followup.md`
- Public BaseScan follow-up page: `site/basescan-followup.html`
- Public BaseScan follow-up JSON: `site/basescan-followup.json`
- BaseScan resubmission package: `launch/basescan_resubmission_package.md`
- BaseScan resubmission values: `launch/basescan_resubmission_values.json`
- BaseScan reviewer checklist tool: `tools/build_basescan_reviewer_checklist.py`
- Domain email provider matrix tool: `tools/build_domain_email_provider_matrix.py`
- Domain email DNS entry packet tool: `tools/build_domain_email_dns_entry_packet.py`
- Domain email switch plan tool: `tools/build_domain_email_switch_plan.py`
- Domain email switch plan artifact: `launch/domain_email_switch_plan.json`
- Domain email switch plan markdown: `launch/domain_email_switch_plan.md`
- Domain email switch patch preview: `launch/domain_email_switch_preview.patch`
- Domain email public switch checker: `tools/check_domain_email_public_switch.py`
- Token allocation plan: `launch/token_allocation_plan.md`
- Liquidity plan: `launch/liquidity_plan.json`
- Liquidity pool runbook: `launch/liquidity_pool_runbook.md`
- Liquidity deployment record: `deployments/base-mainnet-gca-liquidity.json`
- Data platform submission package: `launch/data_platform_package.md`
- Data platform form values: `launch/data_platform_form_values.json`
- GeckoTerminal update runbook: `launch/geckoterminal_update_runbook.md`
- GeckoTerminal form values: `launch/geckoterminal_form_values.json`
- Public member program rules: `site/member-program.json`
- Public member ledger schema page: `site/member-ledger.html`
- Public member ledger schema JSON: `site/member-ledger.json`
- Local member backend: `tools/gca_member_backend.py`
- Local operator console: `site/operator.html`
- Public support intake page: `site/support.html`
- Public support intake JSON: `site/support.json`
- Public company and project profile: `site/about.html`
- Public Chinese user entry page: `site/zh-cn.html`
- Public Chinese buy guide: `site/zh-buy.html`
- Public Chinese participation guide: `site/zh-apply.html`
- Public Chinese review status page: `site/zh-status.html`
- Public Chinese domain email remediation page: `site/zh-domain-email.html`
- Public Chinese liquidity and pool guide: `site/zh-liquidity.html`
- Public Chinese supply and reserve guide: `site/zh-supply.html`
- Public Chinese security and audit guide: `site/zh-security.html`
- Public Chinese roadmap and product boundary guide: `site/zh-roadmap.html`
- Public Chinese FAQ page: `site/zh-faq.html`
- Public Chinese support and intake guide: `site/zh-support.html`
- Public Chinese registration API status page: `site/zh-api-status.html`
- Public Chinese registration operations guide: `site/zh-operations.html`
- Public Chinese user access preview: `site/zh-access.html`
- Public Chinese release gates page: `site/zh-release-gates.html`
- Public Chinese read-only wallet verification guide: `site/zh-wallet-verify.html`
- Public Chinese member review checklist: `site/zh-member-checklist.html`
- Public Chinese site map: `site/zh-site-map.html`
- Public Chinese Data Room guide: `site/zh-data.html`
- Public email-only user registration page: `site/register.html`
- Production-ready email registration backend package: `cloudflare/gca-registration-worker/`
- Email registration backend deployment guide: `docs/gca_registration_backend.md`
- Live member access operator export: `tools/export_cloudflare_member_access.py`
- Local member access report builder: `tools/build_gca_member_access_report.py`
- Local member support reply queue builder: `tools/build_gca_member_support_queue.py`
- Local GCA Member 30-day holding evidence report: `tools/build_gca_holding_period_report.py`
- One-command member access ops pipeline: `tools/run_gca_member_access_ops.py`
- Daily public health, optional member ops check, optional digest build, and `--update-public-status` snapshot refresh: `tools/run_gca_daily_ops.py`
- Public daily status snapshot builder for `site/daily-status.html` and `site/daily-status.json`: `tools/build_gca_daily_status_snapshot.py`
- Local redacted operator digest builder: `tools/build_gca_operator_digest.py`
- GitHub Actions public daily ops check: `.github/workflows/check-gca-daily-ops.yml`
- Read-only live registration API check: `tools/check_gca_registration_api.py`
- GitHub Actions public registration API check: `.github/workflows/check-gca-registration-api.yml`
- Public Chinese member rules page: `site/zh-members.html`
- Public roadmap page: `site/roadmap.html`
- Public roadmap JSON: `site/roadmap.json`
- Public next-step action plan: `site/action-plan.html`
- Public next-step action plan JSON: `site/action-plan.json`
- Public community kit page: `site/community.html`
- Public community kit JSON: `site/community.json`
- Public narrative system page: `site/narrative.html`
- Public narrative system JSON: `site/narrative.json`
- Public Weekly Go China Radar page: `site/radar.html`
- Public Weekly Go China Radar JSON: `site/radar.json`
- Public privacy notice page: `site/privacy.html`
- Public privacy notice JSON: `site/privacy.json`
- Public participation terms page: `site/terms.html`
- Public participation terms JSON: `site/terms.json`
- Public utility bridge page: `site/utility.html`
- Public utility bridge JSON: `site/utility.json`
- Public product spec page: `site/product.html`
- Public product spec JSON: `site/product.json`
- Public access portal page: `site/access.html`
- Public access portal JSON: `site/access.json`
- Public access API contract page: `site/access-api.html`
- Public access API contract JSON: `site/access-api.json`
- Public registration API status page: `site/api-status.html`
- Public registration API status JSON: `site/api-status.json`
- Public review queue contract page: `site/review-queue.html`
- Public review queue contract JSON: `site/review-queue.json`
- Public access operations runbook page: `site/operations.html`
- Public access operations runbook JSON: `site/operations.json`
- Public utility credits catalog page: `site/credits.html`
- Public utility credits catalog JSON: `site/credits.json`
- Public product release gates page: `site/release-gates.html`
- Public product release gates JSON: `site/release-gates.json`
- Public brand kit page: `site/brand-kit.html`
- Public brand kit JSON: `site/brand-kit.json`
- Public on-chain proofs page: `site/onchain-proofs.html`
- Public on-chain proofs JSON: `site/onchain-proofs.json`
- Public supply disclosure JSON: `site/supply.json`
- Public wallet warning evidence page: `site/wallet-warning.html`
- Public wallet warning evidence JSON: `site/wallet-warning.json`
- Public wallet security profile: `site/.well-known/wallet-security.json`
- Public external review status page: `site/external-reviews.html`
- Public external review status JSON: `site/external-reviews.json`
- Public listing readiness page: `site/listing-readiness.html`
- Public listing readiness gate: `site/listing-readiness.json`
- Public market quality page: `site/market-quality.html`
- Public market quality JSON: `site/market-quality.json`
- Public token safety checklist page: `site/token-safety.html`
- Public token safety checklist JSON: `site/token-safety.json`
- Telegram channel runbook: `launch/telegram_channel_runbook.md`
- X profile runbook: `launch/x_profile_runbook.md`
- Audit scope: `launch/audit_scope.md`
- Internal security review: `audit/gca_internal_security_review.md`
- Launch status: `launch/launch_status.md`
- Logo: `brand/gca-logo.svg`
- Social preview card: `brand/gca-social-card.svg`
- Static website: `site/index.html`
- Local review package exporter: `tools/export_gca_review_package.py`
- Live public site check, including market identity, member program rules, access operations runbook, product release gates, listing readiness, and high-risk public-claim guardrails: `.venv/bin/python tools/check_public_site.py`
- GitHub Actions public site check: `.github/workflows/check-public-site.yml`
