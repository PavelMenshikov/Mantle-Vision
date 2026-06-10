"""
Deploy AgentIdentity + SignalRecorder to Mantle Network.

Usage:
    python scripts/deploy_contracts.py [--network sepolia|mainnet]

Requires:
    - MANTLE_PRIVATE_KEY set in .env (must have MNT for gas)
    - MANTLE_RPC_URL set in .env
"""

import json
import os
import sys
import time
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from pathlib import Path

from eth_account import Account
from web3 import Web3

# ── Config ──────────────────────────────────────────────────────────────

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = PROJECT_DIR / "contracts"
BACKEND_DIR = PROJECT_DIR / "backend"
DOT_ENV = PROJECT_DIR / ".env"

# Load .env manually (avoid pydantic dependency in script)
env_vars = {}
if DOT_ENV.exists():
    for line in DOT_ENV.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip().strip('"').strip("'")

MANTLE_RPC_URL = env_vars.get("MANTLE_RPC_URL", "https://rpc.mantle.xyz")
MANTLE_CHAIN_ID = int(env_vars.get("MANTLE_CHAIN_ID", "5003"))
MANTLE_PRIVATE_KEY = env_vars.get("MANTLE_PRIVATE_KEY", "")

# ── Helpers ─────────────────────────────────────────────────────────────

def green(s):
    return f"\033[92m{s}\033[0m"

def yellow(s):
    return f"\033[93m{s}\033[0m"

def red(s):
    return f"\033[91m{s}\033[0m"

# ── Compile ─────────────────────────────────────────────────────────────

def find_openzeppelin():
    """Find @openzeppelin/contracts in node_modules."""
    search_paths = [
        CONTRACTS_DIR / "node_modules",
        PROJECT_DIR / "node_modules",
        Path(os.path.expanduser("~")) / "node_modules",
    ]
    for p in search_paths:
        oz = p / "@openzeppelin" / "contracts"
        if oz.exists():
            return str(oz.parent.parent)  # path to node_modules
    return None

def compile_contracts():
    """Compile AgentIdentity.sol and SignalRecorder.sol using solcx."""
    from solcx import compile_files, install_solc, get_installed_solc_versions

    print(yellow("⚙  Compiling Solidity contracts..."))

    # Ensure solc 0.8.25
    if "0.8.25" not in [str(v) for v in get_installed_solc_versions()]:
        print("  Downloading solc 0.8.25...")
        install_solc("0.8.25")

    oz_path = find_openzeppelin()
    remappings = []
    if oz_path:
        remappings = ["@openzeppelin=" + os.path.join(oz_path, "@openzeppelin")]
        print(f"  Found OpenZeppelin at: {oz_path}")
    else:
        print(red("  ❌ @openzeppelin/contracts not found in node_modules"))
        print("  Run: cd contracts && npm install")
        sys.exit(1)

    sources = [
        str(CONTRACTS_DIR / "AgentIdentity.sol"),
        str(CONTRACTS_DIR / "SignalRecorder.sol"),
    ]

    compiled = compile_files(
        sources,
        solc_version="0.8.25",
        output_values=["abi", "bin"],
        import_remappings=remappings,
        optimize=True,
        optimize_runs=200,
    )

    print(green("  ✅ Contracts compiled successfully"))
    return compiled

# ── Deploy ──────────────────────────────────────────────────────────────

_nonce_lock = [None]  # mutable shared state

def deploy_contract(w3, abi, bytecode, args=None, label=""):
    """Deploy a contract and wait for receipt."""
    account = Account.from_key(MANTLE_PRIVATE_KEY)
    nonce = _nonce_lock[0] if _nonce_lock[0] is not None else w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    construct_txn = Contract.constructor(*args) if args else Contract.constructor()

    tx = construct_txn.build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 3_000_000,
        "gasPrice": gas_price,
        "chainId": MANTLE_CHAIN_ID,
    })

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"  ⏳ {label} deploying... tx: {tx_hash.hex()}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.get("status") != 1:
        raise RuntimeError(f"{label} deployment failed: {receipt}")
    print(green(f"  ✅ {label} deployed at: {receipt['contractAddress']}"))
    _nonce_lock[0] = nonce + 1
    return receipt["contractAddress"]

def update_env(key, value):
    """Update .env file with a new key=value pair."""
    if not DOT_ENV.exists():
        DOT_ENV.write_text(f"{key}={value}\n")
        return

    lines = DOT_ENV.read_text().splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    DOT_ENV.write_text("\n".join(lines) + "\n")
    print(f"  📝 Updated .env: {key}={value}")

# ── Main ────────────────────────────────────────────────────────────────

