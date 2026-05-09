# GCA Whitepaper

Version: 0.4

## Summary

GCA is a fixed-supply ERC-20 token deployed on Base Mainnet. GCA currently stands for Go China Access, a concept-stage community direction focused on China-facing Web3 culture, creators, bilingual education, and public market narrative research.

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

The current public concept is Go China Access. The intended direction is to build a public community around China-facing Web3 activity, bilingual crypto education, creator/community access, and curated research about market narratives.

Near-term work should focus on:

- Creating official community channels
- Publishing a clearer community thesis
- Collecting feedback before committing to a specific product direction
- Keeping public disclosures accurate as the project evolves

This concept does not imply a price target, return promise, revenue share, or completed application.

## Distribution Status

At deployment, the full token supply was assigned to the deployer wallet:

`0x18d007bcb6be029f8ccd7cb13e324aa21891092d`

A starter Uniswap v3 GCA/WETH liquidity position has since been created on Base Mainnet, with LP NFT token ID `5087977` held by the deployer wallet.

The target allocation plan is:

| Allocation | Amount | Percent |
| --- | ---: | ---: |
| Public circulation, ecosystem, and liquidity allocation | 700,000,000 GCA | 70% |
| Owner-held reserve | 300,000,000 GCA | 30% |

The 300,000,000 GCA reserve has been transferred to a separate owner reserve wallet:

- Owner reserve wallet: `0x5e8F84748612B913aAcC937492AC25dc5630E246`
- Reserve transfer transaction: `0x4c342e1f4c969d0a73018637b778d5a76bd05f54749ff1fd2d19327fd5c01c67`
- Reserve transfer block: 45,739,653

The owner-held reserve should not be described as circulating while held as a reserve. This wallet is a normal owner-controlled wallet, not a lock, vesting contract, or Safe multisig. The 70/30 split remains a target allocation plan for public reporting. Future treasury, liquidity, contributor, community, or ecosystem transfers should be executed only after each transfer can be verified on-chain.

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

## BaseScan Token Profile Status

BaseScan source verification and deployer-wallet ownership verification are complete. The public BaseScan token profile update has been submitted and is awaiting BaseScan review.

## Official Contact

Project contact email: `GCAgochina@outlook.com`

Official Telegram: `https://t.me/gcagochinaofficial`

## Risk Notice

GCA does not represent return guarantees, fee distributions, custody, or a right to redeem assets. Public materials should not describe GCA as an investment product or make price, yield, audit, or liquidity guarantees.
