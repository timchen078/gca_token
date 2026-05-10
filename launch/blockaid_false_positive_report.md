# Blockaid / MetaMask False Positive Report

## Status

Submitted on 2026-05-10 through the Blockaid `Mistake` false-positive form at `https://report.blockaid.io/mistake` from the owner's browser session.

Submission confirmation page: `https://report.blockaid.io/submittionSuccessfully`

Observed confirmation text: `Report Sent` and `Thank you for reporting! We'll review it thoroughly`.

This report is for risk-provider review only. It is not a claim that the warning has been removed.

## Form Values

- Domain: `gcagochina.com`
- Chain: `Base Mainnet / chainId 8453`
- Wallet: `MetaMask / Uniswap token warning`
- Address: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- Email: `GCAgochina@outlook.com`

## Report Message

```text
GCA on Base Mainnet appears to be flagged as a suspected honeypot / suspicious token in MetaMask or Uniswap via Blockaid, but the token contract is a simple fixed-supply ERC-20 and the Base Mainnet Uniswap v3 pool has processed both buy and sell swaps.

Token: GCA / Go China Access
Network: Base Mainnet
Chain ID: 8453
Contract: 0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6
BaseScan: https://basescan.org/address/0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6
Official website: https://gcagochina.com/
Whitepaper: https://gcagochina.com/whitepaper.html

Pool: Uniswap v3 GCA/WETH
Pool address: 0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff
GeckoTerminal: https://www.geckoterminal.com/base/pools/0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff

Observed buy test: 0xf79e52ea56a299a30c2d297be99c970295864ed262c01fdcb7e3f60ca669b040
Observed sell test: 0x0ff618062abc6e28933699d4e3bd723026f8505e4a0155db3068073b6fdc86e7

Contract facts: fixed supply 1,000,000,000 GCA; no post-deployment mint function; no owner/admin role; no proxy or upgrade path; no blacklist; no pause function; no transfer tax or hidden fee; no custody or withdrawal path; source verified on BaseScan.

Please review this as a possible false positive.
```

## Evidence Links

- Functional swap evidence: `launch/swap_test_evidence.md`
- Internal security review: `audit/gca_internal_security_review.md`
- Audit status: `audit/third_party_audit_package.json`
- Public website: `https://gcagochina.com/`
- Whitepaper: `https://gcagochina.com/whitepaper.html`

## Follow-Up Rules

- Do not claim that Blockaid or MetaMask removed the warning until the warning is gone in the wallet UI.
- Do not claim that a false-positive report means the token is safe, audited, or approved.
- If Blockaid asks for more evidence, provide the BaseScan source verification, buy/sell test transactions, and the internal review file.
