# GCA Registration and Member Access Backend

This is the deployed backend package for the public GCA email registration form, contact suppression, live member access UI, read-only wallet verification, 100-credit ledger records, and GCA Member ledger records.

The public website remains hosted on GitHub Pages. The write API is deployed on Cloudflare Workers + D1 and currently exposed as:

```text
https://gca-registration-api.gcagochina.workers.dev/gca/email-registrations
https://gca-registration-api.gcagochina.workers.dev/gca/contact-suppressions
https://gca-registration-api.gcagochina.workers.dev/gca/member-access
https://gca-registration-api.gcagochina.workers.dev/gca/wallet-verifications
https://gca-registration-api.gcagochina.workers.dev/gca/access-config
```

## What It Stores

- email
- optional display name
- registration source and language
- interest tags
- contact-consent acknowledgement
- no-secrets/no-custody acknowledgement
- generated `emailRegistrationId`
- timestamps
- optional salted IP hash if `PRIVACY_HASH_SALT` is configured

Contact-suppression requests store:

- email
- generated `suppressionId`
- email hash
- reason and source
- status `suppressed`
- timestamps
- optional salted IP hash if `PRIVACY_HASH_SALT` is configured

Member-access requests store:

- email and optional display name
- Base wallet address
- generated `accountId`
- read-only wallet verification result from Base Mainnet ERC-20 `balanceOf`
- 100 Web3 Radar utility credit ledger record when the verified wallet holds at least 10,000 GCA
- GCA Member ledger record when the verified wallet holds at least 1,000,000 GCA
- holding start date and public evidence transaction hash for 30-day member review
- member benefit status
- timestamps
- optional salted IP hash if `PRIVACY_HASH_SALT` is configured

It does not collect wallet private keys, seed phrases, wallet passwords, exchange API secrets, withdrawal permissions, one-time codes, or remote-control access. It does not request wallet signatures or transactions for wallet verification. It does not automatically transfer GCA. The 10,000 GCA member benefit remains a manual reserve-wallet transfer review after eligibility is recorded.

Public registration, contact-suppression, wallet-verification, and member-access submissions also include empty `website`, `company`, and `homepage` honeypot fields. Normal users never fill these fields; the Worker rejects any request where one of them contains content. This is a light anti-spam control and does not replace Cloudflare rate limits or future account-session CSRF controls.

## Deployed Cloudflare Resources

- Worker: `gca-registration-api`
- Workers.dev endpoint: `https://gca-registration-api.gcagochina.workers.dev`
- D1 database: `gca_registration`
- D1 database id: `b4cb13f7-c52e-4dbc-b8d6-50346a814819`
- Public site integration: `site/register.html`
- Public contact suppression integration: `site/unsubscribe.html`
- Public member access integration: `site/gca/member-access/index.html`
- Public form anti-spam: empty `website`, `company`, and `homepage` honeypot fields rejected by the Worker
- Admin read endpoint: `GET /gca/email-registrations`
- Public contact suppression endpoint: `POST /gca/contact-suppressions`
- Admin contact suppression endpoint: `GET /gca/contact-suppressions`
- Public member access endpoint: `POST /gca/member-access`
- Public wallet verification endpoint: `POST /gca/wallet-verifications`
- Public access config endpoint: `GET /gca/access-config`
- Admin wallet verification endpoint: `GET /gca/wallet-verifications`
- Admin credit ledger endpoint: `GET /gca/credit-ledger`
- Admin member ledger endpoint: `GET /gca/member-ledger`
- Member D1 migration: `cloudflare/gca-registration-worker/migrations/0003_member_access_ledgers.sql`
- Admin read secret: configured in Cloudflare as `ADMIN_READ_TOKEN`
- Privacy hash salt: configured in Cloudflare as `PRIVACY_HASH_SALT`
- Read-only live API check tool: `tools/check_gca_registration_api.py`
- Local admin export tool: `tools/export_cloudflare_email_registrations.py`
- Local member access / wallet / credit / member ledger export tool: `tools/export_cloudflare_member_access.py`
- Local member access report builder: `tools/build_gca_member_access_report.py`
- Local member support reply queue builder: `tools/build_gca_member_support_queue.py`
- Local GCA Member 30-day holding evidence report: `tools/build_gca_holding_period_report.py`
- Local one-command member access ops pipeline: `tools/run_gca_member_access_ops.py`
- Local daily public health and optional member ops check: `tools/run_gca_daily_ops.py`
- Local redacted operator digest builder: `tools/build_gca_operator_digest.py`
- Local ledger sync tool: `tools/sync_cloudflare_email_registrations.py`
- Local contact CSV export tool: `tools/export_gca_email_contacts.py`
- Local one-command ops pipeline: `tools/run_gca_registration_ops.py`
- Local contact suppression tool: `tools/suppress_gca_contact.py`
- Local Cloudflare contact suppression sync tool: `tools/sync_cloudflare_contact_suppressions.py`
- Contact suppression D1 migration: `cloudflare/gca-registration-worker/migrations/0002_contact_suppressions.sql`

