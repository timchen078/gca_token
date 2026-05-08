#!/usr/bin/env python3
"""Compile GCAToken and write deployable ABI/artifact files."""

from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=ResourceWarning)

try:
    from solcx import compile_standard, install_solc
except ImportError as exc:  # pragma: no cover - exercised by command-line users
    raise SystemExit(
        "Missing py-solc-x. Install with: "
        "python3 -m pip install -r requirements-token-dev.txt"
    ) from exc


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "token" / "contracts" / "GCAToken.sol"
CONFIG_PATH = ROOT / "token" / "config" / "gca_token.json"
BUILD_DIR = ROOT / "token" / "build"
ABI_PATH = BUILD_DIR / "GCAToken.abi.json"
ARTIFACT_PATH = BUILD_DIR / "GCAToken.artifact.json"
SOLC_VERSION = "0.8.24"
OPTIMIZER_RUNS = 200


def compile_gca_token() -> dict:
    source = SOURCE_PATH.read_text()
    install_solc(SOLC_VERSION)
    return compile_standard(
        {
            "language": "Solidity",
            "sources": {
                "token/contracts/GCAToken.sol": {
                    "content": source,
                }
            },
            "settings": {
                "optimizer": {
                    "enabled": True,
                    "runs": OPTIMIZER_RUNS,
                },
                "outputSelection": {
                    "*": {
                        "*": [
                            "abi",
                            "evm.bytecode.object",
                            "evm.deployedBytecode.object",
                        ]
                    }
                },
            },
        },
        solc_version=SOLC_VERSION,
    )


def build_artifact() -> tuple[list[dict], dict]:
    compiled = compile_gca_token()
    contract = compiled["contracts"]["token/contracts/GCAToken.sol"]["GCAToken"]
    bytecode = "0x" + contract["evm"]["bytecode"]["object"]
    deployed_bytecode = "0x" + contract["evm"]["deployedBytecode"]["object"]
    config = json.loads(CONFIG_PATH.read_text())

    artifact = {
        "contractName": config["contractName"],
        "source": config["source"],
        "compiler": {
            "version": SOLC_VERSION,
            "optimizer": {
                "enabled": True,
                "runs": OPTIMIZER_RUNS,
            },
        },
        "token": {
            "name": config["name"],
            "symbol": config["symbol"],
            "decimals": config["decimals"],
            "totalSupplyTokens": config["totalSupplyTokens"],
            "totalSupplyBaseUnits": config["totalSupplyBaseUnits"],
            "mintingEnabled": config["mintingEnabled"],
        },
        "constructorArgs": [],
        "recommendedFirstNetwork": config["recommendedFirstNetwork"],
        "abi": contract["abi"],
        "bytecode": bytecode,
        "deployedBytecode": deployed_bytecode,
        "bytecodeSha256": hashlib.sha256(bytecode.encode()).hexdigest(),
    }
    return contract["abi"], artifact


def main() -> None:
    abi, artifact = build_artifact()
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    ABI_PATH.write_text(json.dumps(abi, indent=2) + "\n")
    ARTIFACT_PATH.write_text(json.dumps(artifact, indent=2) + "\n")
    print(f"Wrote {ABI_PATH.relative_to(ROOT)}")
    print(f"Wrote {ARTIFACT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
