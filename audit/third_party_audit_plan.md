# GCA Third-Party Audit Plan

## Status

Third-party audit is not complete. Quote requests were submitted to QuillAudits, Hacken, and OpenZeppelin on 2026-05-10, but no auditor has been selected, paid, or commissioned.

Owner decision on 2026-05-10: defer third-party audit for now and revisit later only if the project needs an external report for user trust, listings, partners, or larger liquidity.

Do not publish "audited", "third-party audited", "externally audited", or an auditor logo until an independent auditor provides a signed report or public verification page that names the GCA Base Mainnet contract.

## Recommended Scope

Ask the auditor to review:

- Contract: `token/contracts/GCAToken.sol`
- Network: Base Mainnet
- Contract address: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- Compiler: `v0.8.24+commit.e11b9ed9`
- Optimizer: enabled, 200 runs
- Standard JSON input: `verification/GCAToken.standard-json-input.json`
- Internal review context: `audit/gca_internal_security_review.md`

The main objective is to independently verify:

- The BaseScan-verified source matches the deployed bytecode.
- Total supply is fixed at `1,000,000,000 GCA`.
- No post-deployment minting exists.
- No owner/admin role exists.
- No proxy or upgrade path exists.
- No blacklist, pause, transfer tax, hidden fee, custody, or withdrawal path exists.
- ERC-20 transfer and allowance behavior is correct.

Out of scope unless separately quoted:

- Token legal classification
- Market/liquidity strategy
- Website, social accounts, wallets, or operational security
- Exchange listing or data platform approval
- Treasury custody review beyond identifying the owner-held reserve wallet

## Shortlist

| Auditor | Best Fit | Official Inquiry Path | Notes |
| --- | --- | --- | --- |
| OpenZeppelin | Highest brand credibility for smart-contract audit claims | `https://www.openzeppelin.com/security-audits` | Strong reputation; likely higher cost and may be overkill for one simple fixed-supply token. |
| Hacken | Practical commercial smart-contract audit quote | `https://hacken.io/a/services/blockchain-security/smart-contract-security-audit/` | Broad Web3 audit provider with request-audit flow. |
| QuillAudits | Cost/turnaround-sensitive token audit quote | `https://www.quillaudits.com/pricing` | Public pricing/estimate flow; useful for a small ERC-20 scope. |
| Quantstamp | Established Web3 security firm | `https://quantstamp.com/` | Official site includes request-audit flow; likely quote-based. |
| ChainSecurity | High-end formal smart-contract review | `https://www.chainsecurity.com/` | Strong technical reputation; likely higher cost and better fit for larger DeFi protocols. |
| Trail of Bits | Top-tier security assessment | `https://trailofbits.com/services/software-assurance/blockchain/` | Excellent reputation; likely expensive and not always a fit for a tiny ERC-20-only scope. |

## Recommended Outreach Order

1. Archive any replies from QuillAudits, Hacken, or OpenZeppelin; do not approve payment while audit is deferred.
2. If the audit process is reopened later, compare quote cost, start date, delivery date, public report terms, Base Mainnet address coverage, and retest/remediation terms.
3. Choose and pay one auditor only after the owner explicitly reopens the audit process.
4. Use Quantstamp, ChainSecurity, or Trail of Bits only if the project budget supports a more expensive review or if the token grows into a broader protocol.

## Minimum Acceptance Criteria

Before publicizing an audit:

- The report must name `GCA`, Base Mainnet, chain ID `8453`, and contract `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`.
- The report must identify the source or repository commit reviewed.
- The report must describe scope and exclusions.
- Any findings must be marked resolved, accepted, or explicitly acknowledged.
- The auditor must provide a signed PDF, public report URL, GitHub report, certificate page, or other verifiable official artifact.

## Public Claim Rules

Allowed before completion:

- "Third-party audit quote requests have been submitted."
- "Third-party audit is currently deferred."
- "Internal engineering review complete."
- "BaseScan source verification complete."

Allowed after completion only if true:

- "Third-party audit completed by [auditor name]."
- "Audit report: [official report URL]."

Never say:

- "Audited" before report delivery.
- "CertiK/OpenZeppelin/Hacken/QuillAudits approved" unless that exact auditor completed the review and gave a verifiable report.
- "No risk", "safe", "guaranteed", or "exploit-proof".
