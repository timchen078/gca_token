# GCA Audit Scope

## Current Status

Repository tests, BaseScan source verification, and internal security review are complete. No third-party audit has been completed.

## Contract Scope

- `token/contracts/GCAToken.sol`
- Compiler: `v0.8.24+commit.e11b9ed9`
- Optimizer: enabled, 200 runs
- Standard JSON input: `verification/GCAToken.standard-json-input.json`
- Deployed Base Mainnet contract: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`

## Review Checklist

- Fixed supply cannot change after deployment.
- No owner, admin, proxy, upgrade, mint, burn, blacklist, tax, custody, or withdrawal path exists.
- Transfers revert on insufficient balance and zero recipient.
- Allowances decrease on `transferFrom`.
- `Transfer` and `Approval` events are emitted for state changes.
- Constructor assigns total supply to the deployer and emits the initial `Transfer`.

## Third-Party Audit Request Template

Please review the GCA fixed-supply ERC-20 contract and deployed bytecode on Base Mainnet. The goal is to confirm that the verified source matches the deployed bytecode, the total supply is fixed, and no hidden privileged control, minting, withdrawal, blacklist, tax, or upgrade behavior exists.

Contract: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`

Network: Base Mainnet, chain ID 8453

Source file: `token/contracts/GCAToken.sol`

## Internal Review

Internal report: `audit/gca_internal_security_review.md`

This can be shared with an external reviewer as context, but it must not be marketed as a third-party audit.
