from __future__ import annotations

import logging
import statistics
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.price_feed import get_price

logger = logging.getLogger(__name__)


class RSIStrategy:
    """Relative Strength Index — detects overbought/oversold conditions from price history.

    RSI < 30 → oversold (buy signal)
    RSI > 70 → overbought (sell signal)
    """

    PERIODS = 14
    OVERBOUGHT = 70
    OVERSOLD = 30

    def __init__(self) -> None:
        self.price_history: dict[str, list[float]] = {}
        self.max_history = 100

    def record_price(self, symbol: str, price: float) -> None:
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        self.price_history[symbol].append(price)
        if len(self.price_history[symbol]) > self.max_history:
            self.price_history[symbol] = self.price_history[symbol][-self.max_history:]

    def compute(self, symbol: str, current_price: Optional[float] = None) -> dict[str, Any]:
        prices = self.price_history.get(symbol, [])
        if current_price is not None:
            self.record_price(symbol, current_price)
            prices = self.price_history.get(symbol, [])

        if len(prices) < self.PERIODS + 1:
            return {"score": 0.5, "rsi": 50.0, "signal": "neutral", "reason": "Not enough data"}

        gains = []
        losses = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))

        avg_gain = statistics.mean(gains[-self.PERIODS:]) if gains else 0
        avg_loss = statistics.mean(losses[-self.PERIODS:]) if losses else 0

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))

        if rsi <= self.OVERSOLD:
            score = max(0.6, 0.9 - (rsi / self.OVERSOLD) * 0.3)
            signal = "buy"
            reason = f"RSI {rsi:.1f} — oversold"
        elif rsi >= self.OVERBOUGHT:
            score = max(0.6, 0.9 - ((100 - rsi) / (100 - self.OVERBOUGHT)) * 0.3)
            signal = "sell"
            reason = f"RSI {rsi:.1f} — overbought"
        else:
            score = 0.5
            signal = "hold"
            reason = f"RSI {rsi:.1f} — neutral"

        return {"score": round(score, 4), "rsi": round(rsi, 2), "signal": signal, "reason": reason}


class VolumeStrategy:
    """Volume Anomaly Detection — measures abnormal volume spikes relative to baseline.

    Current volume vs rolling average. >2σ deviation = anomaly signal.
    """

    LOOKBACK = 20
    ANOMALY_THRESHOLD = 2.0

    def __init__(self) -> None:
        self.volume_history: dict[str, list[float]] = {}

    def record_volume(self, symbol: str, volume: float) -> None:
        if symbol not in self.volume_history:
            self.volume_history[symbol] = []
        self.volume_history[symbol].append(volume)
        if len(self.volume_history[symbol]) > self.LOOKBACK * 2:
            self.volume_history[symbol] = self.volume_history[symbol][-(self.LOOKBACK * 2):]

    def compute(self, symbol: str, current_volume: Optional[float] = None) -> dict[str, Any]:
        volumes = self.volume_history.get(symbol, [])

        if current_volume is not None:
            self.record_volume(symbol, current_volume)
            volumes = self.volume_history.get(symbol, [])

        if len(volumes) < self.LOOKBACK:
            return {"score": 0.5, "z_score": 0.0, "signal": "neutral", "reason": "Not enough volume data"}

        # Use only the last LOOKBACK volumes for baseline
        baseline = volumes[:self.LOOKBACK] if len(volumes) > self.LOOKBACK else volumes
        current = volumes[-1]

        mean = statistics.mean(baseline)
        stdev = statistics.stdev(baseline) if len(baseline) > 1 else 0.0

        if stdev == 0:
            return {"score": 0.5, "z_score": 0.0, "signal": "neutral", "reason": "Zero volume variance"}

        z_score = (current - mean) / stdev

        if z_score > self.ANOMALY_THRESHOLD:
            score = min(0.95, 0.6 + (z_score - self.ANOMALY_THRESHOLD) * 0.1)
            signal = "buy" if current > mean * 1.5 else "sell"
            reason = f"Volume spike: {current:.0f} vs baseline {mean:.0f} (z={z_score:.2f})"
        elif z_score < -self.ANOMALY_THRESHOLD:
            score = 0.5
            signal = "hold"
            reason = f"Volume drop: {current:.0f} vs baseline {mean:.0f} (z={z_score:.2f})"
        else:
            score = 0.5
            signal = "hold"
            reason = f"Volume normal (z={z_score:.2f})"

        return {"score": round(score, 4), "z_score": round(z_score, 2), "signal": signal, "reason": reason}


