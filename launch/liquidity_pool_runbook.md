# GCA Liquidity Pool Runbook

This runbook prepares the liquidity step without executing any wallet transaction. Creating liquidity spends real assets and sets the initial market price.

## Recommended Venue

- Venue: Uniswap on Base
- Network: Base Mainnet
- Pair candidates: GCA / ETH or GCA / USDC
- GCA contract: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`

## Required Decisions

Before opening a pool, choose all of the following:

- Pair asset: ETH or USDC on Base
- GCA amount to deposit
- ETH or USDC amount to deposit
- Initial implied price
- Pool version and fee tier
- Slippage tolerance
- Whether LP position will be kept, transferred, or locked
- Public announcement timing

## Price Formula

Initial price is set by the first liquidity deposit:

`paired asset amount / GCA amount = paired asset price per GCA`

Example only, not a recommendation:

- Deposit: 10,000,000 GCA and 1 ETH
- Implied price: 0.0000001 ETH per GCA

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

Prepared. Not executed. Blocked on the owner's chosen pair asset, amounts, fee tier, and final wallet confirmation.
