# GCA Technical Report

Prepared as an internal technical report for wallet-security, DEX-interface, explorer, and data-platform review.

This is not a third-party audit report. It should not be described as a Certik, Hacken, Trail of Bits, or other independent auditor report.

Public page:

- Technical report page: `https://gcagochina.com/technical-report.html`
- Technical report JSON: `https://gcagochina.com/technical-report.json`

## Token Identity

- Project: GCA / Go China Access
- Network: Base Mainnet
- Chain ID: `8453`
- Contract: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- Decimals: `18`
- Total supply: `1,000,000,000 GCA`
- BaseScan: `https://basescan.org/address/0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`

## Deployment

- Deployer: `0x18d007bcb6be029f8ccd7cb13e324aa21891092d`
- Deployment transaction: `0xae8ae4d0bd89c03b39946564a5b63bb20cd38879a1aa1fdcb20a6f1c4802e74e`
- BaseScan transaction: `https://basescan.org/tx/0xae8ae4d0bd89c03b39946564a5b63bb20cd38879a1aa1fdcb20a6f1c4802e74e`
- Deployment block: `45,735,688`
- Deployment time: `2026-05-08T17:18:43Z`

## Source Verification

- BaseScan source verification: complete
- Compiler: `v0.8.24+commit.e11b9ed9`
- Optimizer: enabled
- Optimizer runs: `200`
- License: MIT

## Contract Control Review

The GCA token contract is a fixed-supply ERC-20 contract. The reviewed public contract facts are:

- Fixed total supply: yes
- Post-deployment mint function: no
- Burn function: no
- Owner/admin role: no
- Proxy or upgrade path: no
- Blacklist function: no
- Pause function: no
- Transfer tax or hidden fee: no
- Custom transfer restrictions: no
- Custody or withdrawal path: no
- External call during transfer: no
- Admin trading controls: no

ERC-20 behavior:

- Standard transfers: yes
- Standard approvals: yes
- Standard transferFrom: yes
- Standard allowance: yes
- User tokens are not custodied by the token contract.
- Wallets can transfer tokens without project approval.

## Market And Liquidity Disclosure

- Official pair: GCA/USDT
- DEX: Uniswap v4
- Pool: `0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- Quote asset: USDT on Base
- USDT contract: `0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2`
- Liquidity status: starter-depth only
- LP lock claimed: no

Starter-depth liquidity can create high price impact and volatile execution prices. Public materials should continue to disclose this.

## Reserve Disclosure

- Owner-held reserve: `600,000,000 GCA`
- Reserve percent: `60%`
- Reserve wallet: `0x5e8F84748612B913aAcC937492AC25dc5630E246`
- Reserve statement: `https://gcagochina.com/reserve-statement.html`
- Reserve statement JSON: `https://gcagochina.com/reserve-statement.json`

The reserve is owner-controlled and is not currently locked, vested, or multisig-controlled.

## Risk Reviewer Notes

Honeypot-control finding:

The token contract does not include blacklist, pause, transfer-tax, admin-transfer, proxy-upgrade, or post-deployment mint controls that would normally create direct transfer-blocking or hidden-fee behavior.

Residual risks:

- starter-depth liquidity can create high price impact and volatile execution prices
- LP is not currently locked
- owner-held reserve remains owner-controlled
- supply concentration remains visible and should be disclosed
- no third-party audit has been completed

## Safe Summary For Blockaid Follow-up

GCA is a fixed-supply ERC-20 token on Base Mainnet. The source is verified on BaseScan. The contract has no post-deployment mint function, no owner/admin role, no proxy or upgrade path, no blacklist, no pause function, no transfer tax, no hidden fee, no custody path, and no withdrawal path.

The public official market route is the Base Mainnet Uniswap v4 GCA/USDT pool. Liquidity remains starter-depth only, and no LP lock is currently claimed.

The owner-held reserve wallet is publicly disclosed at `0x5e8F84748612B913aAcC937492AC25dc5630E246`. It holds the disclosed 600,000,000 GCA reserve through two Base Mainnet transfers. The reserve is owner-controlled and not currently locked, vested, or multisig-controlled.

This report is an internal technical report and should not be described as an independent third-party audit.
