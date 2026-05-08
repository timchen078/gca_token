# GCA Token

GCA is a fixed-supply ERC-20 token contract intended for testnet deployment first.

## Parameters

- Name: `GCA`
- Symbol: `GCA`
- Decimals: `18`
- Total supply: `1,000,000,000 GCA`
- Target allocation: `700,000,000 GCA` public circulation/ecosystem/liquidity and `300,000,000 GCA` owner-held reserve
- Minting after deploy: disabled
- Admin controls: none
- Production network: Base Mainnet
- Test network: Base Sepolia

## Safety Notes

- The contract has no withdrawal, custody, profit-sharing, guaranteed-return, tax, blacklist, or hidden mint logic.
- The deployer receives the full supply at deployment.
- Deploy only to testnet until legal, tokenomics, distribution, and security review are complete.
- Do not commit real private keys, RPC secrets, or block explorer API keys.

## Suggested Deployment Flow

1. Install the token dev dependency: `.venv/bin/python -m pip install -r requirements-token-dev.txt`
2. Compile and refresh ABI/artifacts: `.venv/bin/python token/scripts/build_gca_artifact.py`
3. Run token checks: `.venv/bin/python -m unittest tests.test_gca_token_contract tests.test_gca_token_compile tests.test_gca_token_deploy_script -v`
4. Deploy to Base Sepolia testnet with a wallet that holds only test ETH.
5. Verify the contract source on the explorer.
6. Transfer treasury/community/liquidity allocations from the deployer wallet only after a written distribution plan exists.
7. Deploy to mainnet only after external legal, tokenomics, and security review.

## Base Mainnet Parameters

- Chain ID: `8453`
- Contract: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- Explorer: `https://basescan.org/address/0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- Source verification: verified

## Base Sepolia Parameters

- Chain ID: `84532`
- Explorer: `https://sepolia.basescan.org`
- Public RPC documentation: `https://docs.base.org`

## Generated Files

- `token/build/GCAToken.abi.json`: ABI for wallets, dashboards, and deployment scripts.
- `token/build/GCAToken.artifact.json`: ABI, bytecode, compiler settings, token parameters, and bytecode hash.
