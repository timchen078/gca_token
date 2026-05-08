# GCA Whitepaper

Version: 0.2

## Summary

GCA is a fixed-supply ERC-20 token deployed on Base Mainnet. The contract creates the entire supply at deployment and does not include post-deployment minting, burning, taxes, blacklist logic, or privileged admin controls.

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

## Distribution Status

At deployment, the full token supply was assigned to the deployer wallet:

`0x18d007bcb6be029f8ccd7cb13e324aa21891092d`

A starter Uniswap v3 GCA/WETH liquidity position has since been created on Base Mainnet, with LP NFT token ID `5087977` held by the deployer wallet.

Any future treasury, liquidity, contributor, community, or ecosystem distribution should be executed only after a written allocation table exists and each transfer can be verified on-chain.

## Liquidity Approach

The initial live liquidity position is a Base Mainnet Uniswap v3 GCA/WETH pool with a 1% fee tier and full-range liquidity.

- Position token ID: `5087977`
- Pool address: `0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff`
- Transaction: `0xef94e020c8b431151b789ca3e96c45ab0c18d20d15bf8d7d543630f1370fc158`
- Deposited GCA: `99999.99999999996738248`
- Deposited ETH/WETH: `0.000999901772375952`

This is starter liquidity only. The current pool is shallow, so trades can have high price impact, wide slippage, and volatile execution prices.

## Security Notes

The current contract has been source-verified on BaseScan and covered by repository tests for fixed supply, public ERC-20 functions, compiler output, deployment pages, and deployment records. An internal engineering review is complete. This is not a substitute for a third-party audit, and no third-party audit has been completed.

## BaseScan Token Profile Status

BaseScan source verification and deployer-wallet ownership verification are complete. The public BaseScan token profile update is pending final form submission and BaseScan review.

## Official Contact

Project contact email: `cxy070800@gmail.com`

## Risk Notice

GCA does not represent return guarantees, fee distributions, custody, or a right to redeem assets. Public materials should not describe GCA as an investment product or make price, yield, audit, or liquidity guarantees.
