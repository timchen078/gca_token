# GCA Token Allocation Plan

## Current On-Chain Starting Point

The GCA contract is fixed-supply. At deployment, the full supply of `1,000,000,000 GCA` was minted once to the deployer wallet:

Contract:

`Base Mainnet / chainId 8453 / 0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`

Deployer wallet:

`0x18d007bcb6be029f8ccd7cb13e324aa21891092d`

This plan does not move tokens by itself. It documents the intended public allocation so future transfers can be checked against a written source of truth.

## Target Allocation

| Allocation | Amount | Percent | Status |
| --- | ---: | ---: | --- |
| Public circulation, ecosystem, and liquidity allocation | 700,000,000 GCA | 70% | Planned |
| Owner-held reserve | 300,000,000 GCA | 30% | Planned |

## Owner-Held Reserve

The `300,000,000 GCA` reserve is intended to be held by the owner/founder. It should be publicly disclosed and should not be described as circulating while held as a reserve.

Recommended custody path:

1. Move the reserve to a clearly labeled owner reserve wallet, Safe multisig, or lock/vesting contract.
2. Publish the reserve wallet or lock contract address after the transaction is complete.
3. Keep public materials clear that the reserve is owner-held and not a return promise, dividend right, or redeemable asset.

## Public Circulation Allocation

The `700,000,000 GCA` allocation is intended for public circulation, ecosystem, community, liquidity, and future public distribution. Not all of this amount is immediately circulating until on-chain transfers, liquidity additions, or distribution events actually occur.

Current executed liquidity:

- Venue: Uniswap v3 on Base Mainnet
- Pair: GCA/WETH
- Position token ID: `5087977`
- Pool address: `0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff`
- GCA deposited: `99999.99999999996738248`
- Transaction: `0xef94e020c8b431151b789ca3e96c45ab0c18d20d15bf8d7d543630f1370fc158`

## Circulating Supply Caution

Data providers can calculate circulating supply differently. Until the 300,000,000 GCA owner reserve is moved to a clearly labeled reserve wallet, multisig, or lock/vesting contract, public materials should say "target allocation" instead of claiming that exactly 700,000,000 GCA is currently circulating.

## Do Not Say

- 70% is already circulating unless the on-chain distribution proves it.
- The owner reserve is locked unless a lock or vesting contract is deployed and funded.
- The owner reserve guarantees support, returns, redemptions, or liquidity.
