"""Mantle DEX Trader — executes swaps on Mantle DeFi protocols via user wallet."""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import uuid4

from eth_account import Account
from web3 import Web3

from app.config import settings
from app.models.schemas import AssetType, TradeStatus, TradeType
from app.services.price_feed import get_price

logger = logging.getLogger(__name__)

# Known Mantle DEX router addresses
DEX_ROUTERS = {
    "cleopatra": "0xC3AE5f9a4FFe478D1B4C4a5D6f3C3b8C0D4F1E2A",
    "merchant_moe": "0x9B33361871Da2aE2053aB3672442Ce3BCEA5b5a0",
}

# Minimal router ABI for swap
SWAP_ABI = [
    {
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactETHForTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "payable",
        "type": "function",
    },
]

TOKEN_ADDRESSES = {
    "MNT": "0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000",
    "USDC": "0x09Bc4E0D864854c6aFB6eB9A9cdF58aC190D0dF9",
    "mETH": "0xE3Cb4B0b3B6C7C0aE5C5C5C5C5C5C5C5C5C5C5C5",
    "WETH": "0xE3Cb4B0b3B6C7C0aE5C5C5C5C5C5C5C5C5C5C5C5",
    "USDY": "0x5bE8F8B8B8B8B8B8B8B8B8B8B8B8B8B8B8B8B8b",
}

DEFAULT_SLIPPAGE = 0.005  # 0.5%


class DexTrader:
    """Executes real trades on Mantle DEX via the agent's wallet."""

    def __init__(self) -> None:
        self.w3: Optional[Web3] = None
        self.account: Optional[Account] = None
        self._init_wallet()

    def _init_wallet(self) -> None:
        if not settings.MANTLE_PRIVATE_KEY:
            logger.warning("DexTrader: no private key — paper trading only")
            return
        try:
            self.w3 = Web3(Web3.HTTPProvider(
                settings.MANTLE_RPC_URL,
                request_kwargs={"timeout": 30},
            ))
            if not self.w3.is_connected():
                logger.warning("DexTrader: cannot connect to Mantle RPC")
                return
            self.account = Account.from_key(settings.MANTLE_PRIVATE_KEY)
            balance = self.w3.eth.get_balance(self.account.address)
            logger.info(
                f"DexTrader: wallet {self.account.address[:10]}... "
                f"balance: {self.w3.from_wei(balance, 'ether')} MNT"
            )
        except Exception as e:
            logger.warning(f"DexTrader: init failed: {e}")

    @property
    def is_ready(self) -> bool:
        return bool(self.w3 and self.account and self.w3.is_connected())

    async def get_mnt_balance(self) -> float:
        if not self.is_ready:
            return 0.0
        try:
            bal = self.w3.eth.get_balance(self.account.address)
            return float(self.w3.from_wei(bal, "ether"))
        except Exception:
            return 0.0

    async def swap_mnt_for_tokens(
        self,
        token_out: str,
        amount_mnt: float,
        slippage: float = DEFAULT_SLIPPAGE,
    ) -> dict[str, Any]:
        """Swap MNT for tokens on Cleopatra DEX."""
        if not self.is_ready:
            return {"status": "paper", "message": "Wallet not configured — use paper trading"}

        mnt_balance = await self.get_mnt_balance()
        if mnt_balance < amount_mnt:
            return {"status": "failed", "reason": f"Insufficient MNT balance ({mnt_balance:.4f} < {amount_mnt})"}

        price = await get_price(token_out.upper())
        if not price:
            return {"status": "failed", "reason": "Cannot get token price"}

        amount_wei = self.w3.to_wei(amount_mnt, "ether")
        min_out = int(amount_mnt / price * (1 - slippage) * 10 ** 18) if token_out != "MNT" else 0

        router_addr = Web3.to_checksum_address(DEX_ROUTERS["cleopatra"])
        contract = self.w3.eth.contract(address=router_addr, abi=SWAP_ABI)
        to_addr = self.account.address
        deadline = self.w3.eth.get_block("latest")["timestamp"] + 300

        try:
            tx = contract.functions.swapExactETHForTokens(
                min_out,
                [Web3.to_checksum_address(TOKEN_ADDRESSES["WETH"]),
                 Web3.to_checksum_address(TOKEN_ADDRESSES.get(token_out.upper(), token_out))],
                to_addr,
                deadline,
            ).build_transaction({
                "from": to_addr,
                "value": amount_wei,
                "nonce": self.w3.eth.get_transaction_count(to_addr),
                "gas": 300_000,
                "gasPrice": self.w3.eth.gas_price,
                "chainId": settings.MANTLE_CHAIN_ID,
            })

            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt.get("status") == 1:
                logger.info(f"Swap executed: {amount_mnt} MNT → {token_out} | tx: {tx_hash.hex()}")
                return {
                    "status": "executed",
                    "tx_hash": tx_hash.hex(),
                    "amount_in": amount_mnt,
                    "asset_out": token_out,
                    "block": receipt["blockNumber"],
                }
            else:
                return {"status": "failed", "reason": f"Transaction reverted: {tx_hash.hex()}"}

        except Exception as e:
            logger.error(f"Swap failed: {e}")
            return {"status": "failed", "reason": str(e)}

    def get_wallet_address(self) -> str:
        if self.account:
            return self.account.address
        return ""


dex_trader = DexTrader()
