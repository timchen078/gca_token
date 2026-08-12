# GCA Registration and Member Access Backend

This is the deployed backend package for the public GCA email registration form, contact suppression, live member access UI, redacted device-key account status, read-only wallet verification, 100-credit ledger records, and GCA Member ledger records.

The public website remains hosted on GitHub Pages. The write API is deployed on Cloudflare Workers + D1 and currently exposed as:

```text
https://gca-registration-api.gcagochina.workers.dev/gca/email-registrations
https://gca-registration-api.gcagochina.workers.dev/gca/contact-suppressions
https://gca-registration-api.gcagochina.workers.dev/gca/member-access
https://gca-registration-api.gcagochina.workers.dev/gca/account-status
https://gca-registration-api.gcagochina.workers.dev/gca/account-status/rotate
https://gca-registration-api.gcagochina.workers.dev/gca/account-status/recovery-requests
https://gca-registration-api.gcagochina.workers.dev/gca/account-status/recovery-approvals
https://gca-registration-api.gcagochina.workers.dev/gca/account-status/recover
https://gca-registration-api.gcagochina.workers.dev/gca/account-service-requests
https://gca-registration-api.gcagochina.workers.dev/gca/account-service-requests/status
https://gca-registration-api.gcagochina.workers.dev/gca/account-service-requests/follow-ups
https://gca-registration-api.gcagochina.workers.dev/gca/account-service-requests/delivery-receipts
https://gca-registration-api.gcagochina.workers.dev/gca/account-service-requests/cancellations
https://gca-registration-api.gcagochina.workers.dev/gca/wallet-verifications
https://gca-registration-api.gcagochina.workers.dev/gca/access-config
https://gca-registration-api.gcagochina.workers.dev/gca/service-request-reviews
https://gca-registration-api.gcagochina.workers.dev/gca/service-request-followups
https://gca-registration-api.gcagochina.workers.dev/gca/member-reviews
https://gca-registration-api.gcagochina.workers.dev/gca/holding-verifications
https://gca-registration-api.gcagochina.workers.dev/gca/member-benefit-transfers
```

The account-scoped service request, more-information follow-up, queued-request cancellation, completed-delivery receipt, token-protected append-only service review, reviewed delivery, credit usage, member review, holding-verification, and member-benefit transfer evidence routes are production-live. Cloudflare account authentication, D1 visibility, Worker deploy permission, remote D1 migrations, Worker deployment, public smoke, and admin read-only smoke checks passed for the latest Worker on 2026-08-10 UTC. Anonymous reads return HTTP 401 and token-protected admin reads return HTTP 200.

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
- 100 GCA AI Quant Access credit ledger record when the verified wallet holds at least 10,000 GCA
- queued GCA Member ledger record when the verified wallet holds at least 1,000,000 GCA
- user-submitted holding start date and public evidence transaction hash as a 30-day review preview
- member benefit status
- timestamps
- optional salted IP hash if `PRIVACY_HASH_SALT` is configured

`gca_member_access_v2` also accepts a browser-generated 256-bit device status key. The Worker stores only its SHA-256 hash in `gca_account_status_access` through migration `0009_account_status_access.sql`; the plaintext key remains on the user's device. `POST /gca/account-status` accepts `gca_account_status_v1` and the matching unexpired device key, then returns a redacted read-only account, wallet-verification, credit, member-review, and member-benefit snapshot.

`POST /gca/account-status/rotate` accepts `gca_account_status_rotation_v1`, the current valid device key, and a new browser-generated key. Migration `0010_account_status_rotation.sql` stores only current and previous SHA-256 hashes. The old key immediately loses status-read access and can retry only the same completed rotation for 15 minutes. Rotation does not change the account, wallet verification, credit ledger, member ledger, or any on-chain asset.

Migration `0011_account_status_recovery.sql` adds a registered-email, manual-review recovery queue. `POST /gca/account-status/recovery-requests` accepts the registered email, Base wallet, and a new browser-generated device key, but stores only the email hash and key hash and always returns the same `pending_if_account_matches` response shape. It never confirms whether an account exists, and a public request cannot cancel another request or issued credential. `GET /gca/account-status/recovery-requests` and `POST /gca/account-status/recovery-approvals` require `ADMIN_READ_TOKEN`. After the operator verifies control of the registered mailbox, approval of that exact request atomically supersedes the account's other pending or approved requests, returns a random recovery credential once, and stores only its SHA-256 hash; the credential expires after 24 hours. `POST /gca/account-status/recover` consumes that credential, activates the pre-committed new device key, immediately invalidates the old key, and renews status access for 365 days. It does not change the member account, wallet verification, credit ledger, member ledger, GCA balance, or any on-chain asset.

