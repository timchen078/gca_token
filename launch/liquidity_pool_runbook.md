# GCA Liquidity Pool Runbook

This runbook prepares the liquidity step without executing any wallet transaction. Creating liquidity spends real assets and sets the initial market price.

## Recommended Venue

- Venue: Uniswap on Base
- Network: Base Mainnet
- Pair candidates: GCA / ETH or GCA / USDC
- GCA contract: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`

## Required Decisions

The default launch decision is now:

- Pair asset: ETH on Base
- Pool version: Uniswap v3
- Fee tier: 1%
- Range: full range
- GCA amount: 100,000 GCA
- ETH amount: 0.001 ETH
- Initial implied price: 0.00000001 ETH per GCA
- Implied fully diluted value: 10 ETH
- LP position custody: deployer wallet until a separate locking plan is chosen

This is a small current-wallet pilot that preserves ETH for gas while creating a real Base Mainnet pool. Scale options with the same implied price are stored in `launch/liquidity_plan.json`.

## Price Formula

Initial price is set by the first liquidity deposit:

`paired asset amount / GCA amount = paired asset price per GCA`

Selected default:

- Deposit: 100,000 GCA and 0.001 ETH
- Implied price: 0.00000001 ETH per GCA
- Implied fully diluted value: 10 ETH

## Wallet Steps

1. Open the official Uniswap app.
2. Switch wallet network to Base.
3. Start a new liquidity position.
4. Select the pair asset on Base.
5. Paste the GCA contract address: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`.
6. Enter the chosen GCA and pair-asset amounts.
7. Review initial price, fee tier, slippage, and resulting LP position.
8. Approve GCA spending only for the amount needed.
9. Add liquidity only after the final wallet transaction details match the written plan.
10. Save the pool transaction hash in `deployments/` after completion.

## Safety Rules

- Do not approve unlimited GCA spend unless there is a written reason.
- Do not create liquidity on Base Sepolia when intending a production pool.
- Do not publish a pool link until the transaction is confirmed on Base Mainnet.
- Do not promise price stability, yield, or guaranteed liquidity depth.
- Keep enough ETH in the wallet for gas after approvals and pool creation.

## Status

Planned. Not executed. Blocked only on final wallet approvals and live Uniswap transaction review.
