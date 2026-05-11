# GCA Launch Status

## Done

- Base Mainnet token deployed.
- BaseScan source verification completed.
- BaseScan deployer-wallet ownership verification completed.
- MetaMask Base Mainnet token display confirmed.
- Canonical public profile drafted.
- Draft whitepaper created.
- BaseScan token information submission package prepared.
- 32x32 SVG logo created.
- Static website created.
- GitHub Pages custom domain configured for `https://gcagochina.com/`.
- DNS records for `gcagochina.com` configured in Cloudflare.
- GitHub Pages HTTPS certificate issued and Enforce HTTPS enabled.
- Public logo URL is live at `https://gcagochina.com/assets/gca-logo.svg`.
- Public whitepaper URL is live at `https://gcagochina.com/whitepaper.html`.
- Current public contact email `GCAgochina@outlook.com` is published on the official website for data platform verification.
- BaseScan token update was submitted with `cxy070800@gmail.com`; monitor that inbox while the BaseScan review is pending.
- BaseScan token update form submitted from the owner's browser session.
- BaseScan review follow-up runbook prepared.
- Token allocation plan updated: 400,000,000 GCA target public allocation and 600,000,000 GCA owner-held reserve.
- Owner reserve transfers completed: total 600,000,000 GCA moved to `0x5e8F84748612B913aAcC937492AC25dc5630E246`.
- Liquidity pool default plan selected.
- Earlier Base Mainnet Uniswap v3 GCA/WETH pilot liquidity position created as a historical record only.
- Official public market route updated to the Base Mainnet Uniswap v4 GCA/USDT pool.
- Audit scope prepared.
- Internal security review completed.
- Third-party audit outreach package prepared.
- Third-party audit quote requests submitted to QuillAudits, Hacken, and OpenZeppelin on 2026-05-10; no external audit has been commissioned, paid for, or completed yet.
- Owner decided on 2026-05-10 to defer third-party audit for now and revisit later if needed.
- Website updated with the Go China Access concept-stage project direction.
- Website updated with the GCA x Web3 Radar utility thesis: Go China macro narrative plus planned access to non-custodial quant risk reports, backtests, ENTRY_READY review, position sizing, and risk-control education.
- Verified first holder campaign backend documented: each registered user may verify one wallet holding at least 10,000 GCA and receive a one-time 100 Web3 Radar utility credits ledger record.
- Verified GCA Member backend documented: each registered user may verify one wallet holding at least 1,000,000 GCA and qualify for GCA Member status in the Web3 Radar member ledger.
- Member pre-registration page prepared at `https://gcagochina.com/members.html`; it generates local-only registration packets and does not create a live account.
- Member pre-registration page now has a configurable direct submission endpoint placeholder; collection remains copy/download/email until an approved HTTPS endpoint is configured.
- Web3 Radar local access bridge paths are prepared: `GET /gca/member-access`, `POST /gca/pre-registrations`, `POST /gca/wallet-verifications`, `GET /gca/credit-ledger`, `GET /gca/member-ledger`, and `GET /gca/member-review`; the public static page is not connected to them yet.
- Public utility thesis page prepared at `https://gcagochina.com/utility.html`.
- Public project status page prepared at `https://gcagochina.com/status.html`.
- Public listing kit and machine-readable project JSON prepared at `https://gcagochina.com/listing-kit.html` and `https://gcagochina.com/project.json`.
- Official token list JSON prepared at `https://gcagochina.com/tokenlist.json`.
- Data platform submission package prepared for DEX Screener, GeckoTerminal, CoinGecko, and CoinMarketCap.
- GeckoTerminal token info update runbook prepared.
- GeckoTerminal token info update submitted on 2026-05-09 with `GCAgochina@outlook.com`; owner completed OTP verification in the browser and GeckoTerminal confirmed the form was submitted successfully.
- GeckoTerminal token information update approved on 2026-05-11; the official website links to the GCA/USDT GeckoTerminal pool.
- Official Telegram channel created at `https://t.me/gcagochinaofficial`.
- Official Telegram channel photo updated and first public announcement posted on 2026-05-09.
- First official Telegram announcement pinned on 2026-05-10.
- Telegram channel runbook prepared.
- Small Base Mainnet Uniswap v3 buy/sell functional swap tests observed on 2026-05-10 and documented in `launch/swap_test_evidence.md`.
- Blockaid false-positive report submitted on 2026-05-10 for the MetaMask/Uniswap suspected-honeypot warning.
- Official buy guide page prepared at `https://gcagochina.com/buy.html`.
- Official market page prepared at `https://gcagochina.com/markets.html` to centralize the GCA/USDT pool, USDT contract, Uniswap, GeckoTerminal, DEX Screener, and market risk disclosures.
- Telegram replacement pinned buy announcement template prepared at `launch/telegram_pinned_buy_announcement.md`.

