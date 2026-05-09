# GCA Third-Party Audit Request

Use this text in auditor inquiry forms or email. Replace bracketed fields before sending.

## Subject

Quote request: fixed-supply ERC-20 audit for GCA on Base Mainnet

## Message

Hello,

I would like a quote and timeline for an independent smart-contract audit of GCA, a fixed-supply ERC-20 token deployed on Base Mainnet.

Project:

- Name: GCA
- Concept expansion: Go China Access
- Network: Base Mainnet
- Chain ID: 8453
- Contract: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- BaseScan: `https://basescan.org/address/0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- Website: `https://gcagochina.com/`
- Contact email: `GCAgochina@outlook.com`

Audit scope:

- Source file: `token/contracts/GCAToken.sol`
- Compiler: `v0.8.24+commit.e11b9ed9`
- Optimizer: enabled, 200 runs
- Standard JSON input: `verification/GCAToken.standard-json-input.json`
- Internal review context: `audit/gca_internal_security_review.md`

The goal is to independently verify that the deployed contract is a simple fixed-supply ERC-20 and that it has no post-deployment minting, owner/admin role, proxy/upgrade path, blacklist, pause, transfer tax, hidden fee, custody, or withdrawal path.

Please include in your quote:

- Estimated cost
- Estimated start date and delivery date
- Whether the final report can be public
- Whether the report will explicitly identify the Base Mainnet contract address
- Required repository format or documents
- Whether a retest/remediation round is included

Important context:

- The contract is already deployed and source-verified on BaseScan.
- The total supply is fixed at `1,000,000,000 GCA`.
- The current public allocation disclosure is 40% public/ecosystem/liquidity target allocation and 60% owner-held reserve.
- No third-party audit has been completed yet.

Thank you.

[Sender name]

## Attach Or Link

- `token/contracts/GCAToken.sol`
- `verification/GCAToken.standard-json-input.json`
- `audit/gca_internal_security_review.md`
- `launch/audit_scope.md`
- `docs/mainnet_public_profile.md`