The status response excludes email, email hash, full wallet address, the device key, administrator data, operator notes, IP data, and user-agent data. It does not connect a wallet, request a signature, write an account or business-ledger record, or transfer GCA. If the key is lost, expired, or revoked, the member page can now submit the controlled recovery request; support still must verify the registered email before issuing the one-time credential.

`POST /gca/account-service-requests` accepts a device-key authenticated catalog request and queues it without reserving or deducting credits. `POST /gca/account-service-requests/status` returns the account's latest 25 redacted request records. Migration `0012_service_request_reviews.sql` adds append-only `gca_service_request_review_v1` decisions and links a request to at most one credit usage record. `GET/POST /gca/service-request-reviews` requires `ADMIN_READ_TOKEN`; delivery is valid only after an approved review and requires a non-sensitive `deliveryReference`. The delivered action takes the credit amount from the server catalog and commits the credit usage, ledger deduction, review, and delivered request status in one D1 batch. The deterministic client review ID makes exact retries idempotent, and the unique service-request link prevents a second deduction.

Migration `0015_service_request_followups.sql` adds a public `member_prompt` field to operator reviews and an append-only `gca_service_request_followups` table. A `needs_more_information` review must include a 10-500 character non-sensitive prompt; other decisions cannot include it, and the private `operatorNote` remains hidden. `POST /gca/account-service-requests/follow-ups` accepts `gca_account_service_request_followup_v1`, authenticates the account device key, verifies ownership plus a latest `needs_more_information` review, accepts 20-1200 characters, limits each request to five responses, and uses `clientFollowupId` for exact-retry idempotency. Submission returns the request to `queued_operator_review` without changing credits, wallets, tokens, membership, or trading permission. Account history returns only the public prompt, latest follow-up time, and count, never the follow-up response text. Authorized operators can read responses through token-protected `GET /gca/service-request-followups`.

Migration `0013_service_delivery_receipts.sql` adds a unique account receipt marker to completed service requests. `POST /gca/account-service-requests/delivery-receipts` accepts `gca_account_service_delivery_receipt_v1`, authenticates the browser device key, verifies that the request belongs to the matched account, and requires both a delivered request status and a completed latest operator review. The deterministic receipt ID makes retries idempotent. A receipt records only that the account confirmed receipt; it does not refund, reserve, or deduct credits, change account or member status, connect a wallet, request a signature, send a transaction, transfer tokens, or create trading permission.

Migration `0014_service_request_cancellations.sql` adds a unique account cancellation marker. `POST /gca/account-service-requests/cancellations` accepts `gca_account_service_request_cancellation_v1`, authenticates the browser device key, and verifies that the request belongs to the matched account. Cancellation is allowed only while the request remains queued and before any operator review exists. The deterministic cancellation ID makes retries idempotent. Cancellation is permanent and retains the audit row; it does not refund or restore credits, change account or member status, connect a wallet, request a signature, send a transaction, transfer tokens, or create trading permission.

Account history returns only the latest redacted decision, reason code, review time, public more-information prompt, latest follow-up time and count, delivery state, non-sensitive delivery reference after completed delivery, credits used, and remaining balance. It excludes reviewer identity, private operator notes, follow-up response text, email, full wallet address, device key, and full request body. The review and delivery flow never connects a wallet, requests a signature, sends a transaction, transfers GCA, or creates trading permission.

The submitted holding date and transaction hash do not prove continuous holding or activate GCA Member automatically. An operator must review the submitted evidence and record a decision through the token-protected member review route. Approval refreshes the current GCA balance at a safe Base block, combines Base Blockscout v2 transfer history with recent Base public RPC logs, reconstructs the observed minimum GCA balance over the prior 30 days, and fails closed unless the history is complete, internally consistent, and stays at or above 1,000,000 GCA.

