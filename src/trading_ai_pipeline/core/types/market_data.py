"""
Market data type definitions.

All raw data structures received from MetaTrader 5.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Timeframe(str, Enum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
    MN1 = "MN1"


class Candle(BaseModel):
    """Single OHLCV candle with timestamp."""

    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    spread: Optional[float] = None

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def is_doji(self) -> bool:
        return self.body_size <= (self.high - self.low) * 0.1


class OHLCV(BaseModel):
    """Collection of candles for a specific symbol and timeframe."""

    symbol: str
    timeframe: Timeframe
    candles: List[Candle] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def latest(self) -> Optional[Candle]:
        if not self.candles:
            return None
        return self.candles[-1]

    @property
    def count(self) -> int:
        return len(self.candles)

    def closes(self) -> List[float]:
        return [c.close for c in self.candles]

    def highs(self) -> List[float]:
        return [c.high for c in self.candles]

    def lows(self) -> List[float]:
        return [c.low for c in self.candles]

    def opens(self) -> List[float]:
        return [c.open for c in self.candles]

    def volumes(self) -> List[float]:
        return [c.volume for c in self.candles]


class SymbolInfo(BaseModel):
    """Trading symbol metadata from MT5."""

    name: str
    description: str = ""
    currency_base: str = ""
    currency_profit: str = ""
    digits: int = 5
    point: float = 0.00001
    spread: float = 0.0
    spread_float: bool = True
    trade_contract_size: float = 100000.0
    volume_min: float = 0.01
    volume_max: float = 100.0
    volume_step: float = 0.01
    trade_allowed: bool = True
    session_open: Optional[datetime] = None


class MarketSnapshot(BaseModel):
    """
    Complete market snapshot for one symbol across multiple timeframes.
    This is the primary input for the pipeline.
    """

    symbol: str
    primary_timeframe: Timeframe
    symbol_info: SymbolInfo
    ohlcv_primary: OHLCV
    ohlcv_higher: Optional[OHLCV] = None   # e.g. H4 when primary is H1
    ohlcv_lower: Optional[OHLCV] = None    # e.g. M15 when primary is H1
    current_bid: float = 0.0
    current_ask: float = 0.0
    collected_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def current_spread_points(self) -> float:
        if self.symbol_info.point > 0:
            return (self.current_ask - self.current_bid) / self.symbol_info.point
        return 0.0
