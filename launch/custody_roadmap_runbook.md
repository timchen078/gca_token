# GCA Custody Roadmap Runbook

Use this runbook when a reviewer asks what GCA will do about reserve concentration, LP custody, or future lock evidence.

Public page: `https://gcagochina.com/custody-roadmap.html`

Machine-readable JSON: `https://gcagochina.com/custody-roadmap.json`

## Current status

- Reserve wallet: `0x5e8F84748612B913aAcC937492AC25dc5630E246`
- Reserve amount: `600,000,000 GCA`
- Reserve custody: normal owner-controlled wallet
- Reserve lock claimed: no
- Reserve multisig claimed: no
- LP lock claimed: no
- LP burn claimed: no
- Official market: Base Mainnet GCA/USDT
- Official pool: `0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`

## If asked by Blockaid, BaseScan, or a wallet reviewer

Send the custody roadmap with the risk-remediation plan:

```text
GCA has published a custody roadmap and evidence checklist:
https://gcagochina.com/custody-roadmap.html
https://gcagochina.com/custody-roadmap.json

This is a planning and evidence checklist only. We do not claim the reserve is locked, vested, or multisig-controlled. We do not claim LP is locked or burned. If a future custody upgrade is executed, we will publish the contract/address, transaction hash, custody policy, and unlock or ownership details before making any stronger claim.
```

## Evidence required before stronger claims

- Safe multisig: Safe address, owners, threshold, transfer hash, policy statement.
- Reserve lock or vesting: contract address, amount, beneficiary, unlock or vesting schedule, transaction hash.
- LP lock: provider or lock contract, pool or LP position identifier, transaction hash, owner or beneficiary, unlock date.
- Third-party audit: final report URL, auditor identity, date, scope, and unresolved findings if any.

## Do not say

- Do not say reserve is locked before an on-chain custody change.
- Do not say reserve is multisig-controlled before a published multisig transfer.
- Do not say LP is locked before verifiable lock evidence exists.
- Do not describe the current roadmap as an audit, security-vendor approval, or guarantee of market quality.