Successful approval writes an append-only `gca_holding_verification_v1` evidence row through migration `0007_holding_history_verifications.sql`, links the evidence ID to the member review and member ledger, and exposes protected operator reads at `GET /gca/holding-verifications`. This is an observed public-history reconstruction, not a third-party audit, permanent guarantee, or claim that a public index can never be delayed. The flow remains read-only with respect to the wallet and never signs, sends a transaction, transfers GCA, or authorizes the separate 10,000 GCA member-benefit transfer.

After a manually completed reserve-wallet transfer, `GET/POST /gca/member-benefit-transfers` verifies and stores append-only `gca_member_benefit_transfer_v1` evidence through migration `0008_member_benefit_transfer_evidence.sql`. It requires an active member with linked holding evidence, a successful receipt at or below the Base safe block, the published reserve sender, the approved member recipient, the official GCA contract, and exactly 10,000 GCA in one matching Transfer log. It updates the member claim status in the same D1 batch as the evidence insert.

It does not collect wallet private keys, seed phrases, wallet passwords, exchange API secrets, withdrawal permissions, one-time codes, or remote-control access. It does not request wallet signatures or transactions for wallet verification. It does not automatically transfer GCA. A member approval does not authorize the 10,000 GCA member benefit; the transfer remains a separate manual reserve-wallet action, while the production route verifies only the transaction that already exists.

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
- Public redacted account status endpoint: `POST /gca/account-status`
- Public device-key rotation endpoint: `POST /gca/account-status/rotate`
- Public device recovery request endpoint: `POST /gca/account-status/recovery-requests`
- Admin device recovery queue endpoint: `GET /gca/account-status/recovery-requests`
- Admin device recovery approval endpoint: `POST /gca/account-status/recovery-approvals`
- Public device recovery completion endpoint: `POST /gca/account-status/recover`
- Public account service request endpoint: `POST /gca/account-service-requests`
- Public redacted account service history endpoint: `POST /gca/account-service-requests/status`
- Public more-information follow-up endpoint: `POST /gca/account-service-requests/follow-ups`
- Public completed-delivery receipt endpoint: `POST /gca/account-service-requests/delivery-receipts`
- Public queued-request cancellation endpoint: `POST /gca/account-service-requests/cancellations`
- Public wallet verification endpoint: `POST /gca/wallet-verifications`
- Public access config endpoint: `GET /gca/access-config`
- Admin wallet verification endpoint: `GET /gca/wallet-verifications`
- Admin credit ledger endpoint: `GET /gca/credit-ledger`
- Admin service request endpoint: `GET/POST /gca/service-requests` live and token-protected
- Admin service request review endpoint: `GET/POST /gca/service-request-reviews` live and token-protected
- Admin service request follow-up endpoint: `GET /gca/service-request-followups` live and token-protected
- Admin credit usage endpoint: `GET/POST /gca/credit-usage` live and token-protected
- Admin member ledger endpoint: `GET /gca/member-ledger`
- Admin member review endpoint: `GET/POST /gca/member-reviews` live and token-protected
- Admin holding verification endpoint: `GET /gca/holding-verifications` live and token-protected
- Admin member-benefit evidence endpoint: `GET/POST /gca/member-benefit-transfers` live and token-protected
- Member D1 migration: `cloudflare/gca-registration-worker/migrations/0003_member_access_ledgers.sql`
- Account status access migration: `cloudflare/gca-registration-worker/migrations/0009_account_status_access.sql`
- Account status rotation migration: `cloudflare/gca-registration-worker/migrations/0010_account_status_rotation.sql`
- Account status recovery migration: `cloudflare/gca-registration-worker/migrations/0011_account_status_recovery.sql`
- Service request review migration: `cloudflare/gca-registration-worker/migrations/0012_service_request_reviews.sql`
- Service delivery receipt migration: `cloudflare/gca-registration-worker/migrations/0013_service_delivery_receipts.sql`
- Service request cancellation migration: `cloudflare/gca-registration-worker/migrations/0014_service_request_cancellations.sql`
- Service request follow-up migration: `cloudflare/gca-registration-worker/migrations/0015_service_request_followups.sql`
- Credit usage D1 migration: `cloudflare/gca-registration-worker/migrations/0004_credit_usage_ledger.sql`
- Service request D1 migration: `cloudflare/gca-registration-worker/migrations/0005_service_requests.sql`
- Member review D1 migration: `cloudflare/gca-registration-worker/migrations/0006_member_reviews.sql`
- Holding-history D1 migration: `cloudflare/gca-registration-worker/migrations/0007_holding_history_verifications.sql`
- Member-benefit evidence D1 migration: `cloudflare/gca-registration-worker/migrations/0008_member_benefit_transfer_evidence.sql`
- Production member review operator tool: `tools/review_cloudflare_member.py`
- Production account recovery approval tool: `tools/approve_cloudflare_account_recovery.py`
- Production member-benefit evidence operator tool: `tools/record_cloudflare_member_benefit_transfer.py`
- Production service request review and delivery tool: `tools/review_cloudflare_service_request.py`
- Worker deploy readiness tool: `tools/check_gca_worker_deploy_readiness.py`
- Worker routes deployment record: `docs/gca_worker_pending_routes_deploy_handoff.md`
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

