import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["DEMO_MODE"] = "true"
os.environ["MANTLE_RPC_URL"] = "https://rpc.sepolia.mantle.xyz"
os.environ["MANTLE_CHAIN_ID"] = "5001"
os.environ["MANTLE_PRIVATE_KEY"] = ""


@pytest.fixture
def sample_transfers():
    return [
        {
            "hash": "0xtx1",
            "from": "0xaaa1111111111111111111111111111111111111",
            "to": "0xbbb2222222222222222222222222222222222222",
            "value_eth": 100.0,
            "block": 100,
            "timestamp": 1000000,
            "status": True,
            "gas_used": 21000,
        },
        {
            "hash": "0xtx2",
            "from": "0xaaa1111111111111111111111111111111111111",
            "to": "0xccc3333333333333333333333333333333333333",
            "value_eth": 200.0,
            "block": 101,
            "timestamp": 1000100,
            "status": True,
            "gas_used": 21000,
        },
        {
            "hash": "0xtx3",
            "from": "0xddd4444444444444444444444444444444444444",
            "to": "0xeee5555555555555555555555555555555555555",
            "value_eth": 500.0,
            "block": 102,
            "timestamp": 1000200,
            "status": False,
            "gas_used": 30000,
        },
    ]


@pytest.fixture
def sample_txs_for_anomaly():
    return [
        {"value_eth": 100, "timestamp": 1000000, "to": "0xabc", "gas_used": 21000},
        {"value_eth": 102, "timestamp": 1000060, "to": "0xabc", "gas_used": 21000},
        {"value_eth": 98, "timestamp": 1000120, "to": "0xdef", "gas_used": 22000},
        {"value_eth": 105, "timestamp": 1000180, "to": "0xabc", "gas_used": 21000},
        {"value_eth": 99, "timestamp": 1000240, "to": "0xdef", "gas_used": 21500},
    ]


@pytest.fixture
def sample_anomaly_txs():
    return [
        {"value_eth": 100, "timestamp": 1000000, "to": "0xabc", "gas_used": 21000},
        {"value_eth": 100, "timestamp": 1000000, "to": "0xabc", "gas_used": 21000},
        {"value_eth": 100, "timestamp": 1000000, "to": "0xabc", "gas_used": 21000},
        {"value_eth": 10000, "timestamp": 1000000, "to": "0xabc", "gas_used": 21000},
        {"value_eth": 100, "timestamp": 1000000, "to": "0xabc", "gas_used": 21000},
    ]
