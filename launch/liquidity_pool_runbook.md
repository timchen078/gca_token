# GCA Liquidity Pool Runbook

This runbook records the selected liquidity plan and the completed Base Mainnet execution. Creating liquidity spends real assets and sets the initial market price.

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

1. Opened the official Uniswap app.
2. Switched wallet network to Base.
3. Started a new v3 liquidity position.
4. Selected ETH/WETH as the pair asset on Base.
5. Pasted the GCA contract address: `0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`.
6. Entered 100,000 GCA with the matching ETH side computed by Uniswap.
7. Reviewed initial price, 1% fee tier, full-range bounds, and resulting LP position.
8. Reduced GCA spending approval from unlimited to 100,000 GCA.
9. Added liquidity after the final wallet transaction details matched the written plan.
10. Saved the pool transaction hash in `deployments/base-mainnet-gca-liquidity.json`.

## Safety Rules

- Do not approve unlimited GCA spend unless there is a written reason.
- Do not create liquidity on Base Sepolia when intending a production pool.
- Do not publish a pool link until the transaction is confirmed on Base Mainnet.
- Do not promise price stability, yield, or guaranteed liquidity depth.
- Keep enough ETH in the wallet for gas after approvals and pool creation.

## Status

Executed on Base Mainnet.

- Transaction: `0xef94e020c8b431151b789ca3e96c45ab0c18d20d15bf8d7d543630f1370fc158`
- Block: `45736696`
- Uniswap v3 position token ID: `5087977`
- Pool address: `0x79fc0b367adbd79118c664f5ee27eb6ff8cb69ff`
- Position owner: `0x18d007bcb6be029f8ccd7cb13e324aa21891092d`
- Deposited GCA: `99999.99999999996738248`
- Deposited ETH/WETH: `0.000999901772375952`
- Position link: `https://app.uniswap.org/positions/v3/base/5087977`
