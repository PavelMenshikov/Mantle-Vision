from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.database import db
from app.models.schemas import WhaleProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("/{address}/analysis")
async def analyze_wallet(address: str):
    from app.services.whale_score import whale_scorer
    from app.services.cluster_analyzer import cluster_analyzer

    addr = address.lower()

    score = whale_scorer.score_single_wallet(addr)
    cluster = db.find_cluster_by_address(addr)
    profile = db.get_whale_by_address(addr)

    tags = score.get("tags", [])
    if profile:
        try:
            profile_tags = json.loads(profile["tags"]) if isinstance(profile["tags"], str) else profile["tags"]
            tags = list(set(tags + profile_tags))
        except Exception:
            pass

    cluster_info = None
    if cluster:
        members = cluster.get("members", [])
        cluster_info = {
            "id": cluster["id"],
            "total_members": cluster["total_members"],
            "total_volume": cluster["total_volume"],
            "members": [
                {"address": m["address"], "role": m["role"], "tx_count": m["tx_count"]}
                for m in members[:20]
            ],
        }

    wallet_type = score.get("wallet_type", "unknown")
    risk = score.get("whale_score", 0.5)

    is_cex = any(t in tags for t in ["cex", "exchange", "binance", "bybit"])
    is_fresh = wallet_type == "fresh" or not profile
    is_insider = wallet_type == "insider" or "insider" in tags
    is_smart = wallet_type == "smart_money"
    is_anomaly = wallet_type == "anomaly"

    signals = []
    if is_cex:
        signals.append({"text": "CEX-related wallet — frequent exchange interactions", "severity": "info", "icon": "dollar"})
    if is_fresh:
        signals.append({"text": "Fresh wallet with no history — may be a setup for reconnaissance", "severity": "warning", "icon": "alert"})
    if is_insider:
        signals.append({"text": "Insider connections: cluster found with suspicious activity patterns", "severity": "danger", "icon": "users"})
    if is_smart:
        signals.append({"text": "Smart Money: transaction patterns match experienced traders", "severity": "info", "icon": "brain"})
    if is_anomaly:
        signals.append({"text": "Anomalous behavior: deviation from normal transaction patterns", "severity": "danger", "icon": "alert"})
    if risk > 0.7:
        signals.append({"text": "High risk: scoring indicates elevated danger for interaction", "severity": "danger", "icon": "shield"})
    if not signals:
        signals.append({"text": "No suspicious patterns detected. Wallet appears clean.", "severity": "clean", "icon": "check"})

    return {
        "address": addr,
        "wallet_type": wallet_type,
        "risk_score": round(risk, 2),
        "tags": tags,
        "total_value": score.get("total_volume", 0),
        "tx_count": score.get("tx_count", 0),
        "cluster": cluster_info,
        "signals": signals,
        "profile": {
            "label": profile["label"] if profile else "",
            "last_active": profile["last_active"] if profile else None,
        } if profile else None,
    }


@router.get("/{address}/funding-tree")
async def funding_tree(address: str, depth: int = Query(2, ge=1, le=4)):
    addr = address.lower()
    seen = set()
    nodes = []
    edges = []
    queue = [(addr, 0)]

    while queue:
        current, level = queue.pop(0)
        if current in seen or level > depth:
            continue
        seen.add(current)

        conn = db._get_conn()
        incoming = conn.execute(
            "SELECT from_address, value_eth, tx_hash, timestamp FROM funding_links WHERE to_address = ? ORDER BY value_eth DESC LIMIT 15",
            (current,),
        ).fetchall()
        outgoing = conn.execute(
            "SELECT to_address, value_eth, tx_hash, timestamp FROM funding_links WHERE from_address = ? ORDER BY value_eth DESC LIMIT 15",
            (current,),
        ).fetchall()

        nodes.append({"address": current, "level": level, "is_target": current == addr})

        for row in incoming:
            edge_id = f"{row['from_address']}→{row['to_address'] if 'to_address' in row.keys() else current}"
            if row["from_address"] not in seen:
                queue.append((row["from_address"], level + 1))
            edges.append({
                "from": row["from_address"],
                "to": current,
                "value": row["value_eth"],
                "direction": "in",
            })

        for row in outgoing:
            to_addr = row["to_address"]
            if to_addr not in seen:
                queue.append((to_addr, level + 1))
            edges.append({
                "from": current,
                "to": to_addr,
                "value": row["value_eth"],
                "direction": "out",
            })

    unique_nodes = {n["address"]: n for n in nodes}.values()
    return {
        "target": addr,
        "nodes": list(unique_nodes),
        "edges": edges,
        "total_nodes": len(unique_nodes),
        "total_edges": len(edges),
    }


