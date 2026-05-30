# GCA Member Pre-Registration Runbook

This runbook keeps the legacy static member pre-registration flow operationally clear now that GCA has public Workers + D1 account intake, read-only wallet verification, a 100 credits ledger path, and a GCA Member ledger path.

## Current State

- Public page: `https://gcagochina.com/members.html`
- Page mode: legacy static browser-only packet generator
- Live public account page: `https://gcagochina.com/gca/member-access/`
- Direct public submission endpoint: handled by the Workers + D1 member access page
- Local operator backend: `tools/gca_member_backend.py`
- Local operator URL: `http://127.0.0.1:8787/members.html`
- Local operator console: `http://127.0.0.1:8787/operator.html`
- Local same-origin API: `POST /gca/pre-registrations`, `POST /gca/wallet-verifications`, `GET /gca/operator-summary`, `GET /gca/credit-ledger`, `GET /gca/member-ledger`, `POST /gca/member-benefit-transfers`, `GET /gca/member-benefit-transfers`, and `GET /gca/member-review`
- Fallback collection methods: copy packet, download JSON, or email packet to `support@gcagochina.com`
- Public account and eligible ledger status: live through Workers + D1
- GCA user access page: `/gca/member-access`
- GCA intake path: `/gca/member-access`
- GCA wallet verification path: `/gca/wallet-verifications`
- GCA credit ledger path: `/gca/credit-ledger`
- GCA member ledger path: `/gca/member-ledger`
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
- Exposes a local operator summary at `GET /gca/operator-summary` for pre-registration, wallet verification, credit ledger, member ledger, member benefit transfer, and support review counts.
- Records manually completed 10,000 GCA member benefit transfers at `POST /gca/member-benefit-transfers` after an operator signs the transfer outside this app; it verifies the public transaction hash with read-only Base Mainnet `eth_getTransactionReceipt`, records the matching GCA `Transfer` evidence, and does not send tokens.
- Enables same-origin `POST /gca/pre-registrations` only when the page is opened from `localhost` or `127.0.0.1`.
- Verifies the submitted wallet with read-only Base Mainnet `eth_call` / ERC-20 `balanceOf`.
- Writes append-only local JSONL files under `.gca_access_data/`.
- Creates a 100 Web3 Radar utility credits ledger record when the wallet holds at least 10,000 GCA.
- Creates a GCA Member ledger record when the wallet holds at least 1,000,000 GCA; it activates the member record only when the 30-day holding evidence is present and the public transaction hash format is valid.
- Keeps the 10,000 GCA member benefit as `pending_manual_reserve_transfer`; it never sends tokens automatically.
- Rejects sensitive field names such as private key, seed phrase, mnemonic, exchange API secret, withdrawal permission, recovery phrase, or one-time code.

This is a local operator backend for testing and evidence export. Public account intake now uses the Cloudflare Workers + D1 path.

## Public Submission Setup

Use `https://gcagochina.com/gca/member-access/` for public account intake. The page posts to the Cloudflare Workers + D1 backend and stores only non-sensitive account, wallet, and review metadata. `site/members.html` remains a legacy packet generator and local-operator test surface.

## Web3 Radar Prepared Intake

GCA now has a public access bridge:

- `POST /gca/member-access`
- `POST /gca/wallet-verifications`
- `GET /gca/credit-ledger`
- `GET /gca/member-ledger`

Pre-registration stores a pending review record only. Wallet verification reads the queued wallet's GCA balance with an ERC-20 `balanceOf` call, then records one-time 100 utility credits for verified 10,000 GCA holders and GCA Member status plus one-time 10,000 GCA member benefit review for verified 1,000,000 GCA holders who also pass the 30-day holding-period review. None of these endpoints activate trading permission, order-size changes, leverage changes, live execution, or any risk-control bypass.

## Credit And Member Rules

- 100 Web3 Radar utility credits are account-level service credits only.
- Credit use scope: reports, backtests, risk warnings, ENTRY_READY signal review, position calculators, or education access.
- Credit expiry: 180 days after ledger activation unless a later published policy extends it.
- Credits are not transferable and cannot be redeemed for cash, token claims, income, reimbursement, or trading permission.
- GCA Member status is account-level service access only.
- The 10,000 GCA member benefit requires 1,000,000 GCA held for 30 consecutive days and must come from project or owner-held reserve, not new minting.
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
8. Use `support@gcagochina.com` as the public support contact while the project does not have a separate support desk.
9. Treat 5-10 business days after account intake as a first-response target, not a guarantee.
10. Do not describe the 10,000 GCA member benefit as automatic or self-service transferred.

## Public Boundary

Pre-registration, 100 utility credits, GCA Member status, and the 10,000 GCA member benefit are not cash benefits, income, reimbursement, trading permission, or risk-control bypass. They are account-level records only, and the member benefit remains manual review and reserve-wallet processing only.
