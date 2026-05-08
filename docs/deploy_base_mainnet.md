# Base Mainnet Deployment

This workspace is separate from `/Users/abc/Desktop/web3_radar`.

## Network

- Network: Base Mainnet
- Chain ID: `8453` (`0x2105`)
- RPC: `https://mainnet.base.org`
- Explorer: `https://basescan.org`

## Token

- Name: `GCA`
- Symbol: `GCA`
- Decimals: `18`
- Fixed supply: `1000000000`
- Minting: disabled

## MetaMask Browser Deploy

Use the mainnet-only MetaMask deployment page so no private key is exported:

```bash
cd /Users/abc/Desktop/gca_token
.venv/bin/python -m http.server 5177 --bind 127.0.0.1
```

Open `http://127.0.0.1:5177/tools/metamask_deploy_base_mainnet.html`.

The page only allows Base Mainnet and requires typing `DEPLOY GCA MAINNET` before the deploy button is enabled. MetaMask will still show the final transaction confirmation, and the wallet owner must approve it manually.

## Source Verification

After deployment, verify the contract on BaseScan with:

- Compiler type: Solidity Standard JSON input
- Compiler version: `v0.8.24+commit.e11b9ed9`
- License: MIT
- Standard JSON input: `verification/GCAToken.standard-json-input.json`
- Constructor arguments: empty
