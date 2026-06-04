# Lazy imports to avoid slow startup (sklearn, networkx, aiogram, etc.)

def __getattr__(name):
    if name == "telegram_notifier":
        from app.services.telegram_bot import telegram
        return telegram
    if name == "mantle_scanner":
        from app.services.mantle_scanner import mantle_scanner
        return mantle_scanner
    if name == "dex_trader":
        from app.services.dex_trader import dex_trader
        return dex_trader
    if name == "get_price":
        from app.services.price_feed import get_price
        return get_price
    if name == "get_all_prices":
        from app.services.price_feed import get_all_prices
        return get_all_prices
    if name == "trading_agent":
        from app.services.trading_agent import trading_agent
        return trading_agent
    if name == "cluster_analyzer":
        from app.services.cluster_analyzer import cluster_analyzer
        return cluster_analyzer
    if name == "anomaly_detector":
        from app.services.anomaly_detector import anomaly_detector
        return anomaly_detector
    if name == "knowledge_base":
        from app.services.knowledge_base import knowledge_base
        return knowledge_base
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "telegram_notifier",
    "mantle_scanner",
    "dex_trader",
    "get_price",
    "get_all_prices",
    "trading_agent",
    "cluster_analyzer",
    "anomaly_detector",
    "knowledge_base",
]
