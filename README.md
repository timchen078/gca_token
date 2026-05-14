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

## Mainnet Launch Package

- Canonical public facts: `docs/mainnet_public_profile.md`
- Draft whitepaper: `docs/whitepaper.md`
- BaseScan submission package: `launch/basescan_token_submission.md`
- BaseScan form values: `launch/basescan_form_values.json`
- BaseScan review follow-up: `launch/basescan_review_followup.md`
- BaseScan resubmission package: `launch/basescan_resubmission_package.md`
- BaseScan resubmission values: `launch/basescan_resubmission_values.json`
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
- Public support intake page: `site/support.html`
- Public support intake JSON: `site/support.json`
- Public roadmap page: `site/roadmap.html`
- Public roadmap JSON: `site/roadmap.json`
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
- Public access portal blueprint page: `site/access.html`
- Public access portal blueprint JSON: `site/access.json`
- Public access API contract page: `site/access-api.html`
- Public access API contract JSON: `site/access-api.json`
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
- Live public site check, including market identity, member program rules, product release gates, listing readiness, and high-risk public-claim guardrails: `.venv/bin/python tools/check_public_site.py`
- GitHub Actions public site check: `.github/workflows/check-public-site.yml`
