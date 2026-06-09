# GCA Pending Worker Routes Deploy Handoff

This handoff is for publishing the prepared operator-only Worker routes after Cloudflare Workers service permission is restored.

## Current State

Live production Worker base:

```text
https://gca-registration-api.gcagochina.workers.dev
```

Already live routes:

- `GET /health`
- `GET /gca/access-config`
- `POST /gca/email-registrations`
- `POST /gca/contact-suppressions`
- `POST /gca/wallet-verifications`
- `POST /gca/member-access`
- token-protected `GET /gca/email-registrations`
- token-protected `GET /gca/contact-suppressions`
- token-protected `GET /gca/wallet-verifications`
- token-protected `GET /gca/member-access`
- token-protected `GET /gca/credit-ledger`
- token-protected `GET /gca/member-ledger`

Prepared but not production-live until a new Worker is deployed:

- token-protected `GET/POST /gca/service-requests`
- token-protected `GET/POST /gca/credit-usage`

The prepared routes are operator routes only. They are not public user claim endpoints, they do not connect wallets, they do not request wallet signatures, they do not send transactions, they do not transfer GCA, and they do not create live trading permission.

## Blocker

The local source, migrations, package install, and Wrangler dry-run are prepared, but the active Cloudflare authorization currently fails the Worker deployment-permission gate with:

```text
Authentication error [code: 10000]
```

Do not run `wrangler deploy` until the read-only deploy permission gate passes.

## Preconditions

- Work only from `/Users/abc/Desktop/gca_token`.
- Cloudflare login or API token must target the account that owns the `gca-registration-api` Worker and the `gca_registration` D1 database.
- `npx wrangler d1 list` must show the `gca_registration` database.
- `npx wrangler deployments list --json` must work for this Worker.
- `cloudflare/gca-registration-worker/.env.admin.local` may exist locally for admin smoke checks, but it must stay ignored by git.
- Do not print, commit, paste, or publish `ADMIN_READ_TOKEN`.
- Do not export user ledgers before the post-deploy smoke checks pass.

## Gate 1: Read-Only Readiness

Run from repo root:

```bash
cd /Users/abc/Desktop/gca_token
python3 tools/check_gca_worker_deploy_readiness.py --run-wrangler --run-cloudflare --require-deploy-auth
```

This command is safe before deploy. It checks local files, Worker bundling, D1 visibility, and read-only Worker deployment permission. It does not write D1 data, deploy the Worker, read user ledgers, or print secrets.

Stop if any required check fails.

## Gate 2: Apply Remote D1 Migrations

Only after Gate 1 passes, run:

```bash
cd /Users/abc/Desktop/gca_token/cloudflare/gca-registration-worker
npx wrangler d1 migrations apply gca_registration --remote
```

This applies pending remote D1 migrations, including:

- `0004_credit_usage_ledger.sql`
- `0005_service_requests.sql`

Stop if Wrangler reports a remote D1 migration error.

## Gate 3: Deploy Worker

Only after Gate 2 passes, run:

```bash
cd /Users/abc/Desktop/gca_token/cloudflare/gca-registration-worker
npx wrangler deploy
```

Do not change public site status to live until the post-deploy checks pass.

## Gate 4: Post-Deploy Public Smoke

Run from repo root:

```bash
cd /Users/abc/Desktop/gca_token
python3 tools/check_gca_registration_api.py --public-only --timeout 30 --include-pending-routes
```

This verifies public health/config version fields, CORS, and unauthenticated admin-read rejection for the pending routes. It does not need `ADMIN_READ_TOKEN` and does not write test records.

## Gate 5: Post-Deploy Admin Smoke

Run from repo root:

```bash
cd /Users/abc/Desktop/gca_token
python3 tools/check_gca_registration_api.py --token-file cloudflare/gca-registration-worker/.env.admin.local --limit 5 --include-pending-routes
```

This checks token-protected reads for the live and newly deployed operator routes. It prints only counts and check statuses; it must not print the token or user records.

## Optional Operator Export After Success

Use only after Gates 1 through 5 pass:

```bash
cd /Users/abc/Desktop/gca_token
python3 tools/export_cloudflare_member_access.py \
  --token-file cloudflare/gca-registration-worker/.env.admin.local \
  --limit 100 \
  --include-pending-routes \
  --output .gca_access_data/cloudflare_member_access_export.json
```

The export is an internal operator artifact. Do not publish full user records.

## Status Update After Success

After Gates 1 through 5 pass:

1. Change `site/access-api.json` and `site/api-status.json` route statuses from `prepared-worker-deploy-permission-pending` or `prepared-worker-deploy-pending` to live token-protected status.
2. Update the matching HTML pages to say the routes are live.
3. Run:

```bash
cd /Users/abc/Desktop/gca_token
python3 -m unittest discover tests
python3 tools/check_public_site.py --base-url http://127.0.0.1:8799
python3 tools/check_gca_registration_api.py --public-only --timeout 30 --include-pending-routes
```

4. Commit and push only after the checks pass.

## Rollback And Stop Conditions

Stop and do not claim the routes are live if:

- the readiness gate still returns `Authentication error [code: 10000]`;
- D1 remote migration fails;
- Worker deploy fails;
- `/health` does not expose `gca_credit_usage_v1` and `gca_service_request_v1`;
- unauthenticated reads do not return authorization errors;
- admin smoke checks cannot read the new route response shapes;
- any command prints secrets or user record contents.

Rollback should be handled through Cloudflare Workers deployment history. Do not edit ledgers manually to hide or rewrite failed deployment evidence.
