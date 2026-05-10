# GCA Member Pre-Registration Runbook

This runbook keeps the current static member pre-registration flow operationally clear until Web3 Radar has a real account, wallet verification, credit ledger, and membership ledger.

## Current State

- Public page: `https://gcagochina.com/members.html`
- Page mode: static browser-only pre-registration
- Direct submission endpoint: not configured
- Fallback collection methods: copy packet, download JSON, or email packet to `GCAgochina@outlook.com`
- Live entitlement status: not live

The page can generate a local registration packet for:

- General waitlist
- Holder Bonus candidate: declared balance at or above 10,000 GCA
- GCA Member candidate: declared balance at or above 1,000,000 GCA

## Direct Submission Setup

When an external collection service is ready, set the `SUBMISSION_ENDPOINT` constant in `site/members.html`.

Allowed endpoint options:

- Formspree form endpoint
- Supabase Edge Function endpoint
- Web3 Radar account API endpoint after the product is ready
- Other HTTPS endpoint controlled by the project

Endpoint requirements:

- Accept JSON POST requests.
- Store only email, Telegram handle, Base wallet address, declared GCA balance, program intent, safety acknowledgements, and packet metadata.
- Do not ask for private keys, seed phrases, exchange API secrets, withdrawal permissions, or custody.
- Do not activate live benefits from submission alone.
- Return a 2xx response only after the packet is stored.

## Review Workflow

1. Export or review submitted packets.
2. Deduplicate by email and wallet address.
3. Mark packet status as `received`.
4. Mark wallet verification status as `pending`.
5. Do not mark Holder Bonus or GCA Member benefits as active until Web3 Radar has released the access bridge and verification ledger.

## Public Boundary

Pre-registration is not a token rebate, cash benefit, income, reimbursement, trading permission, or risk-control bypass. It is an early contact and eligibility-intent packet only.
