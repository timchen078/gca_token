# GCA Functional Swap Test Evidence

## Status

A small Base Mainnet Uniswap v3 buy/sell functional test was observed through the GeckoTerminal pool trade feed on 2026-05-10. This file is for transparency and support follow-up only.

This is not a market-making report, not proof of organic demand, not a third-party audit, and not evidence that wallet risk providers will remove warnings.

## Pool

- Network: Base Mainnet
- Pair: GCA/WETH
- Pool address: `0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff`
- Token address: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- GeckoTerminal pool: `https://www.geckoterminal.com/base/pools/0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff`

## Observed Test Trades

These transactions show that the pool has processed both GCA buys and GCA sells:

| Type | Transaction | Block | Observed amount | Approx. USD volume |
| --- | --- | ---: | --- | ---: |
| Buy | `0xf79e52ea56a299a30c2d297be99c970295864ed262c01fdcb7e3f60ca669b040` | 45,799,481 | 0.000854781725675161 WETH to 9,834.32791476174 GCA | $1.99 |
| Sell | `0x0ff618062abc6e28933699d4e3bd723026f8505e4a0155db3068073b6fdc86e7` | 45,799,470 | 19,484.8161504 GCA to 0.00244197168490071 WETH | $5.69 |
| Buy | `0x9e88f36125e0b54eb6d334b3159d6875909553e530dda49af4482d96401a05ac` | 45,799,458 | 0.00256344253410288 WETH to 20,832.8985203378 GCA | $5.97 |
| Sell | `0x2698cee454d22a7977231e7e57173038647c07261c09d8a93260bcbf0cc2d71e` | 45,799,442 | 19,041.01089723 GCA to 0.00208989561806073 WETH | $4.87 |

## Current Interpretation

- The pool has accepted both buy and sell swaps.
- The test supports a narrow functional claim: GCA has been bought and sold through the Base Mainnet Uniswap v3 pool.
- The test does not prove strong liquidity, organic market demand, external audit completion, token-list acceptance, or removal of Blockaid/MetaMask warnings.
- The pool remains starter-depth only and can still have high price impact and slippage.

## Safe Public Wording

Allowed:

`Small Base Mainnet Uniswap v3 buy/sell tests have been observed on-chain. The pool remains shallow and GCA has not completed a third-party audit.`

Do not say:

- `Risk warning removed`
- `No risk`
- `Safe to buy`
- `Audited`
- `Deep liquidity`
- `Organic volume proven`
- `Guaranteed tradable`