The future custom domain `api.gcagochina.com` still requires the GCA Worker account to manage the `gcagochina.com` DNS zone. The current Worker account does not contain that zone, so the production API continues to use the workers.dev address. Do not change the active custom-domain configuration until zone access is confirmed.

The current `wrangler.toml` includes the Cloudflare `account_id` so Wrangler does not need to auto-discover the account before deploy. If `wrangler whoami --json --account <account_id>`, `wrangler d1 list`, `wrangler deployments list --json`, or `wrangler deploy` returns `Authentication error [code: 10000]`, the active Cloudflare token/session is missing access to the configured account, D1 database, or Worker service. Re-authorize Wrangler or use an API token with access to the target account before publishing the Worker.

The deploy readiness report includes a `cloudflare-auth-session` check and an `authRecovery` section. Use that section to confirm whether the blocker is account authentication, D1 visibility, or Worker deployment permission. It does not write D1 records, deploy the Worker, read user ledgers, or print secrets.

From the repository root, the full readiness command is:

```bash
python3 tools/check_gca_worker_deploy_readiness.py --run-wrangler --run-cloudflare --require-deploy-auth
```

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
npm run deploy:readiness
npx wrangler deploy
```

The readiness command is safe to run before every deploy. It performs static checks, `wrangler deploy --dry-run`, account-authentication visibility, D1 visibility, and a read-only Worker deployment-permission check. It does not write D1 records, deploy the Worker, print `ADMIN_READ_TOKEN`, or read user ledgers. If a remote check fails, read the `authRecovery.safeNextActions` field before attempting migrations or deploy.

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

The consolidated public daily ops workflow at `.github/workflows/check-gca-daily-ops.yml` runs `tools/run_gca_daily_ops.py` in public-only mode with `--require-complete-public-observations`. It checks the website, registration API, official GCA/USDT market route, BaseScan public profile, and local BaseScan preflight together. A transient public observation failure returns a failed run so the workflow's bounded retry can collect a complete publication artifact. It does not pass `--include-member-ops` or `--include-holding-report`, and it never reads token-protected user records.

To refresh the public daily status page after a local daily ops run:

```bash
.venv/bin/python tools/run_gca_daily_ops.py \
  --summary-output /tmp/gca_daily_ops_summary.json \
  --update-public-status
```

The daily ops command calls `tools/build_gca_daily_status_snapshot.py` when `--update-public-status` is set. When the canonical `site/daily-status.html` and `site/daily-status.json` outputs are used, it also runs `tools/sync_basescan_daily_status_references.py` so the BaseScan reviewer pages, owner packets, validators, and test snapshots reference the same public status timestamp and public-profile check date. The snapshot flow removes local machine paths from published command strings and does not publish admin tokens, user records, wallet signatures, transactions, or private evidence files.

Check the alignment without editing files:

```bash
python3 tools/sync_basescan_daily_status_references.py --check --json
```

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

curl -fsS 'https://gca-registration-api.gcagochina.workers.dev/gca/member-reviews?limit=20' \
  -H "authorization: Bearer $ADMIN_READ_TOKEN"

curl -fsS 'https://gca-registration-api.gcagochina.workers.dev/gca/account-status/recovery-requests?status=pending&limit=20' \
  -H "authorization: Bearer $ADMIN_READ_TOKEN"
```

## Production Device Recovery Approval

The operator may approve a recovery request only after receiving the request ID from the account's registered mailbox and completing the manual identity review. Inspect the command first:

