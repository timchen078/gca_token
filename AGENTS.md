# AGENTS.md

## Project Scope

This workspace is only for the GCA fixed-supply token project.
Do not mix it with `/Users/abc/Desktop/web3_radar` or any trading-system code.

## Token Safety Rules

- Deploy to testnet before any mainnet deployment.
- Do not commit private keys, mnemonics, RPC secrets, or explorer API keys.
- Do not add withdrawal, custody, profit-sharing, guaranteed-return, tax, blacklist, hidden mint, or admin backdoor logic.
- Keep total supply fixed unless the project requirements explicitly change.
- Run compile and policy tests after every contract change.

## Verification

- Install development dependency: `.venv/bin/python -m pip install -r requirements-token-dev.txt`
- Build artifacts: `.venv/bin/python token/scripts/build_gca_artifact.py`
- Run checks: `.venv/bin/python -m unittest tests.test_gca_token_contract tests.test_gca_token_compile tests.test_gca_token_deploy_script -v`
