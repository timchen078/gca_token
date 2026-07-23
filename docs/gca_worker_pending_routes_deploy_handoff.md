# GCA Worker Routes Deployment Record

This record documents the production release and repeatable deployment gates for the operator-only Worker routes.

## Current State

Live production Worker base:

```text
https://gca-registration-api.gcagochina.workers.dev
```

Already live routes:

- `GET /` redirects to `https://gcagochina.com/`
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
- token-protected `GET/POST /gca/service-requests`
- token-protected `GET/POST /gca/credit-usage`

The two service routes are production-live and token-protected. They are operator routes only. They are not public user claim endpoints, they do not connect wallets, they do not request wallet signatures, they do not send transactions, they do not transfer GCA, and they do not create live trading permission.

## Production Verification

The deployment was completed on `2026-07-23` UTC.

- Readiness passed at `2026-07-23T17:55:52Z`.
- Remote migration `0005_service_requests.sql` applied successfully.
- Worker version `8988fc75-bbe0-403e-960a-832bf83da20f` deployed successfully.
- Public smoke passed at `2026-07-23T17:53:42Z`.
- Admin read-only smoke passed at `2026-07-23T17:53:54Z`.
- Anonymous reads for both operator routes return HTTP `401`.
- Token-protected admin reads return HTTP `200`.

The deployment blocker is cleared. For future releases, do not apply remote migrations or run `wrangler deploy` until `cloudflare-auth-session`, `cloudflare-d1-visible`, and `cloudflare-worker-deploy-permission` all pass. If `Authentication error [code: 10000]` reappears after login, treat it as an account or permission blocker and follow `authRecovery.safeNextActions`.

## Preconditions

- Work only from `/Users/abc/Desktop/gca_token`.
- Cloudflare login or API token must target the account that owns the `gca-registration-api` Worker and the `gca_registration` D1 database.
- The readiness report must show `cloudflare-auth-session`, `cloudflare-d1-visible`, and `cloudflare-worker-deploy-permission` as passed.
- If the readiness report contains `authRecovery.status: cloudflare-auth-or-permission-blocked`, follow `authRecovery.safeNextActions` before applying migrations or deploying.
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

This command is safe before deploy. It checks local files, Worker bundling, Cloudflare account authentication, D1 visibility, and read-only Worker deployment permission. It does not write D1 data, deploy the Worker, read user ledgers, or print secrets.

Stop if any required check fails.

## Gate 2: Apply Remote D1 Migrations

Only after Gate 1 passes, run:

```bash
cd /Users/abc/Desktop/gca_token/cloudflare/gca-registration-worker
npx wrangler d1 migrations apply gca_registration --remote
```

This applies pending remote D1 migrations. The production database already includes:

- `0004_credit_usage_ledger.sql`
- `0005_service_requests.sql`

Stop if Wrangler reports a remote D1 migration error.

## Gate 3: Deploy Worker

Only after Gate 2 passes, run:

```bash
cd /Users/abc/Desktop/gca_token/cloudflare/gca-registration-worker
npx wrangler deploy
```

Do not change public site status for a future release until the post-deploy checks pass.

## Gate 4: Post-Deploy Public Smoke

Run from repo root:

```bash
cd /Users/abc/Desktop/gca_token
python3 tools/check_gca_registration_api.py --public-only --timeout 30 --include-pending-routes
```

This verifies public health/config version fields, CORS, and unauthenticated admin-read rejection for the service routes. It does not need `ADMIN_READ_TOKEN` and does not write test records.

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

Gates 1 through 5 passed for the 2026-07-23 deployment. For future deployments:

1. Change `site/access-api.json` and `site/api-status.json` route statuses from the previous release state to live token-protected status.
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

- Wrangler is not logged in, or the readiness gate returns `Authentication error [code: 10000]`;
- D1 remote migration fails;
- Worker deploy fails;
- `/health` does not expose `gca_credit_usage_v1` and `gca_service_request_v1`;
- unauthenticated reads do not return authorization errors;
- admin smoke checks cannot read the new route response shapes;
- any command prints secrets or user record contents.

Rollback should be handled through Cloudflare Workers deployment history. Do not edit ledgers manually to hide or rewrite failed deployment evidence.
