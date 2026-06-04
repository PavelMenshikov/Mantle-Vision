from __future__ import annotations

import logging
from typing import Any, Optional
from web3 import Web3
from web3.types import BlockNumber, Wei
from eth_account import Account

from app.config import settings

logger = logging.getLogger(__name__)

AGENT_CONTRACT_ABI = [
    {
        "inputs": [{"name": "agentURI", "type": "string"}],
        "name": "register",
        "outputs": [{"name": "agentId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "name": "getSignalCount",
        "outputs": [{"name": "totalSignals", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "name": "getAccuracy",
        "outputs": [
            {"name": "totalSignals", "type": "uint256"},
            {"name": "accurateSignals", "type": "uint256"},
            {"name": "accuracyBasisPoints", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getSignalRecorder",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
]


class MantleClient:
    def __init__(self) -> None:
        self.rpc_url = settings.MANTLE_RPC_URL
        self.chain_id = settings.MANTLE_CHAIN_ID
        self.private_key = settings.MANTLE_PRIVATE_KEY
        self.agent_contract_addr = settings.AGENT_CONTRACT_ADDRESS

        self.w3: Optional[Web3] = None
        self._connected = False

        self._connect()

    def _connect(self) -> None:
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 30}))
            self._connected = self.w3.is_connected()
            if self._connected:
                logger.info(f"Connected to Mantle RPC (chain: {self.w3.eth.chain_id})")
            else:
                logger.warning("Failed to connect to Mantle RPC")
        except Exception as e:
            logger.warning(f"Mantle RPC connection failed: {e}")
            self._connected = False

    @property
    def is_connected(self) -> bool:
        if self.w3:
            self._connected = self.w3.is_connected()
        return self._connected

    async def get_block_number(self) -> int:
        if not self.is_connected:
            self._connect()
        if not self.w3:
            return 0
        try:
            return self.w3.eth.block_number
        except Exception as e:
            logger.error(f"Failed to get block number: {e}")
            return 0

    async def get_balance(self, address: str) -> float:
        if not self.is_connected:
            self._connect()
        if not self.w3:
            return 0.0
        try:
            checksum = self.w3.to_checksum_address(address)
            balance_wei = self.w3.eth.get_balance(checksum)
            return float(self.w3.from_wei(balance_wei, "ether"))
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {e}")
            return 0.0

    async def get_transaction(self, tx_hash: str) -> Optional[dict[str, Any]]:
        if not self.is_connected:
            self._connect()
        if not self.w3:
            return None
        try:
            tx = self.w3.eth.get_transaction(tx_hash)
            if tx:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                return {
                    "hash": tx["hash"].hex(),
                    "from": tx["from"],
                    "to": tx.get("to", ""),
                    "value": float(self.w3.from_wei(tx["value"], "ether")),
                    "gasPrice": float(self.w3.from_wei(tx.get("gasPrice", 0), "gwei")),
                    "blockNumber": tx.get("blockNumber", 0),
                    "status": bool(receipt.get("status", 0)) if receipt else False,
                }
        except Exception as e:
            logger.error(f"Failed to get tx {tx_hash}: {e}")
        return None

    async def create_agent_identity(self, agent_uri: str = "https://mantle-vision.ai/agent.json") -> Optional[int]:
        if not self.private_key or not self.agent_contract_addr:
            logger.warning("Agent contract address or private key not configured")
            return None

        if not self.is_connected or not self.w3:
            self._connect()
            if not self.w3:
                return None

        try:
            account = Account.from_key(self.private_key)
            contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(self.agent_contract_addr),
                abi=AGENT_CONTRACT_ABI,
            )

            tx = contract.functions.register(agent_uri).build_transaction({
                "from": account.address,
                "nonce": self.w3.eth.get_transaction_count(account.address),
                "gas": 300_000,
                "gasPrice": self.w3.eth.gas_price,
                "chainId": self.chain_id,
            })

            signed = account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt.get("status") == 1:
                logs = contract.events.Registered().process_receipt(receipt)
                agent_id = logs[0]["args"]["agentId"] if logs else None
                logger.info(f"Agent identity created: id={agent_id}, tx={tx_hash.hex()}")
                return agent_id

            logger.error(f"Agent creation failed: {receipt}")
            return None

        except Exception as e:
            logger.error(f"Failed to create agent identity: {e}")
            return None

    async def get_agent_identity(self, agent_id: int) -> Optional[dict[str, Any]]:
        if not self.agent_contract_addr:
            return None
        if not self.is_connected or not self.w3:
            self._connect()
            if not self.w3:
                return None

        try:
            contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(self.agent_contract_addr),
                abi=AGENT_CONTRACT_ABI,
            )
            signal_count = contract.functions.getSignalCount(agent_id).call()
            accuracy_result = contract.functions.getAccuracy(agent_id).call()
            return {
                "agentId": agent_id,
                "totalSignals": signal_count,
                "accurateSignals": accuracy_result[1],
                "accuracyBasisPoints": accuracy_result[2],
                "accuracyPercent": accuracy_result[2] / 100.0 if accuracy_result[2] else 0.0,
            }
        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            return None


mantle_client = MantleClient()
