#!/usr/bin/env python3
"""Deploy GCAToken to Base Sepolia only."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    from web3 import Web3
except ImportError as exc:  # pragma: no cover - command-line dependency guard
    raise SystemExit(
        "Missing web3. Install with: "
        "python3 -m pip install -r requirements-token-dev.txt"
    ) from exc


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = ROOT / "token" / "build" / "GCAToken.artifact.json"
BASE_SEPOLIA_CHAIN_ID = 84532
CONFIRMATION = "I_UNDERSTAND_THIS_IS_TESTNET"


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def load_artifact() -> dict:
    return json.loads(ARTIFACT_PATH.read_text())


def build_deploy_transaction(w3: Web3, deployer: str, artifact: dict) -> dict:
    contract = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
    nonce = w3.eth.get_transaction_count(deployer)
    tx = contract.constructor().build_transaction(
        {
            "from": deployer,
            "nonce": nonce,
            "chainId": BASE_SEPOLIA_CHAIN_ID,
        }
    )

    gas_estimate = w3.eth.estimate_gas(tx)
    tx["gas"] = int(gas_estimate * 1.2)

    latest_block = w3.eth.get_block("latest")
    base_fee = latest_block.get("baseFeePerGas")
    if base_fee is not None:
        priority_fee = w3.to_wei(0.01, "gwei")
        tx["maxPriorityFeePerGas"] = priority_fee
        tx["maxFeePerGas"] = int(base_fee * 2 + priority_fee)
    else:
        tx["gasPrice"] = w3.eth.gas_price

    return tx


def main() -> int:
    if os.environ.get("CONFIRM_TESTNET_DEPLOY") != CONFIRMATION:
        raise SystemExit(
            "Set CONFIRM_TESTNET_DEPLOY=I_UNDERSTAND_THIS_IS_TESTNET to deploy."
        )

    rpc_url = required_env("BASE_SEPOLIA_RPC_URL")
    private_key = required_env("DEPLOYER_PRIVATE_KEY")

    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 20}))
    if not w3.is_connected():
        raise SystemExit("Could not connect to Base Sepolia RPC.")

    chain_id = w3.eth.chain_id
    if chain_id != BASE_SEPOLIA_CHAIN_ID:
        raise SystemExit(
            f"Refusing to deploy to chain {chain_id}; expected {BASE_SEPOLIA_CHAIN_ID}."
        )

    account = w3.eth.account.from_key(private_key)
    deployer = account.address
    artifact = load_artifact()
    tx = build_deploy_transaction(w3, deployer, artifact)
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

    print(f"Network: Base Sepolia ({BASE_SEPOLIA_CHAIN_ID})")
    print(f"Deployer: {deployer}")
    print(f"Transaction: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    print(f"Contract: {receipt.contractAddress}")
    print(f"Status: {receipt.status}")
    return 0 if receipt.status == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