```bash
.venv/bin/python tools/approve_cloudflare_account_recovery.py --help
```

Issue the one-time credential only with all explicit confirmations:

```bash
.venv/bin/python tools/approve_cloudflare_account_recovery.py \
  --recovery-request-id gca_recovery_request_00000000000000000000 \
  --registered-email member@example.com \
  --operator-id gca-operator \
  --reason-code registered_email_verified \
  --confirm-registered-email-ownership \
  --confirm-manual-identity-review \
  --confirm-production-write
```

The command writes the one-time credential to an ignored local file under `.gca_access_data/account_recovery/` with mode `0600`; it does not print the credential or `ADMIN_READ_TOKEN`. Deliver that file's credential only to the verified registered email. Never ask the user for the browser-generated new device key, private key, seed phrase, wallet password, wallet signature, approval, or transaction. Reissuing a credential invalidates the prior credential, and successful completion consumes it permanently.

## Production Member Review

The public member-access route can queue a GCA Member record, but it cannot activate membership from a submitted date. After manually checking the public holding evidence, an operator records one of `approved`, `rejected`, or `needs_more_information` through the production route.

Inspect the command first:

```bash
.venv/bin/python tools/review_cloudflare_member.py --help
```

An approval requires both explicit confirmations:

```bash
.venv/bin/python tools/review_cloudflare_member.py \
  --member-ledger-id gca_member_00000000000000000000 \
  --decision approved \
  --reason-code holding_evidence_reviewed \
  --reviewer-id gca-operator \
  --confirm-evidence-reviewed \
  --confirm-production-write
```

Replace the sample ledger ID with the real token-protected `memberLedgerId`. The command refreshes the current balance with read-only Base RPC and writes an append-only review decision plus the resulting account/member status in one D1 batch transaction. It does not connect a wallet, request a signature, send a transaction, transfer GCA, or authorize the 10,000 GCA member benefit.

## Production Member Benefit Transfer Evidence

The operator must first complete the approved transfer manually from the published reserve wallet. Only after the Base transaction exists should the evidence command be used:

```bash
.venv/bin/python tools/record_cloudflare_member_benefit_transfer.py \
  --member-ledger-id gca_member_00000000000000000000 \
  --transaction-hash 0x0000000000000000000000000000000000000000000000000000000000000000 \
  --reviewer-id gca-operator \
  --reason-code approved_member_benefit \
  --confirm-manual-transfer-completed \
  --confirm-public-transaction-evidence \
  --confirm-production-write
```

Replace both sample identifiers with the real approved member ledger ID and public transaction hash. The Worker reads the Base safe block and transaction receipt, then fails closed unless the transaction succeeded and proves exactly one 10,000 GCA transfer from `0x5e8F84748612B913aAcC937492AC25dc5630E246` to the approved member wallet through the official GCA contract. The command never initiates, signs, authorizes, or broadcasts a transaction.

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
  --include-service-routes \
  --export-output .gca_access_data/cloudflare_member_access_export.json \
  --report-dir .gca_access_data/member_access_report \
  --support-queue-output .gca_access_data/member_access_report/gca_member_support_queue.csv \
  --summary-output .gca_access_data/gca_member_access_ops_summary.json
```

The service route option includes service requests, append-only operator reviews, account follow-ups, and linked credit usage. Public-redacted exports clear user service text, internal notes, member prompts, delivery references, reviewer identifiers, email, and display name while retaining public wallet evidence for on-chain review.

To rebuild reports from an existing complete export without reading Cloudflare:

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
  --include-service-routes \
  --summary-output .gca_access_data/gca_daily_ops_summary.json
```

To also record the daily 30-day GCA Member holding snapshot during that member-ops run, add `--include-holding-report`:

```bash
.venv/bin/python tools/run_gca_daily_ops.py \
  --include-member-ops \
  --include-service-routes \
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
    "packetVersion": "gca_member_access_v2",
    "statusAccessToken": "gca_status_<43_random_base64url_characters>",
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

After a successful v2 account submission, the same page stores the plaintext device key only in that browser and can call `POST /gca/account-status` for a redacted server snapshot. The browser keeps the latest redacted snapshot for up to 30 days; the server-side hashed access record expires after 365 days. A user who still has a valid key can rotate it from the same page. The pending new key is retained locally for up to 30 days so an interrupted request can be recovered without exposing either key.