The future custom domain `api.gcagochina.com` still requires Wrangler to be logged into a Cloudflare account that can see the `gcagochina.com` zone. DNS currently uses Cloudflare nameservers, but the currently authorized account does not contain that zone, so Cloudflare rejects the custom-domain deployment with `The zone "gcagochina.com" does not exist on your account`.

## Deployment Commands

Run these commands from `cloudflare/gca-registration-worker/` after logging in to the correct Cloudflare account:

```bash
npm install
npx wrangler d1 create gca_registration
```

Copy the returned D1 `database_id` into `wrangler.toml`.

Then apply the migration and set required secrets:

```bash
npx wrangler d1 migrations apply gca_registration --remote
npx wrangler secret put ADMIN_READ_TOKEN
npx wrangler secret put PRIVACY_HASH_SALT
npx wrangler deploy
```

The current configuration publishes through `workers.dev`. Switch to a Cloudflare custom domain only after the official domain is managed by Cloudflare.

## Admin Read

The admin read endpoint is enabled by the deployed Worker but protected by `ADMIN_READ_TOKEN`.

The local operator copy of the token is stored only in:

```text
cloudflare/gca-registration-worker/.env.admin.local
```

That file is ignored by git and must not be committed or shared publicly.

To run a read-only live API smoke check without writing production D1 data:

```bash
.venv/bin/python tools/check_gca_registration_api.py --limit 5
```

This checks `/health`, `/gca/access-config`, CORS preflight, unauthenticated admin-read rejection, and token-protected admin-read response shape. It prints only counts and check statuses; it does not print the admin token or user email records.

For public CI or environments without `ADMIN_READ_TOKEN`, run only the public surface checks:

```bash
.venv/bin/python tools/check_gca_registration_api.py --public-only --timeout 30
```

The GitHub Actions workflow at `.github/workflows/check-gca-registration-api.yml` uses `--public-only`, so it does not require secrets and does not read token-protected user records.

The consolidated public daily ops workflow at `.github/workflows/check-gca-daily-ops.yml` runs `tools/run_gca_daily_ops.py` in default public-only mode. It checks the public website and public registration API together, and it does not pass `--include-member-ops` or `--include-holding-report`.

To read recent email registrations:

```bash
cd cloudflare/gca-registration-worker
set -a
. ./.env.admin.local
set +a

curl -fsS 'https://gca-registration-api.gcagochina.workers.dev/gca/email-registrations?limit=20' \
  -H "authorization: Bearer $ADMIN_READ_TOKEN"
```

To read recent contact-suppression requests:

```bash
curl -fsS 'https://gca-registration-api.gcagochina.workers.dev/gca/contact-suppressions?limit=20' \
  -H "authorization: Bearer $ADMIN_READ_TOKEN"

curl -fsS 'https://gca-registration-api.gcagochina.workers.dev/gca/member-access?limit=20' \
  -H "authorization: Bearer $ADMIN_READ_TOKEN"

curl -fsS 'https://gca-registration-api.gcagochina.workers.dev/gca/wallet-verifications?limit=20' \
  -H "authorization: Bearer $ADMIN_READ_TOKEN"

curl -fsS 'https://gca-registration-api.gcagochina.workers.dev/gca/credit-ledger?limit=20' \
  -H "authorization: Bearer $ADMIN_READ_TOKEN"

curl -fsS 'https://gca-registration-api.gcagochina.workers.dev/gca/member-ledger?limit=20' \
  -H "authorization: Bearer $ADMIN_READ_TOKEN"
```

