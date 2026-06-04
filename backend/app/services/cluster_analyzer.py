from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from app.config import settings
from app.database import db
from app.services.mantle_scanner import mantle_scanner

logger = logging.getLogger(__name__)

MAX_HOPS = 2
CLUSTER_MIN_MEMBERS = 2


class ClusterAnalyzer:
    def __init__(self) -> None:
        self._funding_cache: dict[str, list[dict[str, Any]]] = {}

    async def analyze_wallet(self, address: str, depth: int = MAX_HOPS) -> Optional[dict[str, Any]]:
        existing = db.find_cluster_by_address(address)
        if existing:
            return existing

        funding_tree = await self._build_funding_tree(address, depth)
        if not funding_tree or len(funding_tree) < 2:
            return None

        root_funder = self._find_root_funder(funding_tree)
        cluster_id = db.save_cluster(root_funder, funding_tree)
        return db.get_cluster_by_id(cluster_id)

    async def _build_funding_tree(self, address: str, depth: int) -> list[dict[str, Any]]:
        visited = set()
        tree: dict[str, dict[str, Any]] = {}
        queue = [(address, 0)]

        while queue:
            addr, hop = queue.pop(0)
            addr_key = addr.lower()
            if addr_key in visited or hop > depth:
                continue
            visited.add(addr_key)

            if addr_key not in tree:
                tree[addr_key] = {
                    "address": addr_key,
                    "total_in": 0.0,
                    "total_out": 0.0,
                    "tx_count": 0,
                    "role": "member",
                    "hop": hop,
                }

            funders = await self._get_funding_sources(addr)
            for funder in funders:
                faddr = funder.get("from", "").lower()
                if faddr and faddr not in visited:
                    if faddr not in tree:
                        tree[faddr] = {
                            "address": faddr,
                            "total_in": 0.0,
                            "total_out": 0.0,
                            "tx_count": 0,
                            "role": "funder" if hop < depth else "member",
                            "hop": hop + 1,
                        }
                    tree[faddr]["total_out"] += funder.get("value_eth", 0)
                    tree[addr_key]["total_in"] += funder.get("value_eth", 0)

                    db.save_funding_link(
                        from_addr=funder.get("from", ""),
                        to_addr=addr,
                        value_eth=funder.get("value_eth", 0),
                        tx_hash=funder.get("hash", ""),
                        block_number=funder.get("block_number", 0),
                        timestamp=funder.get("timestamp", ""),
                    )
                    queue.append((faddr, hop + 1))

        return [v for v in tree.values()]

    async def _get_funding_sources(self, address: str) -> list[dict[str, Any]]:
        addr_key = address.lower()
        if addr_key in self._funding_cache:
            return self._funding_cache[addr_key]

        sources = []
        latest = mantle_scanner.get_latest_block()
        if not latest:
            return sources

        from_block = max(0, latest - 500)
        for block_num in range(from_block, latest + 1):
            try:
                block = mantle_scanner.w3.eth.get_block(block_num, full_transactions=True) if mantle_scanner.w3 else None
                if not block:
                    continue
                for tx in block.get("transactions", []):
                    to_addr = (tx.get("to") or "").lower()
                    if to_addr == addr_key:
                        value_eth = float(mantle_scanner.w3.from_wei(tx.get("value", 0) or 0, "ether"))
                        if value_eth > 0.1:
                            sources.append({
                                "from": tx["from"].lower(),
                                "to": to_addr,
                                "value_eth": value_eth,
                                "hash": tx["hash"].hex(),
                                "block_number": block_num,
                                "timestamp": str(block.get("timestamp", 0)),
                            })
            except Exception:
                continue

        self._funding_cache[addr_key] = sources
        return sources

    def _find_root_funder(self, members: list[dict[str, Any]]) -> str:
        out_volumes = {m["address"]: m.get("total_out", 0) for m in members}
        return max(out_volumes, key=out_volumes.get) if out_volumes else members[0]["address"]

    def detect_insider_cluster(self, transfers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        addr_tx_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for tx in transfers:
            addr = tx.get("from", "").lower()
            if addr:
                addr_tx_map[addr].append(tx)

        clusters: list[dict[str, Any]] = []
        processed = set()

        for addr, txs in addr_tx_map.items():
            if addr in processed:
                continue

            cluster = db.find_cluster_by_address(addr)
            if cluster and cluster["total_members"] >= CLUSTER_MIN_MEMBERS:
                success = all(
                    t.get("status", False) for t in txs
                )
                clusters.append({
                    "root_funder": cluster["root_funder"],
                    "members": cluster["members"],
                    "size": cluster["total_members"],
                    "total_volume": cluster["total_volume"],
                    "recent_success": success,
                    "confidence": min(0.5 + cluster["total_members"] * 0.05, 0.95),
                })
                for m in cluster["members"]:
                    processed.add(m["address"])

        return clusters

    def compute_cluster_score(self, members: list[dict[str, Any]]) -> float:
        if not members:
            return 0.0
        size_factor = min(1.0, len(members) / 20.0)
        volume = sum(m.get("total_in", 0) + m.get("total_out", 0) for m in members)
        volume_factor = min(1.0, volume / 5000.0)
        diversity = len(set(m.get("role", "") for m in members)) / 3.0
        score = size_factor * 0.4 + volume_factor * 0.4 + diversity * 0.2
        return round(min(1.0, score), 4)


cluster_analyzer = ClusterAnalyzer()
