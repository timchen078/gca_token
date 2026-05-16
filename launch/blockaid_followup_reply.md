# GCA Blockaid Follow-up Reply

Use this only if Blockaid, MetaMask, Uniswap, or another wallet-security reviewer asks for additional information. Do not send duplicate reports without a reviewer request.

Public follow-up package:

- Page: `https://gcagochina.com/blockaid-followup.html`
- JSON: `https://gcagochina.com/blockaid-followup.json`
- Technical report: `https://gcagochina.com/technical-report.html`
- Reserve statement: `https://gcagochina.com/reserve-statement.html`
- Holder distribution: `https://gcagochina.com/holder-distribution.html`
- Risk remediation plan: `https://gcagochina.com/risk-remediation.html`
- Custody roadmap: `https://gcagochina.com/custody-roadmap.html`
- Wallet warning evidence: `https://gcagochina.com/wallet-warning.html`

## Copyable Reply

```text
Hello Blockaid team,

Thank you for reviewing GCA and for explaining the current risk factors.

Network: Base Mainnet / chainId 8453
Contract: 0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6
Official website: https://gcagochina.com/
Public Blockaid follow-up package: https://gcagochina.com/blockaid-followup.html
Machine-readable follow-up JSON: https://gcagochina.com/blockaid-followup.json
Internal technical report: https://gcagochina.com/technical-report.html
Reserve address statement: https://gcagochina.com/reserve-statement.html
Holder distribution disclosure: https://gcagochina.com/holder-distribution.html
Risk remediation plan: https://gcagochina.com/risk-remediation.html
Custody roadmap: https://gcagochina.com/custody-roadmap.html
Wallet warning evidence: https://gcagochina.com/wallet-warning.html
Official market route: Base Mainnet Uniswap v4 GCA/USDT
Official pool: 0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0

We understand the risk factors you listed:

1. Price volatility / high price impact
GCA currently has starter-depth liquidity. We disclose that trades can have high price impact and volatile execution prices. We do not claim price stability or price support.

2. LP lock
No LP lock is currently claimed. The custody roadmap lists the evidence required before any future LP-lock claim. If a future LP lock is executed, we will publish the lock platform, lock address, transaction hash, position identifier, unlock date, and custody details.

3. Supply concentration
The 600,000,000 GCA owner-held reserve is publicly disclosed at 0x5e8F84748612B913aAcC937492AC25dc5630E246, with two on-chain reserve transfer proofs. The holder distribution disclosure and custody roadmap record that concentration risk remains because the reserve is owner-controlled and is not currently locked, vested, or multisig-controlled.

4. Third-party audit
No third-party audit has been completed. We have published an internal technical report for reviewer triage, but we are not describing it as a Certik, Hacken, Trail of Bits, or other independent audit report.

Contract-level controls:
The GCA contract source is verified on BaseScan. The contract is fixed-supply and has no post-deployment mint function, owner/admin role, proxy, blacklist, pause function, transfer tax, hidden fee, custody path, withdrawal path, custom transfer restriction, or admin trading control.

Request:
Could you please review whether any suspected-honeypot or transfer-blocking label can be separated from the disclosed market-structure risks above? We accept that starter-depth liquidity, high price impact, unlocked LP status, owner-controlled reserve status, supply concentration, and missing third-party audit are current risks, and we do not ask those to be ignored.

Thank you.
GCA / Go China Access
GCAgochina@outlook.com
```

## Claims To Avoid

- Do not claim Blockaid, MetaMask, Uniswap, or wallet-security approval before vendor confirmation.
- Do not claim third-party audit completion before an independent report is published.
- Do not claim LP lock before a verifiable lock exists.
- Do not claim locked reserve before on-chain custody changes.
- Do not claim deep liquidity, price support, price stability, or return promises.