## Needs Owner Input Or External Service

- Wait for BaseScan review or an email reply to `cxy070800@gmail.com`.
- If BaseScan asks for supply details during review, use the updated 40/60 allocation and both reserve transfer transactions.
- Wait for stronger public activity and market volume before submitting CoinGecko or CoinMarketCap listing requests.
- Expose the Web3 Radar access bridge through controlled HTTPS account UI before describing report credits, backtest quotas, ENTRY_READY reviews, or calculators as public self-service token-gated features.
- Add public UI, spend/expiry rules, and support workflow before describing the 10,000 GCA holder bonus as claimable by users without operator help.
- Add public UI, refresh cadence, member benefit limits, and support workflow before describing the 1,000,000 GCA Member tier as self-service claimable by users.
- Configure a controlled HTTPS collection endpoint in `site/members.html` before asking users to rely on direct packet submission.
- Deploy the Web3 Radar GCA intake behind the same official HTTPS origin or a reviewed reverse proxy before enabling the public `Submit Packet` button.
- Add the official Telegram link to any BaseScan or GeckoTerminal follow-up if those reviewers ask for social links.
- Replace the Telegram pinned message with `launch/telegram_pinned_buy_announcement.md` when ready.
- Move the owner reserve to a Safe multisig or lock/vesting contract if stronger reserve assurances are needed.
- Archive any audit quote replies from QuillAudits, Hacken, or OpenZeppelin; do not approve payment while audit is deferred.
- Reopen third-party audit only if user trust, listings, partners, or larger liquidity make an external report necessary.

## Public Communication Rules

- BaseScan source and ownership verification are complete. The public BaseScan token profile update has been submitted, but it is not complete until BaseScan accepts and publishes it.
- GeckoTerminal token information update was approved on 2026-05-11. Keep linking users to the official GCA/USDT pool and do not submit duplicate updates unless project details change.
- Internal engineering review is complete, but no third-party audit has been completed.
- Audit quote requests have been submitted and then deferred by owner decision, but quote submission is not an audit and does not allow any public "audited" claim.
- Current official Uniswap GCA/USDT liquidity is starter-depth only; trades can have high price impact and slippage.
- Functional buy/sell swap tests do not remove wallet risk warnings and must not be described as proof of organic volume or deep liquidity.
- Blockaid report submission does not mean the warning has been removed; wait for Blockaid/MetaMask review or verify directly in the wallet UI.
- The owner reserve is in a normal owner-controlled wallet. Do not describe it as locked, vested, or multisig-controlled unless custody changes on-chain.
- The product direction is still concept-stage. Do not describe GCA as a finished platform or as having guaranteed utility.
- The Web3 Radar bridge has a local verified-access backend, but public self-service claiming is not live until controlled HTTPS account UI, support rules, and risk disclosures are released.
- The 10,000 GCA holder bonus must be described as 100 Web3 Radar utility credits only, not as cash, tokens, income, reimbursement, trading permission, or a way to bypass risk controls.
- The 1,000,000 GCA Member tier must be described as service access only, not as cash, tokens, income, reimbursement, voting control, guaranteed lifetime access, trading permission, or a way to bypass risk controls.
- Do not claim return promises, price stability, liquidity depth, or external audit completion.

## Owner Reserve

- Current amount after second reserve transfer: 600,000,000 GCA
- Wallet: `0x5e8F84748612B913aAcC937492AC25dc5630E246`
- First transfer transaction: `0x4c342e1f4c969d0a73018637b778d5a76bd05f54749ff1fd2d19327fd5c01c67`
- First transfer block: 45,739,653
- Second transfer transaction: `0xfffb674448abdbd3af45bb0a30c48e5fbb0e675542b971f031381254b5dc5317`
- Second transfer block: 45,779,081
- Custody type: normal owner-controlled wallet; not a lock, vesting contract, or multisig.

## Official Market Pool

- Venue: Uniswap v4 on Base Mainnet
- Pair: GCA/USDT
- Fee tier: 0.01%
- Pool address: `0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- Quote asset: Base USDT `0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2`
- GeckoTerminal: `https://www.geckoterminal.com/base/pools/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- DEX Screener: `https://dexscreener.com/base/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- Uniswap pool: `https://app.uniswap.org/explore/pools/base/0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0`
- Official swap route: `https://app.uniswap.org/swap?chain=base&inputCurrency=0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2&outputCurrency=0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`

## Canonical Production Identity

`Base Mainnet / chainId 8453 / 0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`

## Do Not Use As Production Identity

`Base Sepolia / chainId 84532 / 0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6`
