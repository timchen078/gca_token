# GCA Whitepaper

Version: 0.1

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

At launch, the full token supply is held by the deployer wallet:

`0x18d007bcb6be029f8ccd7cb13e324aa21891092d`

Any future treasury, liquidity, contributor, community, or ecosystem distribution should be executed only after a written allocation table exists and each transfer can be verified on-chain.

## Liquidity Approach

The recommended first pool is a Base Mainnet DEX pool paired against a Base asset such as ETH or USDC. The initial pool price is set by the ratio of GCA and the paired asset deposited into the pool. Adding liquidity requires wallet approvals and one or more irreversible on-chain transactions.

Before creating liquidity, define:

- Pair asset
- Amount of GCA
- Amount of paired asset
- Initial implied price
- Fee tier or pool type
- Whether liquidity will be locked, time-locked, or retained by the deployer
- Public communication plan

## Security Notes

The current contract has been source-verified on BaseScan and covered by repository tests for fixed supply, public ERC-20 functions, compiler output, deployment pages, and deployment records. This is not a substitute for a third-party audit.

## Risk Notice

GCA does not represent return guarantees, fee distributions, custody, or a right to redeem assets. Public materials should not describe GCA as an investment product or make price, yield, or liquidity guarantees.
