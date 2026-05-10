# GCA Token Allocation Plan

## Current On-Chain Starting Point

The GCA contract is fixed-supply. At deployment, the full supply of `1,000,000,000 GCA` was minted once to the deployer wallet:

Contract:

`Base Mainnet / chainId 8453 / 0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`

Deployer wallet:

`0x18d007bcb6be029f8ccd7cb13e324aa21891092d`

This plan documents the intended public allocation and the executed owner-reserve transfers so future transfers can be checked against a written source of truth.

## Target Allocation

| Allocation | Amount | Percent | Status |
| --- | ---: | ---: | --- |
| Public circulation, ecosystem, and liquidity allocation | 400,000,000 GCA | 40% | Target allocation |
| Owner-held reserve | 600,000,000 GCA | 60% | Transferred to owner reserve wallet |

## Owner-Held Reserve

The `600,000,000 GCA` reserve is held by the owner/founder in a separate publicly disclosed wallet. It should not be described as circulating while held as a reserve.

Reserve custody:

1. Reserve wallet: `0x5e8F84748612B913aAcC937492AC25dc5630E246`
2. First transfer transaction: `0x4c342e1f4c969d0a73018637b778d5a76bd05f54749ff1fd2d19327fd5c01c67`
3. First transfer block: `45739653`
4. Second transfer transaction: `0xfffb674448abdbd3af45bb0a30c48e5fbb0e675542b971f031381254b5dc5317`
5. Second transfer block: `45779081`
6. Current reserve wallet balance after the second transfer: `600,000,000 GCA`
7. Keep public materials clear that the reserve is owner-held and not a return promise, dividend right, or redeemable asset.

This is the minimum custody approach: a normal owner-controlled wallet. It is not a lock, vesting contract, or Safe multisig.

## Public Circulation Allocation

The `400,000,000 GCA` allocation is intended for public circulation, ecosystem, community, liquidity, and future public distribution. Not all of this amount is immediately circulating until on-chain transfers, liquidity additions, or distribution events actually occur.

Current official market pool:

- Venue: Uniswap v4 on Base Mainnet
- Pair: GCA/USDT
- Fee tier: 0.01%
- Pool address: `0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- Quote asset: Base USDT `0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2`
- GeckoTerminal: `https://www.geckoterminal.com/base/pools/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- DEX Screener: `https://dexscreener.com/base/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- Official swap route: `https://app.uniswap.org/swap?chain=base&inputCurrency=0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2&outputCurrency=0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`

## Circulating Supply Caution

Data providers can calculate circulating supply differently. The 600,000,000 GCA owner reserve is now visible in a separate wallet, but public materials should still say "target allocation" unless a data provider accepts the reserve treatment and the rest of the distribution is visible on-chain.

## Do Not Say

- 40% is already circulating unless the on-chain distribution proves it.
- The owner reserve is locked unless a lock or vesting contract is deployed and funded.
- The owner reserve is controlled by a multisig unless it is moved to a Safe or another published multisig.
- The owner reserve guarantees support, returns, redemptions, or liquidity.
