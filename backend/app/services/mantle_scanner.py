"""Real Mantle blockchain scanner — reads actual on-chain data."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from web3 import Web3

from app.config import settings

logger = logging.getLogger(__name__)

# Known Mantle DEX & Protocol contracts — верифицированные адреса
# Источники: официальная документация каждого протокола
# Если адрес не найден — протокол закомментирован, плейсхолдеры недопустимы
KNOWN_PROTOCOLS: dict[str, str] = {
    # Merchant Moe: LBRouter на Mantle mainnet
    # https://github.com/merchant-moe/moe-core
    "merchant_moe_router": "0x9B33361871Da2aE2053aB3672442Ce3BCEA5b5a0",
    # Agni Finance: SwapRouter на Mantle mainnet
    # https://docs.agni.finance/resources/smart-contract-addresses
    "agni_swap_router": "0x319B69888b0d11cEC22caA5034e25FfFBDc88421",
    # Mantle Network: WMNT token contract
    # https://docs.mantle.xyz/network/system-information/deployed-contracts
    "wmnt": "0x78c1b0C915c4FAA5FffA6CAbf0219DA63d7f4cb8",
    # mETH Protocol: mETH staking contract
    # https://docs.methprotocol.xyz/contracts
    "meth_staking": "0xe3cBd06D7dadB3F4e6557bAb7EdD924CD1489E8f",
}
# Протоколы с неподтверждёнными адресами — удалены.
# Раскомментируй только после проверки в официальной документации:
# "cleopatra_pool_factory": "не найден — проверь cleopatra.exchange",
# "lendle_pool": "не найден — проверь lendle.xyz",

WHALE_MIN_VALUE_ETH = 50.0

SEPOLIA_CHAIN_ID = 5003


class MantleScanner:
    """Scans Mantle blockchain for real on-chain activity."""

    def __init__(self, w3: Optional[Web3] = None) -> None:
        self.w3 = w3
        self._connected = False
        self._chain_id = 0
        if self.w3 is None:
            self._connect()

    def _connect(self) -> bool:
        try:
            self.w3 = Web3(Web3.HTTPProvider(
                settings.MANTLE_RPC_URL,
                request_kwargs={"timeout": 30},
            ))
            self._connected = self.w3.is_connected()
            if self._connected:
                self._chain_id = self.w3.eth.chain_id
                logger.info(f"MantleScanner: connected (chain: {self._chain_id})")
            else:
                logger.warning("MantleScanner: could not connect to RPC")
            return self._connected
        except Exception as e:
            logger.warning(f"MantleScanner: connection failed: {e}")
            self._connected = False
            return False

    @property
    def chain_id(self) -> int:
        return self._chain_id

    @property
    def is_sepolia(self) -> bool:
        return self._chain_id == SEPOLIA_CHAIN_ID

    @property
    def whale_min_value(self) -> float:
        return 0.01 if self.is_sepolia else WHALE_MIN_VALUE_ETH

    def get_latest_block(self) -> int:
        if not self.w3 or not self._connected:
            if not self._connect():
                return 0
        try:
            return self.w3.eth.block_number
        except Exception as e:
            logger.error(f"get_latest_block: {e}")
            return 0

    def get_block(self, block_num: int) -> dict[str, Any]:
        if not self.w3 or not self._connected:
            self._connect()
        if not self.w3:
            return {}
        try:
            block = self.w3.eth.get_block(block_num, full_transactions=True)
            return {
                "number": block.get("number", block_num),
                "hash": block.get("hash", b"").hex() if block.get("hash") else "",
                "timestamp": block.get("timestamp", 0),
                "tx_count": len(block.get("transactions", [])),
                "gas_used": block.get("gasUsed", 0),
                "gas_limit": block.get("gasLimit", 0),
            }
        except Exception as e:
            logger.error(f"get_block({block_num}): {e}")
            return {}

    def scan_large_transfers(
        self,
        from_block: int,
        to_block: int,
        min_value_eth: float = WHALE_MIN_VALUE_ETH,
    ) -> list[dict[str, Any]]:
        """Scan blocks for large ETH/MNT transfers (real whale movements)."""
        if not self.w3 or not self._connected:
            if not self._connect():
                return []

        transfers = []
        limit = 500
        for block_num in range(from_block, min(to_block, from_block + limit) + 1):
            try:
                block = self.w3.eth.get_block(block_num, full_transactions=True)
                for tx in block.get("transactions", []):
                    value_eth = float(Web3.from_wei(tx.get("value", 0) or 0, "ether"))
                    if value_eth >= min_value_eth:
                        transfers.append({
                            "type": "whale_transfer",
                            "hash": tx["hash"].hex(),
                            "from": tx["from"],
                            "to": tx.get("to", ""),
                            "value_eth": value_eth,
                            "block": block_num,
                            "timestamp": block.get("timestamp", 0),
                            # receipt не запрашиваем — экономит ~50x RPC вызовов за цикл
                            "status": True,
                            "gas_used": tx.get("gas", 21000),
                        })
            except Exception as e:
                logger.debug(f"scan_large_transfers block {block_num}: {e}")
                continue

        return transfers

    def scan_protocol_interactions(
        self,
        from_block: int,
        to_block: int,
    ) -> list[dict[str, Any]]:
        """Scan for interactions with known Mantle DeFi protocols."""
        if not self.w3 or not self._connected:
            if not self._connect():
                return []

        events = []
        protocol_addresses = {v.lower(): k for k, v in KNOWN_PROTOCOLS.items()}

        for block_num in range(from_block, min(to_block, from_block + 500) + 1):
            try:
                block = self.w3.eth.get_block(block_num, full_transactions=True)
                for tx in block.get("transactions", []):
                    to_addr = (tx.get("to") or "").lower()
                    if to_addr in protocol_addresses:
                        protocol = protocol_addresses[to_addr]
                        value_eth = float(Web3.from_wei(tx.get("value", 0) or 0, "ether"))
                        events.append({
                            "type": "protocol_interaction",
                            "protocol": protocol,
                            "hash": tx["hash"].hex(),
                            "from": tx["from"],
                            "value_eth": value_eth,
                            "block": block_num,
                            "timestamp": block.get("timestamp", 0),
                        })
            except Exception as e:
                logger.debug(f"scan_protocol block {block_num}: {e}")
                continue

        return events

    def get_balance(self, address: str) -> float:
        """Get real MNT balance for any address."""
        if not self.w3 or not self._connected:
            if not self._connect():
                return 0
        try:
            checksum = Web3.to_checksum_address(address)
            balance_wei = self.w3.eth.get_balance(checksum)
            return float(Web3.from_wei(balance_wei, "ether"))
        except Exception as e:
            logger.error(f"get_balance({address}): {e}")
            return 0

    def get_top_wallets(self, count: int = 10) -> list[dict[str, Any]]:
        """Get top MNT holders by scanning recent blocks for active wallets."""
        if not self.w3 or not self._connected:
            if not self._connect():
                return []

        wallets: dict[str, dict[str, Any]] = {}
        latest = self.get_latest_block()
        if not latest:
            return []

        from_block = max(0, latest - 100)
        for block_num in range(from_block, latest + 1):
            try:
                block = self.w3.eth.get_block(block_num, full_transactions=True)
                for tx in block.get("transactions", []):
                    sender = tx["from"].lower()
                    receiver = (tx.get("to") or "").lower()
                    value = float(Web3.from_wei(tx.get("value", 0) or 0, "ether"))

                    for addr in [sender, receiver]:
                        if addr and len(addr) == 42:
                            if addr not in wallets:
                                wallets[addr] = {"address": addr, "total_in": 0, "total_out": 0, "tx_count": 0}
                            wallets[addr]["tx_count"] += 1
                            if addr == receiver:
                                wallets[addr]["total_in"] += value
                            elif addr == sender:
                                wallets[addr]["total_out"] += value
            except Exception:
                continue

        sorted_wallets = sorted(
            wallets.values(),
            key=lambda w: w["total_in"] + w["total_out"],
            reverse=True,
        )[:count]

        return [
            {
                "address": w["address"],
                "label": f"Active Wallet #{i + 1}",
                "total_value": round(w["total_in"] + w["total_out"], 2),
                "tx_count": w["tx_count"],
                "risk_score": round(min(w["total_in"] / (w["total_in"] + w["total_out"] + 1), 0.9), 2),
                "tags": ["active", "on_chain"],
            }
            for i, w in enumerate(sorted_wallets)
        ]


mantle_scanner = MantleScanner()