@router.get("/{address}/summary")
async def wallet_summary(address: str):
    from app.services.analyzer import analyzer
    from app.services.whale_score import whale_scorer

    addr = address.lower()
    score = whale_scorer.score_single_wallet(addr)
    cluster = db.find_cluster_by_address(addr)
    profile = db.get_whale_by_address(addr)

    wallet_type = score.get("wallet_type", "unknown")
    risk = score.get("whale_score", 0.5)
    tags = score.get("tags", [])
    tx_count = score.get("tx_count", 0)

    if profile:
        try:
            profile_tags = json.loads(profile["tags"]) if isinstance(profile["tags"], str) else profile["tags"]
            tags = list(set(tags + profile_tags))
        except Exception:
            pass

    cluster_info = None
    if cluster:
        cluster_info = {
            "id": cluster["id"],
            "total_members": cluster["total_members"],
            "total_volume": cluster["total_volume"],
        }

    prompt = (
        f"Analyze wallet {addr} on Mantle Network.\n"
        f"Context: type={wallet_type}, risk={risk:.2f}, tags={tags}, "
        f"tx_count={tx_count}, cluster={cluster_info}.\n"
        f"Return a JSON object with a 'summary' field containing ONE concise sentence "
        f"(under 25 words) describing what this wallet appears to be doing on Mantle."
    )

    ai_result = await analyzer._call_ai(prompt)

    if ai_result:
        try:
            data = json.loads(ai_result)
            if isinstance(data, dict) and "summary" in data:
                return {"summary": data["summary"], "provider": "altllm"}
        except Exception:
            pass

    fallbacks = {
        "cex": "Exchange wallet handling deposits and withdrawals on Mantle.",
        "exchange": "Exchange wallet handling deposits and withdrawals on Mantle.",
        "fresh": "Newly created wallet with little on-chain history on Mantle.",
        "insider": "Suspicious wallet linked to coordinated cluster activity on Mantle.",
        "smart_money": "Sophisticated trader executing profitable strategies on Mantle.",
        "anomaly": "Wallet exhibiting unusual or anomalous transaction patterns on Mantle.",
        "whale": "High-net-worth wallet moving significant capital on Mantle.",
    }
    summary = fallbacks.get(wallet_type)
    if not summary:
        for t in tags:
            if t.lower() in fallbacks:
                summary = fallbacks[t.lower()]
                break
    if not summary:
        summary = f"Mantle wallet with {tx_count} transactions and {risk:.0%} risk score."

    return {"summary": summary, "provider": "deterministic"}


@router.get("/{address}/transactions")
async def wallet_transactions(address: str, limit: int = Query(20, ge=1, le=100)):
    from app.services.mantle_scanner import mantle_scanner

    addr = address.lower()
    latest = mantle_scanner.get_latest_block()
    if not latest or not mantle_scanner.w3:
        return []

    from web3 import Web3
    from_block = max(0, latest - 50)
    txs = []

    for block_num in range(from_block, latest + 1):
        try:
            raw = mantle_scanner.w3.eth.get_block(block_num, full_transactions=True)
            for tx in raw.get("transactions", []):
                tx_from = tx["from"].lower()
                tx_to = (tx.get("to") or "").lower()
                if tx_from == addr or tx_to == addr:
                    value_eth = float(Web3.from_wei(tx.get("value", 0) or 0, "ether"))
                    txs.append({
                        "from": tx_from,
                        "to": tx_to,
                        "value_eth": round(value_eth, 6),
                        "hash": tx["hash"].hex(),
                        "block": block_num,
                        "timestamp": raw.get("timestamp", 0),
                    })
        except Exception:
            continue

    txs.sort(key=lambda t: t["block"], reverse=True)
    return txs[:limit]