To export recent registrations into the ignored local data directory:

```bash
.venv/bin/python tools/export_cloudflare_email_registrations.py \
  --limit 100 \
  --output .gca_access_data/cloudflare_email_registrations_export.json
```

Use a redacted export before sharing outside the operator workspace:

```bash
.venv/bin/python tools/export_cloudflare_email_registrations.py \
  --redact public \
  --output .gca_access_data/cloudflare_email_registrations_public_redacted.json
```

To export live member access, wallet verification, credit ledger, and member ledger records into the ignored local data directory:

```bash
.venv/bin/python tools/export_cloudflare_member_access.py \
  --dataset all \
  --limit 100 \
  --output .gca_access_data/cloudflare_member_access_export.json
```

To inspect one wallet across the member ledgers:

```bash
.venv/bin/python tools/export_cloudflare_member_access.py \
  --dataset all \
  --wallet-address 0x0000000000000000000000000000000000000000 \
  --output .gca_access_data/cloudflare_member_access_wallet_export.json
```

Use a redacted export before sharing outside the operator workspace. It removes raw email and display-name fields, keeps email hashes, and retains wallet addresses only for on-chain review:

```bash
.venv/bin/python tools/export_cloudflare_member_access.py \
  --dataset all \
  --redact public \
  --output .gca_access_data/cloudflare_member_access_public_redacted.json
```

To turn a member-access export into local operator CSV reports:

```bash
.venv/bin/python tools/build_gca_member_access_report.py \
  --input .gca_access_data/cloudflare_member_access_export.json \
  --output-dir .gca_access_data/member_access_report \
  --summary-output .gca_access_data/member_access_report/gca_member_access_report_summary.json
```

The report writes account, wallet-verification, credit-ledger, member-ledger, and member-benefit review queue CSV files. It is offline and does not call Cloudflare, wallets, or Base RPC.

To build an operator-reviewed support reply queue from the same export:

```bash
.venv/bin/python tools/build_gca_member_support_queue.py \
  --input .gca_access_data/cloudflare_member_access_export.json \
  --output .gca_access_data/member_access_report/gca_member_support_queue.csv \
  --summary-output .gca_access_data/member_access_report/gca_member_support_queue_summary.json
```

The support queue includes reply status, subject, body, and next step. It is not an auto-send system; every row requires operator review before a user reply is sent.

For routine member operations, run the combined member-access pipeline instead. It fetches live member access datasets, saves the local export, builds CSV reports, and writes an ignored summary JSON:
It also builds the operator-reviewed support reply queue.

```bash
.venv/bin/python tools/run_gca_member_access_ops.py \
  --limit 100 \
  --export-output .gca_access_data/cloudflare_member_access_export.json \
  --report-dir .gca_access_data/member_access_report \
  --support-queue-output .gca_access_data/member_access_report/gca_member_support_queue.csv \
  --summary-output .gca_access_data/gca_member_access_ops_summary.json
```

To rebuild reports from an existing export without reading Cloudflare:

```bash
.venv/bin/python tools/run_gca_member_access_ops.py \
  --input .gca_access_data/cloudflare_member_access_export.json \
  --report-dir .gca_access_data/member_access_report
```

To build the GCA Member 30-day holding evidence report from the same export and record one read-only Base Mainnet balance snapshot per candidate wallet:

```bash
.venv/bin/python tools/build_gca_holding_period_report.py \
  --input .gca_access_data/cloudflare_member_access_export.json \
  --snapshot-output .gca_access_data/gca_holding_snapshots.jsonl \
  --report-output .gca_access_data/member_access_report/gca_holding_period_report.csv \
  --summary-output .gca_access_data/member_access_report/gca_holding_period_summary.json
```

To include the same report in the one-command member ops pipeline:

```bash
.venv/bin/python tools/run_gca_member_access_ops.py \
  --input .gca_access_data/cloudflare_member_access_export.json \
  --include-holding-report
```

Use `--holding-no-live-read` when you only want to rebuild the holding report from existing local snapshots. The holding report is local operator evidence only; it does not approve the 10,000 GCA member benefit by itself.

To run the daily public health check for the website and API without reading user records:

```bash
.venv/bin/python tools/run_gca_daily_ops.py \
  --summary-output .gca_access_data/gca_daily_ops_summary.json
```

