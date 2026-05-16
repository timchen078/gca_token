# GCA Member Pre-Registration Runbook

This runbook keeps the current static member pre-registration flow operationally clear now that Web3 Radar has local wallet verification, a 100 credits ledger, and a GCA Member ledger, while the public page still waits for controlled HTTPS account UI.

## Current State

- Public page: `https://gcagochina.com/members.html`
- Page mode: static browser-only pre-registration
- Direct submission endpoint: not connected on the public static page
- Local operator backend: `tools/gca_member_backend.py`
- Local operator URL: `http://127.0.0.1:8787/members.html`
- Local operator console: `http://127.0.0.1:8787/operator.html`
- Local same-origin API: `POST /gca/pre-registrations`, `POST /gca/wallet-verifications`, `GET /gca/operator-summary`, `GET /gca/credit-ledger`, `GET /gca/member-ledger`, and `GET /gca/member-review`
- Fallback collection methods: copy packet, download JSON, or email packet to `GCAgochina@outlook.com`
- Public claim status: not connected
- Prepared Web3 Radar user access page: `/gca/member-access`
- Prepared Web3 Radar intake path: `/gca/pre-registrations`
- Prepared Web3 Radar wallet verification path: `/gca/wallet-verifications`
- Prepared Web3 Radar credit ledger path: `/gca/credit-ledger`
- Prepared Web3 Radar member ledger path: `/gca/member-ledger`
- Prepared Web3 Radar review path: `/gca/member-review`
- Published machine-readable program rules: `https://gcagochina.com/member-program.json`

The page can generate a local registration packet for:

- General waitlist
- Holder Bonus candidate: declared balance at or above 10,000 GCA
- GCA Member candidate: declared balance at or above 1,000,000 GCA, plus later public evidence that the wallet bought and continuously held the threshold for 30 days

## Local Operator Backend

Run:

```bash
.venv/bin/python tools/gca_member_backend.py --host 127.0.0.1 --port 8787
```

Then open `http://127.0.0.1:8787/members.html` for intake or `http://127.0.0.1:8787/operator.html` for the local operator console.

Local backend behavior:

- Serves the static `site/` pages.
- Exposes a local operator summary at `GET /gca/operator-summary` for pre-registration, wallet verification, credit ledger, member ledger, and support review counts.
- Enables same-origin `POST /gca/pre-registrations` only when the page is opened from `localhost` or `127.0.0.1`.
- Verifies the submitted wallet with read-only Base Mainnet `eth_call` / ERC-20 `balanceOf`.
- Writes append-only local JSONL files under `.gca_access_data/`.
- Creates a 100 Web3 Radar utility credits ledger record when the wallet holds at least 10,000 GCA.
- Creates a GCA Member ledger record when the wallet holds at least 1,000,000 GCA; it activates the member record only when the 30-day holding evidence is present and the public transaction hash format is valid.
- Keeps the 10,000 GCA member benefit as `pending_manual_reserve_transfer`; it never sends tokens automatically.
- Rejects sensitive field names such as private key, seed phrase, mnemonic, exchange API secret, withdrawal permission, recovery phrase, or one-time code.

This is a local operator backend, not a public production account system.

## Direct Submission Setup

When an external collection service is ready, set the `SUBMISSION_ENDPOINT` constant in `site/members.html`.

Allowed endpoint options:

- Formspree form endpoint
- Supabase Edge Function endpoint
- Web3 Radar account API endpoint after it is deployed behind the same official HTTPS origin or a reviewed same-origin reverse proxy
- Other HTTPS endpoint controlled by the project

Endpoint requirements:

- Accept JSON POST requests.
- Store only email, Telegram handle, Base wallet address, declared GCA balance, program intent, safety acknowledgements, and packet metadata.
- Do not ask for private keys, seed phrases, exchange API secrets, withdrawal permissions, or custody.
- Do not activate live benefits from submission alone.
- Return a 2xx response only after the packet is stored.
- Keep broad cross-origin writes blocked unless a separate security review approves a narrow origin policy.

## Web3 Radar Prepared Intake

Web3 Radar now has a local access bridge prepared:

- `GET /gca/member-access`
- `GET /radar/gca/member-access`
- `POST /gca/pre-registrations`
- `POST /radar/gca/pre-registrations`
- `POST /gca/wallet-verifications`
- `POST /radar/gca/wallet-verifications`
- `GET /gca/credit-ledger`
- `GET /radar/gca/credit-ledger`
- `GET /gca/member-ledger`
- `GET /radar/gca/member-ledger`
- `GET /gca/member-review`
- `GET /radar/gca/member-review`

Pre-registration stores a pending review record only. Wallet verification reads the queued wallet's GCA balance with an ERC-20 `balanceOf` call, then records one-time 100 utility credits for verified 10,000 GCA holders and GCA Member status plus one-time 10,000 GCA member benefit review for verified 1,000,000 GCA holders who also pass the 30-day holding-period review. None of these endpoints activate trading permission, order-size changes, leverage changes, live execution, or any risk-control bypass.

## Credit And Member Rules

- 100 Web3 Radar utility credits are planned as account-level service credits only.
- Credit use scope: reports, backtests, risk warnings, ENTRY_READY signal review, position calculators, or education access.
- Credit expiry: 180 days after ledger activation unless a later published policy extends it.
- Credits are not transferable and cannot be redeemed for cash, token claims, income, reimbursement, or trading permission.
- GCA Member status is planned as account-level service access only.
- The planned 10,000 GCA member benefit requires 1,000,000 GCA held for 30 consecutive days and must come from project or owner-held reserve, not new minting.
- Member balance refresh cadence: 30 days after activation, or earlier if the user requests a manual recheck.
- Member access scope: higher utility credit limits, member research notes, priority report queue, member training sessions, and priority support.
- Member status does not activate live trading, leverage, custody, withdrawals, voting control, lifetime access, or risk-control bypass.

## Review Workflow

1. Export or review submitted packets.
2. Deduplicate by email and wallet address.
3. Mark packet status as `received`.
4. Mark wallet verification status as `pending`.
5. Run wallet verification only for queued wallets and only through the Web3 Radar backend.
6. Confirm the credit and member ledgers show service-access records only.
7. Record support status as `received`, `wallet_pending`, `eligible`, `needs_more_information`, `rejected`, or `ledger_recorded`.
8. Use `GCAgochina@outlook.com` as the public support contact while the project does not have a separate support desk.
9. Treat 5-10 business days after controlled intake is live as a first-response target, not a guarantee.
10. Do not describe the public page as self-service claimable until the controlled HTTPS account UI is released.

## Public Boundary

Pre-registration, 100 utility credits, GCA Member status, and the planned 10,000 GCA member benefit are not cash benefits, income, reimbursement, trading permission, or risk-control bypass. They are account-level records only, and the member benefit is not self-service live.
