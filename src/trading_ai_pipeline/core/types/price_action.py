"""
Price action type definitions.

Structures for support/resistance, patterns, and breakouts.
Python detects raw levels; AI interprets their significance.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class LevelType(str, Enum):
    SUPPORT = "support"
    RESISTANCE = "resistance"
    PIVOT = "pivot"
    SWING_HIGH = "swing_high"
    SWING_LOW = "swing_low"


class CandlePatternType(str, Enum):
    # Reversal
    HAMMER = "hammer"
    SHOOTING_STAR = "shooting_star"
    ENGULFING_BULL = "engulfing_bull"
    ENGULFING_BEAR = "engulfing_bear"
    DOJI = "doji"
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"
    PIN_BAR_BULL = "pin_bar_bull"
    PIN_BAR_BEAR = "pin_bar_bear"
    # Continuation
    INSIDE_BAR = "inside_bar"
    OUTSIDE_BAR = "outside_bar"
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    THREE_BLACK_CROWS = "three_black_crows"


class BreakoutType(str, Enum):
    RESISTANCE_BREAK = "resistance_break"
    SUPPORT_BREAK = "support_break"
    RANGE_BREAK_UP = "range_break_up"
    RANGE_BREAK_DOWN = "range_break_down"
    FALSE_BREAK = "false_break"


class SupportResistanceLevel(BaseModel):
    """A detected support or resistance zone."""

    level_type: LevelType
    price: float
    price_zone_upper: float
    price_zone_lower: float
    strength: int = Field(ge=1, le=10, description="Touch count / importance 1-10")
    timeframe_origin: str = ""
    bars_ago: Optional[int] = None
    is_key_level: bool = False
    was_broken: bool = False
    retest_likely: bool = False


class CandlePattern(BaseModel):
    """Detected candle pattern at a specific bar."""

    pattern_type: CandlePatternType
    bar_index: int = 0        # 0 = current/latest bar
    price_at_pattern: float = 0.0
    is_at_key_level: bool = False
    is_at_support: bool = False
    is_at_resistance: bool = False
    confirmation_needed: bool = True
    bullish_signal: bool = False
    bearish_signal: bool = False


class BreakoutSignal(BaseModel):
    """Detected breakout or false break."""

    breakout_type: BreakoutType
    broken_level: SupportResistanceLevel
    breakout_candle_close: float
    confirmed: bool = False
    volume_expansion: bool = False
    retest_occurred: bool = False


class RangeInfo(BaseModel):
    """Detected trading range (consolidation zone)."""

    range_high: float
    range_low: float
    range_mid: float
    width_pips: float = 0.0
    bars_in_range: int = 0
    is_active: bool = True


class PriceActionBundle(BaseModel):
    """
    Complete price action analysis output from Python calculations.
    Passed to Price Action AI agent as structured input.
    """

    symbol: str
    timeframe: str

    # Key levels (sorted by proximity to current price)
    nearest_resistance_levels: List[SupportResistanceLevel] = Field(default_factory=list)
    nearest_support_levels: List[SupportResistanceLevel] = Field(default_factory=list)

    # Patterns on last 3 bars
    recent_patterns: List[CandlePattern] = Field(default_factory=list)

    # Breakouts
    recent_breakout: Optional[BreakoutSignal] = None

    # Range
    active_range: Optional[RangeInfo] = None
    in_range: bool = False

    # Swing structure
    last_swing_high: Optional[float] = None
    last_swing_low: Optional[float] = None
    swing_high_bars_ago: Optional[int] = None
    swing_low_bars_ago: Optional[int] = None

    # Current price context
    current_price: float = 0.0
    distance_to_nearest_resistance_pips: Optional[float] = None
    distance_to_nearest_support_pips: Optional[float] = None