To include token-protected member report refresh in the same daily run, add `--include-member-ops`. Use this only from an operator machine with `ADMIN_READ_TOKEN` available:

```bash
.venv/bin/python tools/run_gca_daily_ops.py \
  --include-member-ops \
  --summary-output .gca_access_data/gca_daily_ops_summary.json
```

To also record the daily 30-day GCA Member holding snapshot during that member-ops run, add `--include-holding-report`:

```bash
.venv/bin/python tools/run_gca_daily_ops.py \
  --include-member-ops \
  --include-holding-report \
  --summary-output .gca_access_data/gca_daily_ops_summary.json
```

Use `--holding-no-live-read` with the daily command when you only want to rebuild the holding report from existing local snapshots. The holding report option is deliberately gated behind `--include-member-ops` because it depends on token-protected member exports.

To build the redacted local operator digest as part of the same daily run:

```bash
.venv/bin/python tools/run_gca_daily_ops.py \
  --build-digest \
  --summary-output .gca_access_data/gca_daily_ops_summary.json \
  --digest-output .gca_access_data/gca_operator_digest.md \
  --digest-json-output .gca_access_data/gca_operator_digest.json
```

`--build-digest` reads existing summary files only. It does not include user records, emails, admin tokens, signatures, transactions, wallet actions, or automatic benefit transfers.

To build a redacted local operator digest from the latest summary files:

```bash
.venv/bin/python tools/build_gca_operator_digest.py \
  --output .gca_access_data/gca_operator_digest.md \
  --json-output .gca_access_data/gca_operator_digest.json
```

The digest includes public health status, member-ops counts, support queue counts, holding-period counts, and next actions. It does not include user records, emails, admin tokens, signatures, transactions, or automatic transfer actions.

To sync full Cloudflare registrations into the local operator JSONL ledger:

```bash
.venv/bin/python tools/sync_cloudflare_email_registrations.py \
  --limit 100 \
  --data-dir .gca_access_data
```

The sync is idempotent by `emailRegistrationId`, so running it again skips records already present in `.gca_access_data/email_registrations.jsonl`.

To sync Cloudflare contact suppressions into the local do-not-contact JSONL file:

```bash
.venv/bin/python tools/sync_cloudflare_contact_suppressions.py \
  --limit 100 \
  --suppression-file .gca_access_data/gca_contact_suppressions.jsonl
```

The suppression sync is idempotent by `suppressionId` and normalized email. Running it again skips records already present in `.gca_access_data/gca_contact_suppressions.jsonl`.

For routine operations, run the combined pipeline instead. It syncs Cloudflare records into the local ledger, exports the internal contact CSV, exports the public redacted contact CSV, and writes an ignored summary JSON:

```bash
.venv/bin/python tools/run_gca_registration_ops.py \
  --limit 100 \
  --data-dir .gca_access_data
```

When `--input` is omitted, the combined pipeline also reads Cloudflare `/gca/contact-suppressions`, syncs it into `.gca_access_data/gca_contact_suppressions.jsonl`, and excludes suppressed emails before writing contact CSV files.

If a user should no longer be contacted, add the email to the local suppression list before the next export:

```bash
.venv/bin/python tools/suppress_gca_contact.py \
  --email user@example.com \
  --reason unsubscribe_request \
  --source support
```

The suppression list is stored at `.gca_access_data/gca_contact_suppressions.jsonl`. The contact export and combined ops pipeline read it automatically and exclude suppressed emails from both the internal CSV and the public redacted CSV.

To sync from a previously exported full, non-redacted file:

```bash
.venv/bin/python tools/sync_cloudflare_email_registrations.py \
  --input .gca_access_data/cloudflare_email_registrations_export.json \
  --data-dir .gca_access_data
```

To run the combined pipeline from local registration and suppression export files without live network access:

```bash
.venv/bin/python tools/run_gca_registration_ops.py \
  --input .gca_access_data/cloudflare_email_registrations_export.json \
  --suppression-input .gca_access_data/cloudflare_contact_suppressions_export.json \
  --data-dir .gca_access_data
```

To export a local contact CSV after syncing the ledger:

