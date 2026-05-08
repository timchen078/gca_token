# GCA Token Workspace

This is the standalone workspace for the GCA fixed-supply token.
It is intentionally separate from `/Users/abc/Desktop/web3_radar`.

See `token/README.md` for token parameters, safety notes, and deployment flow.

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-token-dev.txt
.venv/bin/python token/scripts/build_gca_artifact.py
.venv/bin/python -m unittest tests.test_gca_token_contract tests.test_gca_token_compile -v
```