class NostalgiaStrategy:
    """Pattern-based strategy adapted from Gekko/Nostalgia.

    Detects MACD crossovers, support/resistance breaks, and trend strength using ADX-like logic.
    Uses only price history — no AI, purely mathematical.
    """

    SHORT_EMA = 12
    LONG_EMA = 26
    SIGNAL_EMA = 9

    def __init__(self) -> None:
        self.price_history: dict[str, list[float]] = {}

    def record_price(self, symbol: str, price: float) -> None:
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        self.price_history[symbol].append(price)
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]

    @staticmethod
    def _ema(data: list[float], period: int) -> list[float]:
        if len(data) < period:
            return []
        multiplier = 2.0 / (period + 1)
        result = [statistics.mean(data[:period])]
        for price in data[period:]:
            result.append((price - result[-1]) * multiplier + result[-1])
        return result

    def compute(self, symbol: str, current_price: Optional[float] = None) -> dict[str, Any]:
        prices = self.price_history.get(symbol, [])
        if current_price is not None:
            self.record_price(symbol, current_price)
            prices = self.price_history.get(symbol, [])

        if len(prices) < self.LONG_EMA + self.SIGNAL_EMA:
            return {"score": 0.5, "signal": "neutral", "reason": "Not enough price history for Nostalgia"}

        ema_short = self._ema(prices, self.SHORT_EMA)
        ema_long = self._ema(prices, self.LONG_EMA)

        if not ema_short or not ema_long:
            return {"score": 0.5, "signal": "neutral", "reason": "EMA computation failed"}

        # Align lengths
        min_len = min(len(ema_short), len(ema_long))
        macd_line = [ema_short[-min_len + i] - ema_long[-min_len + i] for i in range(min_len)]

        signal_line = self._ema(macd_line, self.SIGNAL_EMA)
        if not signal_line:
            return {"score": 0.5, "signal": "neutral", "reason": "Signal line computation failed"}

        # Align again
        macd_vals = macd_line[-len(signal_line):]
        histogram = [macd_vals[i] - signal_line[i] for i in range(len(signal_line))]

        if len(histogram) < 2:
            return {"score": 0.5, "signal": "neutral", "reason": "Not enough histogram data"}

        current_hist = histogram[-1]
        prev_hist = histogram[-2]

        # Detect crossover
        if prev_hist <= 0 and current_hist > 0:
            score = 0.75
            signal = "buy"
            reason = "Nostalgia: MACD bullish crossover"
        elif prev_hist >= 0 and current_hist < 0:
            score = 0.75
            signal = "sell"
            reason = "Nostalgia: MACD bearish crossover"
        else:
            strength = abs(current_hist) / (abs(statistics.mean(histogram[-5:])) + 0.0001)
            if current_hist > 0 and strength > 1.5:
                score = 0.65
                signal = "buy"
                reason = f"Nostalgia: bullish momentum (strength {strength:.2f})"
            elif current_hist < 0 and strength > 1.5:
                score = 0.65
                signal = "sell"
                reason = f"Nostalgia: bearish momentum (strength {strength:.2f})"
            else:
                score = 0.5
                signal = "hold"
                reason = f"Nostalgia: neutral (hist {current_hist:.4f})"

        return {"score": round(score, 4), "signal": signal, "reason": reason}


rsi_strategy = RSIStrategy()
volume_strategy = VolumeStrategy()
nostalgia_strategy = NostalgiaStrategy()