```bash
.venv/bin/python tools/export_gca_email_contacts.py \
  --data-dir .gca_access_data \
  --output .gca_access_data/gca_email_contacts.csv
```

Only records with `contactConsentAccepted: true` are exported, and duplicate emails are collapsed to the latest registration record. For external reporting, export a redacted CSV:

```bash
.venv/bin/python tools/export_gca_email_contacts.py \
  --data-dir .gca_access_data \
  --redact public \
  --output .gca_access_data/gca_email_contacts_public_redacted.csv
```

## Custom Domain Activation

Use this only after logging into the Cloudflare account that owns the `gcagochina.com` zone, or after adding the current Cloudflare account as a member with zone and Worker permissions.

1. Confirm the account can see the zone:

```bash
dig +short NS gcagochina.com
```

2. Copy the custom-domain example over the active Wrangler config:

```bash
cp wrangler.custom-domain.example.toml wrangler.toml
```

3. Deploy:

```bash
npx wrangler deploy
```

4. Verify:

```bash
dig +short api.gcagochina.com
curl -fsS https://api.gcagochina.com/health
```

5. After `api.gcagochina.com` is live, update `site/register.html`, `site/access-api.json`, and this document to use `https://api.gcagochina.com` as the production API base, then run the public-site checks and push.

## Smoke Test

```bash
curl -fsS https://gca-registration-api.gcagochina.workers.dev/health

curl -fsS https://gca-registration-api.gcagochina.workers.dev/gca/email-registrations \
  -H 'content-type: application/json' \
  -X POST \
  --data '{
    "packetVersion": "gca_email_registration_v1",
    "email": "user@example.com",
    "source": "register.html",
    "language": "zh-CN",
    "interests": ["gca_updates", "member_access"],
    "acknowledgements": {
      "emailContactConsent": true,
      "noSecretsNoCustody": true
    }
  }'

curl -fsS https://gca-registration-api.gcagochina.workers.dev/gca/contact-suppressions \
  -H 'content-type: application/json' \
  -X POST \
  --data '{
    "packetVersion": "gca_contact_suppression_v1",
    "email": "user@example.com",
    "reason": "unsubscribe_request",
    "source": "unsubscribe.html",
    "acknowledgements": {
      "contactSuppressionRequested": true,
      "noSecretsNoCustody": true
    }
  }'

curl -fsS https://gca-registration-api.gcagochina.workers.dev/gca/access-config

curl -fsS https://gca-registration-api.gcagochina.workers.dev/gca/wallet-verifications \
  -H 'content-type: application/json' \
  -X POST \
  --data '{
    "walletAddress": "0x0000000000000000000000000000000000000000"
  }'

curl -fsS https://gca-registration-api.gcagochina.workers.dev/gca/member-access \
  -H 'content-type: application/json' \
  -X POST \
  --data '{
    "packetVersion": "gca_member_access_v1",
    "user": {
      "email": "user@example.com",
      "displayName": "GCA User",
      "walletAddress": "0x0000000000000000000000000000000000000000"
    },
    "memberBenefitReviewEvidence": {
      "holdingStartDate": "2026-05-01",
      "evidenceTxHash": ""
    },
    "acknowledgements": {
      "emailContactConsent": true,
      "noSecretsNoCustody": true,
      "memberAccessTerms": true
    }
  }'

curl -fsS 'https://gca-registration-api.gcagochina.workers.dev/gca/email-registrations?limit=20' \
  -H "authorization: Bearer $ADMIN_READ_TOKEN"

curl -fsS 'https://gca-registration-api.gcagochina.workers.dev/gca/contact-suppressions?limit=20' \
  -H "authorization: Bearer $ADMIN_READ_TOKEN"
```

## Current Public Site Behavior

`site/register.html` now tries the production Workers API first when loaded from `gcagochina.com`. If the API temporarily fails, the page exposes the official email fallback to avoid losing user registrations.

`site/unsubscribe.html` posts contact-suppression requests to the same Workers API when loaded from `gcagochina.com`. If the API temporarily fails, it exposes the official email fallback so a user can still request removal from future contact exports.

`site/gca/member-access/index.html` posts account intake and wallet-verification requests to the same Workers API. The wallet check is a read-only Base Mainnet `eth_call`; it writes eligible D1 ledger records but does not request wallet signatures, transactions, custody, or automatic token transfers.
