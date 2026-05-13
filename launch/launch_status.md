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
- Public site health-check script prepared at `tools/check_public_site.py`; it checks official market identity, metadata files, member pre-registration, member program rules, and high-risk public-claim guardrails.
- GitHub Actions public site health-check workflow prepared to run `tools/check_public_site.py` manually, on a daily schedule, and after health-check workflow/script changes.
- GitHub Pages custom domain configured for `https://gcagochina.com/`.
- DNS records for `gcagochina.com` configured in Cloudflare.
- GitHub Pages HTTPS certificate issued and Enforce HTTPS enabled.
- GitHub Actions publishing workflow prepared to run the full validation suite and sync `site/` to the `gh-pages` branch after `main` site changes.
- Public logo URL is live at `https://gcagochina.com/assets/gca-logo.svg`.
- Public whitepaper URL is live at `https://gcagochina.com/whitepaper.html`.
- Current public contact email `GCAgochina@outlook.com` is published on the official website for data platform verification.
- BaseScan token update was submitted with `cxy070800@gmail.com`, returned by BaseScan as information-insufficient on 2026-05-13, and resubmitted on 2026-05-13.
- BaseScan token update resubmission submitted from the owner's browser session on 2026-05-13; the profile is awaiting BaseScan email/review.
- BaseScan review follow-up runbook prepared.
- BaseScan resubmission values recorded at `launch/basescan_resubmission_package.md` and `launch/basescan_resubmission_values.json`.
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
- Static member access preview page prepared at `https://gcagochina.com/gca/member-access/`; it can parse local packets and run read-only GCA balance previews, but it does not create accounts, submit data, or write ledger records.
- Public member program rules prepared at `https://gcagochina.com/member-program.json`, including 100 credit spend scope, 180-day credit expiry, 30-day member refresh cadence, and support status workflow.
- Public member ledger schema prepared at `https://gcagochina.com/member-ledger.html` and `https://gcagochina.com/member-ledger.json` for wallet verification, 100 credits ledger, GCA Member ledger, and support review records.
- Browser-only read-only GCA balance preview added to `https://gcagochina.com/members.html` using MetaMask `eth_call` / ERC-20 `balanceOf`; it does not sign messages, send transactions, submit packets, or create ledger records.
- Public support intake page and JSON prepared at `https://gcagochina.com/support.html` and `https://gcagochina.com/support.json` for support routing, safe packet handling, wallet-warning evidence, and no-sensitive-data boundaries.
- Public roadmap page and JSON prepared at `https://gcagochina.com/roadmap.html` and `https://gcagochina.com/roadmap.json` for concept-stage utility buildout, support intake, member verification, Web3 Radar access planning, external dependencies, and public claim boundaries.
- Public community kit page and JSON prepared at `https://gcagochina.com/community.html` and `https://gcagochina.com/community.json` for official Telegram and X links, safe announcement copy, X launch post drafts, moderator replies, and community claim boundaries.
- Public narrative system page and JSON prepared at `https://gcagochina.com/narrative.html` and `https://gcagochina.com/narrative.json` for Go China Access, China Narrative Radar, Liquidation Replay, ENTRY_READY Review, GCA Member Club, and Risk First Trading public language.
- Weekly Go China Radar pilot page and JSON prepared at `https://gcagochina.com/radar.html` and `https://gcagochina.com/radar.json` as the first reusable content format for narrative research and risk education.
- Public privacy notice and participation terms prepared at `https://gcagochina.com/privacy.html`, `https://gcagochina.com/privacy.json`, `https://gcagochina.com/terms.html`, and `https://gcagochina.com/terms.json` for pre-registration data handling, wallet verification boundaries, and planned account-level service access.
- Member pre-registration page now has a configurable direct submission endpoint placeholder; collection remains copy/download/email until an approved HTTPS endpoint is configured.
- Web3 Radar local access bridge paths are prepared: `GET /gca/member-access`, `POST /gca/pre-registrations`, `POST /gca/wallet-verifications`, `GET /gca/credit-ledger`, `GET /gca/member-ledger`, and `GET /gca/member-review`; the public static page is not connected to them yet.
- Public utility thesis page prepared at `https://gcagochina.com/utility.html`.
- Official verify page prepared at `https://gcagochina.com/verify.html` to centralize canonical contract, Base Mainnet chain ID, official GCA/USDT pool, website, Telegram, metadata files, and anti-scam link checks.
- Public project status page prepared at `https://gcagochina.com/status.html`.
- Public listing kit and machine-readable project JSON prepared at `https://gcagochina.com/listing-kit.html` and `https://gcagochina.com/project.json`.
- Public brand kit page and JSON prepared at `https://gcagochina.com/brand-kit.html` and `https://gcagochina.com/brand-kit.json` for logo assets, token metadata, colors, official links, and logo usage boundaries.
- Public on-chain proofs page and JSON prepared at `https://gcagochina.com/onchain-proofs.html` and `https://gcagochina.com/onchain-proofs.json` for deployment, source verification, reserve transfers, official GCA/USDT market route, and functional swap evidence.
- Public wallet warning evidence page and JSON prepared at `https://gcagochina.com/wallet-warning.html` and `https://gcagochina.com/wallet-warning.json` for Blockaid / MetaMask follow-up evidence, contract facts, and warning-status boundaries.
- Public wallet security profile prepared at `https://gcagochina.com/.well-known/wallet-security.json` for wallet-security reviewers that need fixed-supply, no-mint, no-tax, no-blacklist, no-custody, review-status, and official market facts in a stable JSON URL.
- Public token safety checklist prepared at `https://gcagochina.com/token-safety.html` and `https://gcagochina.com/token-safety.json` for human-readable and machine-readable wallet-security review.
- Public external review status page and JSON prepared at `https://gcagochina.com/external-reviews.html` and `https://gcagochina.com/external-reviews.json` for BaseScan, Blockaid / MetaMask, GeckoTerminal, DEX Screener, CoinGecko, CoinMarketCap, and audit status.
- Public reviewer kit page and JSON prepared at `https://gcagochina.com/reviewer-kit.html` and `https://gcagochina.com/reviewer-kit.json` for wallet-security, DEX interface, explorer, data-platform, and community moderator review.
- Public platform replies page and JSON prepared at `https://gcagochina.com/platform-replies.html` and `https://gcagochina.com/platform-replies.json` for copyable BaseScan, wallet-warning, metadata-correction, community, and listing-readiness replies.
- Public trust center page and JSON prepared at `https://gcagochina.com/trust.html` and `https://gcagochina.com/trust.json` for consolidated contract facts, review status, official market route, supply disclosure, and public claim boundaries.
- Public listing readiness page and JSON prepared at `https://gcagochina.com/listing-readiness.html` and `https://gcagochina.com/listing-readiness.json` to keep CoinGecko, CoinMarketCap, centralized exchange, and paid listing outreach deferred until market and public activity are stronger.
- Official token list JSON prepared at `https://gcagochina.com/tokenlist.json`.
- Public well-known token identity JSON and security contact files prepared at `https://gcagochina.com/.well-known/gca-token.json` and `https://gcagochina.com/.well-known/security.txt`.
- Data platform submission package prepared for DEX Screener, GeckoTerminal, CoinGecko, and CoinMarketCap.
- External review follow-up tracker prepared at `launch/external_review_followup_tracker.md`.
- GeckoTerminal token info update runbook prepared.
- GeckoTerminal token info update submitted on 2026-05-09 with `GCAgochina@outlook.com`; owner completed OTP verification in the browser and GeckoTerminal confirmed the form was submitted successfully.
- GeckoTerminal token information update approved on 2026-05-11; the official website links to the GCA/USDT GeckoTerminal pool.
- Official Telegram channel created at `https://t.me/gcagochinaofficial`.
- Official Telegram channel photo updated and first public announcement posted on 2026-05-09.
- First official Telegram announcement pinned on 2026-05-10.
- Telegram channel runbook prepared.
- Official X profile configured at `https://x.com/XXYRadar`.
- X profile runbook and first-post / pinned-post drafts prepared at `launch/x_profile_runbook.md`; no official X post has been published or pinned yet.
- Small historical Base Mainnet Uniswap v3 GCA/WETH buy/sell functional swap tests observed on 2026-05-10 and documented in `launch/swap_test_evidence.md`; current public market links remain centralized on the GCA/USDT pool.
- Blockaid false-positive report submitted on 2026-05-10 for the MetaMask/Uniswap suspected-honeypot warning.
- Blockaid false-positive follow-up submitted on 2026-05-13 with current GCA/USDT links, public wallet-warning evidence, and historical buy/sell test transactions; the Blockaid support portal returned HTTP 200 OK.
- Blockaid follow-up context updated to use the current GCA/USDT pool while keeping the old GCA/WETH transactions as historical functional evidence only.
- Official buy guide page prepared at `https://gcagochina.com/buy.html`.
- Official market page prepared at `https://gcagochina.com/markets.html` to centralize the GCA/USDT pool, USDT contract, Uniswap, GeckoTerminal, DEX Screener, and market risk disclosures.
- Official market quality page and JSON prepared at `https://gcagochina.com/market-quality.html` and `https://gcagochina.com/market-quality.json` to define legitimate market-growth actions and reject artificial activity, self-trading, wash trading, and misleading volume.
- Official supply and reserve page prepared at `https://gcagochina.com/supply.html` to explain fixed total supply, 40/60 target allocation, reserve wallet evidence, and circulating supply cautions.
- Public supply disclosure JSON prepared at `https://gcagochina.com/supply.json` for data platforms and reviewers that need machine-readable total supply, target allocation, reserve wallet, and custody boundaries.
- Official security page prepared at `https://gcagochina.com/security.html` to summarize fixed supply, no mint, no tax, no blacklist, no admin controls, source verification, internal review, residual risks, and third-party audit status.
- Official risk disclosure page prepared at `https://gcagochina.com/risk.html` to centralize early-stage, starter-liquidity, wallet-warning, audit, reserve-custody, utility-readiness, listing, and public-claim risks.
- Official FAQ page prepared at `https://gcagochina.com/faq.html` to answer wallet import, price display, risk warning, pool mechanics, supply, reserve, audit, and public-claim questions.
- Telegram replacement pinned buy announcement template prepared at `launch/telegram_pinned_buy_announcement.md`.

