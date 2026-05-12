# GCA Member Pre-Registration Runbook

This runbook keeps the current static member pre-registration flow operationally clear now that Web3 Radar has local wallet verification, a 100 credits ledger, and a GCA Member ledger, while the public page still waits for controlled HTTPS account UI.

## Current State

- Public page: `https://gcagochina.com/members.html`
- Page mode: static browser-only pre-registration
- Direct submission endpoint: not connected on the public static page
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
- GCA Member candidate: declared balance at or above 1,000,000 GCA

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

Pre-registration stores a pending review record only. Wallet verification reads the queued wallet's GCA balance with an ERC-20 `balanceOf` call, then records one-time 100 utility credits for verified 10,000 GCA holders and GCA Member status for verified 1,000,000 GCA holders. None of these endpoints activate trading permission, order-size changes, leverage changes, live execution, or any risk-control bypass.

## Credit And Member Rules

- 100 Web3 Radar utility credits are planned as account-level service credits only.
- Credit use scope: reports, backtests, risk warnings, ENTRY_READY signal review, position calculators, or education access.
- Credit expiry: 180 days after ledger activation unless a later published policy extends it.
- Credits are not transferable and cannot be redeemed for cash, tokens, income, reimbursement, or trading permission.
- GCA Member status is planned as account-level service access only.
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

Pre-registration, 100 utility credits, and GCA Member status are not token rebates, cash benefits, income, reimbursement, trading permission, or risk-control bypass. They are service-access records only.
