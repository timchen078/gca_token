# GCA Mainnet Public Profile

## Canonical Token Facts

- Token name: GCA
- Token symbol: GCA
- Network: Base Mainnet
- Chain ID: 8453
- Contract address: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- Decimals: 18
- Total supply: 1,000,000,000 GCA
- Source status: verified on BaseScan
- Deployer: `0x18d007bcb6be029f8ccd7cb13e324aa21891092d`
- Deployment transaction: `0xae8ae4d0bd89c03b39946564a5b63bb20cd38879a1aa1fdcb20a6f1c4802e74e`
- BaseScan contract: `https://basescan.org/address/0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- BaseScan transaction: `https://basescan.org/tx/0xae8ae4d0bd89c03b39946564a5b63bb20cd38879a1aa1fdcb20a6f1c4802e74e`

## Public Contract Description

GCA is a fixed-supply ERC-20 token deployed on Base Mainnet. GCA currently stands for Go China Access, a concept-stage community direction focused on China-facing Web3 culture, bilingual education, public market narrative research, and planned access to non-custodial quant risk tools. The practical product direction is still being developed publicly.

The contract creates 1,000,000,000 GCA at deployment and includes no post-deployment minting, burning, taxes, blacklist, or admin controls.

## Target Allocation

- Public circulation, ecosystem, and liquidity allocation: 400,000,000 GCA (40%)
- Owner-held reserve: 600,000,000 GCA (60%)

The 600,000,000 GCA owner-held reserve has been moved to a separate publicly disclosed wallet:

- Owner reserve wallet: `0x5e8F84748612B913aAcC937492AC25dc5630E246`
- First reserve transfer transaction: `https://basescan.org/tx/0x4c342e1f4c969d0a73018637b778d5a76bd05f54749ff1fd2d19327fd5c01c67`
- First reserve transfer block: 45,739,653
- Second reserve transfer transaction: `https://basescan.org/tx/0xfffb674448abdbd3af45bb0a30c48e5fbb0e675542b971f031381254b5dc5317`
- Second reserve transfer block: 45,779,081

This is a normal owner-controlled wallet. It is not a lock, vesting contract, or Safe multisig. Do not claim that the reserve is locked unless it is later moved to a lock/vesting contract or a published multisig with the correct disclosure.

The full fixed supply was minted to the deployer wallet at deployment. The 40/60 split remains a target allocation plan for public reporting. Do not claim that exactly 400,000,000 GCA is currently circulating until reserve treatment and public distribution are accepted by the relevant data provider and visible on-chain.

## Official Contact

- Project contact email: `GCAgochina@outlook.com`
- Official Telegram: `https://t.me/gcagochinaofficial`
- The contact email is publicly listed on the official website for data platform verification.

## Project Direction

- Current concept: Go China Access
- Status: concept-stage community project
- Intended themes: China-facing Web3 culture, Go China macro narrative research, community access, bilingual education, risk-control education, and curated public information
- Planned Web3 Radar bridge: liquidation replay reports, risk-warning credits, realistic backtest usage, ENTRY_READY signal review, position-size calculators, subscription discounts, and risk-control training
- Planned first campaign: each registered user may verify one wallet holding at least 10,000 GCA and receive a one-time 100 Web3 Radar utility credits bonus after the access bridge is live
- Planned GCA Member tier: each registered user may verify one wallet holding at least 1,000,000 GCA and qualify for GCA Member status after the access bridge is live

Do not describe the current project as having a finished product, guaranteed utility, guaranteed market demand, return promise, or revenue distribution model.
Do not describe planned holder benefits or GCA Member status as cash, tokens, income, reimbursement, voting control, guaranteed lifetime access, trading permission, or a way to bypass Web3 Radar risk controls.

## BaseScan Token Profile Status

Source verification and deployer-wallet ownership verification are complete. The public BaseScan token profile update was submitted from the owner's browser session on 2026-05-09 and is awaiting BaseScan review.

Do not describe the BaseScan token profile as complete or visible until BaseScan accepts and publishes the submitted update.

## Liquidity Status

Starter liquidity is live on Base Mainnet:

- Venue: Uniswap v4
- Pair: GCA/USDT
- Fee tier: 0.01%
- Pool address: `0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- Quote asset: Base USDT `0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2`

The pool is shallow, so trades can have high price impact and slippage.

Market reference links:

- DEX Screener pair: `https://dexscreener.com/base/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- GeckoTerminal pool: `https://www.geckoterminal.com/base/pools/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- Uniswap pool: `https://app.uniswap.org/explore/pools/base/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- Official swap route: `https://app.uniswap.org/swap?chain=base&inputCurrency=0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2&outputCurrency=0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`

## Audit Status

Internal engineering review is complete. Third-party audit quote requests were submitted to QuillAudits, Hacken, and OpenZeppelin on 2026-05-10, then deferred by owner decision. No third-party audit has been completed. Do not describe GCA as externally audited unless an independent auditor provides a report or public verification page.

## Same Address Notice

The Base Mainnet and Base Sepolia deployments currently use the same contract address:

`0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`

This is possible because contract addresses are derived from deployment data on each chain. Treat the chain ID as part of the identity. For production references, always publish:

`Base Mainnet / chainId 8453 / 0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`

Do not publish the Sepolia explorer link as the production token link.

## Risk Notice

GCA does not represent return guarantees, fee distributions, custody, or a right to redeem assets. Users should verify the contract, chain, audit status, and pool details before interacting.