def main():
    network = "sepolia" if "sepolia" in MANTLE_RPC_URL else "mainnet"
    print(yellow(f"\n{'='*60}"))
    print(f"  Mantle Vision — Contract Deployment")
    print(f"  Network: {network.upper()} ({MANTLE_RPC_URL})")
    print(f"{'='*60}\n")

    if not MANTLE_PRIVATE_KEY:
        print(red("  ❌ MANTLE_PRIVATE_KEY is not set in .env!"))
        print("  Add your deployer wallet private key to .env:")
        print("  MANTLE_PRIVATE_KEY=0x...")
        sys.exit(1)

    # Connect
    w3 = Web3(Web3.HTTPProvider(MANTLE_RPC_URL, request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        print(red(f"  ❌ Cannot connect to {MANTLE_RPC_URL}"))
        sys.exit(1)

    account = Account.from_key(MANTLE_PRIVATE_KEY)
    balance = w3.eth.get_balance(account.address)
    print(f"  Deployer: {account.address}")
    print(f"  Balance : {w3.from_wei(balance, 'ether'):.4f} MNT\n")

    if balance == 0:
        print(red("  ❌ Deployer has 0 MNT! Get testnet MNT from Mantle faucet."))
        sys.exit(1)

    # Compile
    compiled = compile_contracts()

    # Extract AgentIdentity
    agent_id_path = str(CONTRACTS_DIR / "AgentIdentity.sol")
    sig_rec_path = str(CONTRACTS_DIR / "SignalRecorder.sol")

    agent_identity_data = compiled.get(agent_id_path + ":AgentIdentity")
    signal_recorder_data = compiled.get(sig_rec_path + ":SignalRecorder")

    if not agent_identity_data:
        # Try with different key format (solcx v3 uses different keys)
        for key, data in compiled.items():
            if "AgentIdentity" in key:
                agent_identity_data = data
            if "SignalRecorder" in key:
                signal_recorder_data = data

    if not agent_identity_data or not signal_recorder_data:
        print(red("  ❌ Could not find compiled contracts in output"))
        print("  Available keys:", list(compiled.keys()))
        sys.exit(1)

    # Deploy AgentIdentity
    print(yellow("\n📦 Step 1/4: Deploying AgentIdentity..."))
    agent_addr = deploy_contract(
        w3,
        agent_identity_data["abi"],
        agent_identity_data["bin"],
        label="AgentIdentity",
    )

    # Deploy SignalRecorder
    print(yellow("\n📦 Step 2/4: Deploying SignalRecorder..."))
    recorder_addr = deploy_contract(
        w3,
        signal_recorder_data["abi"],
        signal_recorder_data["bin"],
        args=[Web3.to_checksum_address(agent_addr)],
        label="SignalRecorder",
    )

    # Link SignalRecorder to AgentIdentity
    print(yellow("\n🔗 Step 3/4: Linking SignalRecorder → AgentIdentity..."))
    agent_contract = w3.eth.contract(
        address=Web3.to_checksum_address(agent_addr),
        abi=agent_identity_data["abi"],
    )
    nonce = _nonce_lock[0] if _nonce_lock[0] is not None else w3.eth.get_transaction_count(account.address)
    tx = agent_contract.functions.setSignalRecorder(
        Web3.to_checksum_address(recorder_addr)
    ).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 200_000,
        "gasPrice": w3.eth.gas_price,
        "chainId": MANTLE_CHAIN_ID,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.get("status") == 1:
        print(green("  ✅ SignalRecorder linked to AgentIdentity"))
        _nonce_lock[0] = nonce + 1
    else:
        print(red("  ❌ Failed to link SignalRecorder"))

    # Register Agent
    print(yellow("\n🤖 Step 4/4: Registering AI Agent..."))
    agent_uri = "https://mantle-vision.ai/agent.json"
    nonce = _nonce_lock[0] if _nonce_lock[0] is not None else w3.eth.get_transaction_count(account.address)
    tx = agent_contract.functions.register(agent_uri).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 300_000,
        "gasPrice": w3.eth.gas_price,
        "chainId": MANTLE_CHAIN_ID,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    if receipt.get("status") == 1:
        # Parse agent ID from Registered event
        logs = agent_contract.events.Registered().process_receipt(receipt)
        agent_id = logs[0]["args"]["agentId"] if logs else "?"
        print(green(f"  ✅ Agent registered — ID: {agent_id}"))
        _nonce_lock[0] = nonce + 1
    else:
        print(red("  ❌ Agent registration failed"))

    # Update .env
    print(yellow("\n📝 Updating .env..."))
    update_env("AGENT_CONTRACT_ADDRESS", agent_addr)

    print(green(f"\n{'='*60}"))
    print(green(f"  ✅ DEPLOYMENT COMPLETE!"))
    print(green(f"  AgentIdentity : {agent_addr}"))
    print(green(f"  SignalRecorder: {recorder_addr}"))
    print(green(f"  AGENT_CONTRACT_ADDRESS written to .env"))
    print(green(f"{'='*60}\n"))


if __name__ == "__main__":
    main()
