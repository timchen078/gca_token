# GCA Reserve Address Statement

Prepared for wallet-security, DEX-interface, explorer, and data-platform review.

Public page:

- Reserve statement page: `https://gcagochina.com/reserve-statement.html`
- Reserve statement JSON: `https://gcagochina.com/reserve-statement.json`

## Token

- Project: GCA / Go China Access
- Network: Base Mainnet
- Chain ID: `8453`
- Contract: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- Total supply: `1,000,000,000 GCA`
- Decimals: `18`

## Reserve Address

- Owner reserve wallet: `0x5e8F84748612B913aAcC937492AC25dc5630E246`
- Owner-held reserve amount: `600,000,000 GCA`
- Owner-held reserve percent: `60%`
- Target public / ecosystem / liquidity allocation: `400,000,000 GCA`
- Target public / ecosystem / liquidity allocation percent: `40%`

## On-chain Transfer Proofs

The 600,000,000 GCA reserve was moved from the deployer wallet to the disclosed reserve wallet through two Base Mainnet transfers:

1. `300,000,000 GCA`
   - Transaction: `0x4c342e1f4c969d0a73018637b778d5a76bd05f54749ff1fd2d19327fd5c01c67`
   - BaseScan: `https://basescan.org/tx/0x4c342e1f4c969d0a73018637b778d5a76bd05f54749ff1fd2d19327fd5c01c67`
   - Block: `45,739,653`

2. `300,000,000 GCA`
   - Transaction: `0xfffb674448abdbd3af45bb0a30c48e5fbb0e675542b971f031381254b5dc5317`
   - BaseScan: `https://basescan.org/tx/0xfffb674448abdbd3af45bb0a30c48e5fbb0e675542b971f031381254b5dc5317`
   - Block: `45,779,081`

## Custody Disclosure

The reserve wallet is publicly disclosed and separate from the deployer wallet. It is a normal owner-controlled wallet.

The reserve is not currently:

- locked
- vested
- multisig-controlled
- burned
- controlled by an independent custodian

This disclosure is intended to make the reserve wallet and transfer history explicit for reviewers. It does not remove concentration risk by itself.

## LP Lock Boundary

No LP lock is currently claimed.

If a future LP lock is executed, the project should publish:

- lock platform
- lock contract or custody address
- transaction hash
- locked LP position identifier
- unlock date
- owner/custody details

Until that exists, public materials must not describe GCA liquidity as locked.

## Reviewer Summary

The reserve is disclosed as a separate owner-held wallet rather than hidden circulation. The public 40/60 split is a target allocation disclosure. Data platforms may still calculate circulating supply differently until they accept reserve treatment and publish their own methodology.

Safe statements:

- GCA has a publicly disclosed owner-held reserve wallet.
- Two on-chain transfers moved 600,000,000 GCA to the disclosed reserve wallet.
- The reserve wallet is separate from the deployer wallet.
- The reserve is owner-controlled and not currently locked, vested, or multisig-controlled.
- No LP lock is currently claimed.

Do not claim:

- reserve lock before on-chain custody changes
- LP lock before a verifiable LP lock is executed
- burned supply before a burn transaction exists
- external audit approval before an independent report is published
- deep liquidity, price support, or return promises