## Needs Owner Input Or External Service

- Wait for BaseScan email/review; do not submit duplicates unless BaseScan asks for corrections.
- Use `launch/basescan_resubmission_package.md` and `launch/basescan_resubmission_values.json` as the record of the 2026-05-13 BaseScan token update resubmission.
- Use `launch/external_review_followup_tracker.md` for BaseScan, Blockaid, GeckoTerminal, DEX Screener, CoinGecko, CoinMarketCap, and audit follow-up status before sending any new platform request.
- Use `https://gcagochina.com/brand-kit.html` and `https://gcagochina.com/brand-kit.json` when wallets, data platforms, moderators, or community posts need official GCA logo assets and metadata usage boundaries.
- Use `https://gcagochina.com/member-ledger.html` and `https://gcagochina.com/member-ledger.json` when Web3 Radar integration, support review, or community moderators need the published wallet verification and ledger data contract.
- Use `https://gcagochina.com/support.html` for official support routing, member packet handling, wallet-warning evidence intake, and data-platform correction context.
- Use `https://gcagochina.com/support.json` when reviewers, moderators, or integration code need machine-readable support intake boundaries.
- Use `https://gcagochina.com/roadmap.html` and `https://gcagochina.com/roadmap.json` when community members, moderators, or data reviewers ask what is live now, what is next, and what claims must remain off-limits.
- Use `https://gcagochina.com/community.html`, `https://gcagochina.com/community.json`, and `launch/x_profile_runbook.md` before posting Telegram or X announcements, preparing moderator replies, or giving community members official links.
- Use `https://gcagochina.com/privacy.html` before collecting member pre-registration packets or answering questions about data handling, custody, and wallet verification.
- Use `https://gcagochina.com/terms.html` before answering questions about participation boundaries, planned credits, GCA Member status, or the no-custody/no-outcome-promise boundary.
- If BaseScan asks for supply details during review, use the updated 40/60 allocation and both reserve transfer transactions.
- Use `https://gcagochina.com/supply.json` when a data platform asks for machine-readable supply, allocation, reserve-wallet, or circulating-supply context.
- Wait for stronger public activity and market volume before submitting CoinGecko or CoinMarketCap listing requests.
- Use `https://gcagochina.com/market-quality.html` before presenting market-growth updates or new liquidity actions.
- Use `https://gcagochina.com/onchain-proofs.html` and `https://gcagochina.com/onchain-proofs.json` when a reviewer asks for deployment, reserve, official market, or transaction proof.
- Use `https://gcagochina.com/wallet-warning.html` and `https://gcagochina.com/wallet-warning.json` if Blockaid, MetaMask, Uniswap, or another wallet-security reviewer asks for public evidence.
- Use `https://gcagochina.com/.well-known/wallet-security.json` if a wallet-security reviewer or automated metadata checker needs machine-readable security facts.
- Use `https://gcagochina.com/token-safety.html` and `https://gcagochina.com/token-safety.json` when a reviewer or community moderator needs a concise token safety checklist.
- Use `https://gcagochina.com/external-reviews.html` and `https://gcagochina.com/external-reviews.json` when a public reviewer asks for current BaseScan, Blockaid / MetaMask, GeckoTerminal, DEX Screener, CoinGecko, CoinMarketCap, or audit status.
- Use `https://gcagochina.com/reviewer-kit.html` and `https://gcagochina.com/reviewer-kit.json` when a reviewer wants one consolidated packet instead of separate proof, warning, market, brand, and status links.
- Use `https://gcagochina.com/platform-replies.html` and `https://gcagochina.com/platform-replies.json` when you need copyable replies for platform requests, wallet-warning evidence requests, metadata corrections, moderator responses, or listing-readiness questions.
- Use `https://gcagochina.com/trust.html` and `https://gcagochina.com/trust.json` when a platform, moderator, or wallet-security reviewer asks for a single public verification hub covering contract facts, official market route, supply disclosure, review status, and claim boundaries.
- Use `https://gcagochina.com/listing-readiness.html` and `https://gcagochina.com/listing-readiness.json` before any tracked-listing or exchange outreach; the current status is `not-ready`.
- Expose the Web3 Radar access bridge through controlled HTTPS account UI before describing report credits, backtest quotas, ENTRY_READY reviews, or calculators as public self-service token-gated features.
- Connect controlled HTTPS account UI before describing the 10,000 GCA holder bonus as claimable by users without operator help.
- Connect controlled HTTPS account UI before describing the 1,000,000 GCA Member tier as self-service claimable by users.
- Configure a controlled HTTPS collection endpoint in `site/members.html` before asking users to rely on direct packet submission.
- Deploy the Web3 Radar GCA intake behind the same official HTTPS origin or a reviewed reverse proxy before enabling the public `Submit Packet` button.
- Add the official Telegram and X links to any BaseScan or GeckoTerminal follow-up if those reviewers ask for social links.
- Replace the Telegram pinned message with `launch/telegram_pinned_buy_announcement.md` when ready.
- Publish the prepared X first post only after confirming the profile photo, website field, and verification link; pin only the official links post after it is live.
- Move the owner reserve to a Safe multisig or lock/vesting contract if stronger reserve assurances are needed.
- Archive any audit quote replies from QuillAudits, Hacken, or OpenZeppelin; do not approve payment while audit is deferred.
- Reopen third-party audit only if user trust, listings, partners, or larger liquidity make an external report necessary.

