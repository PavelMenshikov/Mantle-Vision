from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SignalDirection(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class SignalSource(str, Enum):
    NANSEN = "nansen"
    ELFA = "elfa_ai"
    ANALYZER = "ai_analyzer"
    MANUAL = "manual"
    SURF = "surf_ai"
    ALTLLM = "altllm"


class TradeType(str, Enum):
    BUY = "buy"
    SELL = "sell"


class TradeStatus(str, Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssetType(str, Enum):
    MNT = "MNT"
    USDC = "USDC"
    METH = "mETH"
    USDY = "USDY"
    FBTC = "fBTC"


class Signal(BaseModel):
    id: str
    type: str
    asset: str
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    txHash: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: SignalSource


class WhaleProfile(BaseModel):
    address: str
    label: str = ""
    totalValue: float = 0.0
    lastActivity: Optional[datetime] = None
    riskScore: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = []


class PortfolioPosition(BaseModel):
    asset: AssetType
    amount: Decimal = Decimal("0")
    value: float = 0.0
    pnl: float = 0.0
    pnlPercent: float = 0.0


class PaperTrade(BaseModel):
    id: str
    type: TradeType
    asset: AssetType
    amount: Decimal
    price: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: TradeStatus = TradeStatus.EXECUTED
    txHash: Optional[str] = None


class AgentIdentity(BaseModel):
    name: str
    description: str = ""
    totalSignals: int = 0
    accuracy: float = 0.0
    owner: str = ""


class WhaleActivity(BaseModel):
    txHash: str
    method: str = ""
    value: float = 0.0
    timestamp: datetime
    token: str = ""
    to: str = ""
    from_: str = Field(alias="from")


class PnLDataPoint(BaseModel):
    timestamp: datetime
    pnl: float
    portfolioValue: float
