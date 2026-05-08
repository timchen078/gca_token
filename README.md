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
- Liquidity plan: `launch/liquidity_plan.json`
- Liquidity pool runbook: `launch/liquidity_pool_runbook.md`
- Audit scope: `launch/audit_scope.md`
- Internal security review: `audit/gca_internal_security_review.md`
- Launch status: `launch/launch_status.md`
- Logo: `brand/gca-logo.svg`
- Static website: `site/index.html`