## Public Communication Rules

- BaseScan source and ownership verification are complete. The public BaseScan token profile update was returned as information-insufficient on 2026-05-13, resubmitted on 2026-05-13, and is not complete until BaseScan accepts and publishes it.
- GeckoTerminal token information update was approved on 2026-05-11. Keep linking users to the official GCA/USDT pool and do not submit duplicate updates unless project details change.
- Internal engineering review is complete, but no third-party audit has been completed.
- Audit quote requests have been submitted and then deferred by owner decision, but quote submission is not an audit and does not allow any public "audited" claim.
- Current official Uniswap GCA/USDT liquidity is starter-depth only; trades can have high price impact and slippage.
- Functional buy/sell swap tests do not remove wallet risk warnings and must not be described as proof of organic volume or deep liquidity.
- Blockaid report and follow-up submission do not mean the warning has been removed; wait for Blockaid/MetaMask review or verify directly in the wallet UI.
- The owner reserve is in a normal owner-controlled wallet. Do not describe it as locked, vested, or multisig-controlled unless custody changes on-chain.
- The product direction is still concept-stage. Do not describe GCA as a finished platform or as having guaranteed utility.
- The Web3 Radar bridge has a local verified-access backend, but public self-service claiming is not live until controlled HTTPS account UI, support rules, and risk disclosures are released.
- The public member page may preview a wallet's GCA balance with a read-only browser `eth_call`, but this is only an eligibility preview and not a ledger activation or claim approval.
- The support intake page is public. It states that current intake is manual, direct submit is not connected, and users should never send private keys, seed phrases, exchange API secrets, withdrawal permission, one-time codes, recovery phrases, custody requests, or fund-transfer requests.
- The roadmap page is public. It states that GCA is in concept-stage utility buildout, public self-service member claiming is not live, and external dependencies such as BaseScan profile review, wallet-warning review, audit completion, and tracked listings remain unresolved until confirmed by the relevant third party.
- The community kit is public. It gives safe announcement copy and moderator replies while forbidding claims about BaseScan profile approval, wallet-warning removal, external audit completion, deep liquidity, price support, listing approval, or trading outcomes.
- The privacy notice and participation terms are public. They state that the current static member page is local packet generation only and that no private key, seed phrase, exchange API secret, withdrawal permission, or custody request belongs in the GCA member flow.
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
