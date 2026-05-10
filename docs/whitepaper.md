# GCA Whitepaper

Version: 0.5

Official buy guide: `https://gcagochina.com/buy.html`

Utility thesis: `https://gcagochina.com/utility.html`

## Summary

GCA is a fixed-supply ERC-20 token deployed on Base Mainnet. GCA currently stands for Go China Access, a concept-stage community direction focused on China-facing Web3 culture, bilingual education, public market narrative research, and planned access to non-custodial quant risk tools.

The contract creates the entire supply at deployment and does not include post-deployment minting, burning, taxes, blacklist logic, or privileged admin controls. The product roadmap is still being developed publicly, so GCA should not be described as a finished platform or as having guaranteed utility.

## Token Parameters

- Name: GCA
- Symbol: GCA
- Network: Base Mainnet
- Chain ID: 8453
- Contract: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- Decimals: 18
- Total supply: 1,000,000,000 GCA
- Source verification: verified on BaseScan

## Contract Design

The contract implements a compact ERC-20 surface:

- `balanceOf`
- `allowance`
- `transfer`
- `approve`
- `transferFrom`
- `Transfer` event
- `Approval` event

The supply is assigned to the deployer in the constructor. There is no owner role, no upgrade mechanism, no mint function, no burn function, no transfer tax, no blacklist, and no withdrawal path.

## Network Selection

GCA is deployed on Base Mainnet because Base is an EVM-compatible Layer 2 network that uses ETH for gas and supports common ERC-20 wallet and DEX workflows.

## Project Direction

The current public concept is Go China Access. The intended direction is to build a public community around China-facing Web3 activity, bilingual crypto education, creator/community access, curated research about market narratives, and practical trading-risk education.

The planned product bridge is to connect GCA with Web3 Radar-style non-custodial quant tooling. Suitable utility includes:

- Liquidation replay reports
- Risk-warning credits
- Backtest usage
- ENTRY_READY signal review
- Position-size calculators
- Subscription discounts
- Risk-control training

Near-term work should focus on:

- Creating official community channels
- Publishing a clearer community thesis
- Collecting feedback before committing to a specific product release
- Defining the Web3 Radar access bridge
- Keeping public disclosures accurate as the project evolves

This concept does not imply a price target, return promise, revenue share, or completed application.

## Planned Utility Boundaries

GCA should be positioned as an access and membership layer, not as a yield product. Token utility should unlock reports, credits, education, and research workflows. It should not distribute platform revenue, promise outcomes, provide custody, request withdrawal permission, or bypass trading risk checks.

## Distribution Status

At deployment, the full token supply was assigned to the deployer wallet:

`0x18d007bcb6be029f8ccd7cb13e324aa21891092d`

A starter Uniswap v3 GCA/WETH liquidity position has since been created on Base Mainnet, with LP NFT token ID `5087977` held by the deployer wallet.

The target allocation plan is:

| Allocation | Amount | Percent |
| --- | ---: | ---: |
| Public circulation, ecosystem, and liquidity allocation | 400,000,000 GCA | 40% |
| Owner-held reserve | 600,000,000 GCA | 60% |

The 600,000,000 GCA reserve has been transferred to a separate owner reserve wallet through two on-chain transfers:

- Owner reserve wallet: `0x5e8F84748612B913aAcC937492AC25dc5630E246`
- First reserve transfer transaction: `0x4c342e1f4c969d0a73018637b778d5a76bd05f54749ff1fd2d19327fd5c01c67`
- First reserve transfer block: 45,739,653
- Second reserve transfer transaction: `0xfffb674448abdbd3af45bb0a30c48e5fbb0e675542b971f031381254b5dc5317`
- Second reserve transfer block: 45,779,081

The owner-held reserve should not be described as circulating while held as a reserve. This wallet is a normal owner-controlled wallet, not a lock, vesting contract, or Safe multisig. The 40/60 split remains a target allocation plan for public reporting. Future treasury, liquidity, contributor, community, or ecosystem transfers should be executed only after each transfer can be verified on-chain.

## Liquidity Approach

The initial live liquidity position is a Base Mainnet Uniswap v3 GCA/WETH pool with a 1% fee tier and full-range liquidity.

- Position token ID: `5087977`
- Pool address: `0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff`
- Transaction: `0xef94e020c8b431151b789ca3e96c45ab0c18d20d15bf8d7d543630f1370fc158`
- Deposited GCA: `99999.99999999996738248`
- Deposited ETH/WETH: `0.000999901772375952`

This is starter liquidity only. The current pool is shallow, so trades can have high price impact, wide slippage, and volatile execution prices.

Market reference links:

- DEX Screener pair: `https://dexscreener.com/base/0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff`
- GeckoTerminal pool: `https://www.geckoterminal.com/base/pools/0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff`
- CoinMarketCap DexScan pool: `https://dex.coinmarketcap.com/base/0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff/`
- Uniswap v3 liquidity position: `https://app.uniswap.org/positions/v3/base/5087977`

## Security Notes

The current contract has been source-verified on BaseScan and covered by repository tests for fixed supply, public ERC-20 functions, compiler output, deployment pages, and deployment records. An internal engineering review is complete. This is not a substitute for a third-party audit, and no third-party audit has been completed.

Third-party audit quote requests were submitted to QuillAudits, Hacken, and OpenZeppelin on 2026-05-10, then deferred by owner decision. GCA should not be described as audited, externally audited, or audit-approved unless an independent auditor later provides a verifiable report.

## BaseScan Token Profile Status

BaseScan source verification and deployer-wallet ownership verification are complete. The public BaseScan token profile update has been submitted and is awaiting BaseScan review.

## Official Contact

Project contact email: `GCAgochina@outlook.com`

Official Telegram: `https://t.me/gcagochinaofficial`

## Risk Notice

GCA does not represent return guarantees, fee distributions, custody, or a right to redeem assets. Public materials should not describe GCA as an investment product or make price, yield, audit, or liquidity guarantees.
