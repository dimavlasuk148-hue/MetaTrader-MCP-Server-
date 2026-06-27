"""
Indicator type definitions.

All Python-calculated indicator results. AI reads these — never calculates them.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class TrendDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"
    UNDEFINED = "undefined"


class SignalStrength(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NEUTRAL = "neutral"


class EMACrossSignal(BaseModel):
    """EMA crossover state."""

    ema_fast_period: int
    ema_slow_period: int
    ema_fast_value: float
    ema_slow_value: float
    ema_200_value: Optional[float] = None
    price_above_ema200: Optional[bool] = None
    crossover_bullish: bool = False   # fast crossed above slow recently
    crossover_bearish: bool = False   # fast crossed below slow recently
    trend: TrendDirection = TrendDirection.UNDEFINED
    bars_since_cross: Optional[int] = None


class MACDSignal(BaseModel):
    """MACD state."""

    macd_line: float
    signal_line: float
    histogram: float
    histogram_prev: Optional[float] = None
    above_zero: bool = False
    bullish_divergence: bool = False
    bearish_divergence: bool = False
    histogram_expanding: bool = False   # momentum increasing
    histogram_shrinking: bool = False   # momentum fading


class RSISignal(BaseModel):
    """RSI state."""

    period: int = 14
    value: float
    is_overbought: bool = False    # > 70
    is_oversold: bool = False      # < 30
    is_neutral: bool = True        # 30-70
    bullish_divergence: bool = False
    bearish_divergence: bool = False


class ATRData(BaseModel):
    """Average True Range — used for dynamic SL/TP."""

    period: int = 14
    value: float
    value_in_pips: float = 0.0
    volatility_label: str = "normal"   # low / normal / high / extreme


class ADXData(BaseModel):
    """Average Directional Index — trend strength."""

    period: int = 14
    adx_value: float
    plus_di: float
    minus_di: float
    trend_strength: SignalStrength = SignalStrength.NEUTRAL
    is_trending: bool = False    # ADX > 25
    is_ranging: bool = True


class BollingerBands(BaseModel):
    """Bollinger Bands state."""

    period: int = 20
    std_dev: float = 2.0
    upper: float
    middle: float   # SMA
    lower: float
    bandwidth: float = 0.0   # (upper - lower) / middle
    price_position: float = 0.0  # 0.0 = at lower, 1.0 = at upper
    squeeze: bool = False   # bandwidth < historical average
    breakout_up: bool = False
    breakout_down: bool = False


class VWAPData(BaseModel):
    """VWAP with deviations."""

    vwap: float
    dev_1_upper: Optional[float] = None
    dev_1_lower: Optional[float] = None
    dev_2_upper: Optional[float] = None
    dev_2_lower: Optional[float] = None
    price_above_vwap: bool = False
    distance_pips: float = 0.0


class IndicatorBundle(BaseModel):
    """
    Complete set of calculated indicators for one symbol/timeframe.
    This is what all three AI agents receive as input.
    """

    symbol: str
    timeframe: str
    candles_used: int = 0

    # Trend
    ema: Optional[EMACrossSignal] = None
    macd: Optional[MACDSignal] = None
    rsi: Optional[RSISignal] = None
    adx: Optional[ADXData] = None

    # Volatility
    atr: Optional[ATRData] = None
    bollinger: Optional[BollingerBands] = None

    # Volume-based
    vwap: Optional[VWAPData] = None

    # Higher timeframe context
    higher_tf_trend: Optional[TrendDirection] = None
    higher_tf_ema_trend: Optional[TrendDirection] = None
