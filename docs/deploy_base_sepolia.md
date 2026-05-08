# Base Sepolia Deployment

This workspace is separate from `/Users/abc/Desktop/web3_radar`.

## One-Time Setup

```bash
cd /Users/abc/Desktop/gca_token
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-token-dev.txt
.venv/bin/python token/scripts/build_gca_artifact.py
.venv/bin/python -m unittest tests.test_gca_token_contract tests.test_gca_token_compile tests.test_gca_token_deploy_script -v
```

## Required Secrets

Set these only in your local shell or local `.env` file:

```bash
export BASE_SEPOLIA_RPC_URL="https://sepolia.base.org"
export DEPLOYER_PRIVATE_KEY="0x..."
export CONFIRM_TESTNET_DEPLOY="I_UNDERSTAND_THIS_IS_TESTNET"
```

Use a wallet that holds only Base Sepolia test ETH. Do not use a main wallet or any wallet that has mainnet funds.

## Deploy

```bash
.venv/bin/python token/scripts/deploy_base_sepolia.py
```

The script refuses to deploy unless the connected network reports chain ID `84532`.

## MetaMask Browser Deploy

If you prefer not to export a private key, use the local MetaMask deployment page:

```bash
cd /Users/abc/Desktop/gca_token
.venv/bin/python -m http.server 5177 --bind 127.0.0.1
```

Then open `http://127.0.0.1:5177/tools/metamask_deploy.html`, connect MetaMask, and deploy on Base Sepolia. The page only uses MetaMask RPC requests and never asks for a private key.

## Current Base Sepolia Deployment

- Contract: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- Transaction: `0xb7db856bd08dad76422d281eaa18c7bf9009ffb1d6263331507e411b76b8285e`
- Explorer: `https://sepolia.basescan.org/address/0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
- Source verification: verified on BaseScan with Solidity Standard JSON input, `v0.8.24+commit.e11b9ed9`, optimizer enabled with 200 runs, MIT license.
- Verification input: `verification/GCAToken.standard-json-input.json`
- Deployment record: `deployments/base-sepolia-gca.json`

## Remote Repository

After you create a separate GitHub repository for this token project:

```bash
cd /Users/abc/Desktop/gca_token
git remote add origin git@github.com:<owner>/<repo>.git
git push -u origin main
```
