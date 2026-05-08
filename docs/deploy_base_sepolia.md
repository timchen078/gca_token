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

## Remote Repository

After you create a separate GitHub repository for this token project:

```bash
cd /Users/abc/Desktop/gca_token
git remote add origin git@github.com:<owner>/<repo>.git
git push -u origin main
```
