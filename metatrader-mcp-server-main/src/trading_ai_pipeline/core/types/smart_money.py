"""
Smart Money Concept (SMC) type definitions.

BOS, CHoCH, FVG, Order Blocks, Liquidity Sweeps.
Python detects these structures; AI evaluates their trading significance.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class StructureType(str, Enum):
    BOS_BULLISH = "bos_bullish"       # Break of Structure up
    BOS_BEARISH = "bos_bearish"       # Break of Structure down
    CHOCH_BULLISH = "choch_bullish"   # Change of Character (bearish → bullish)
    CHOCH_BEARISH = "choch_bearish"   # Change of Character (bullish → bearish)


class FVGType(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class OrderBlockType(str, Enum):
    BULLISH = "bullish"    # last bearish candle before bullish move
    BEARISH = "bearish"    # last bullish candle before bearish move


class LiquidityType(str, Enum):
    BUY_SIDE = "buy_side"     # above swing highs (stops of shorts)
    SELL_SIDE = "sell_side"   # below swing lows (stops of longs)
    EQUAL_HIGHS = "equal_highs"
    EQUAL_LOWS = "equal_lows"


class StructureBreak(BaseModel):
    """
    BOS (Break of Structure) or CHoCH (Change of Character).
    Python detects by comparing swing points.
    """

    structure_type: StructureType
    broken_level: float           # price level that was broken
    break_candle_index: int = 0   # bars ago (0 = latest)
    break_candle_close: float = 0.0
    confirmed: bool = False       # candle closed beyond the level
    higher_timeframe_aligned: bool = False
    internal_bos: bool = False    # minor BOS within larger structure


class FairValueGap(BaseModel):
    """
    Fair Value Gap (FVG) / imbalance.
    3-candle pattern: gap between candle[n-2].high and candle[n].low (bullish)
    or candle[n-2].low and candle[n].high (bearish).
    """

    fvg_type: FVGType
    gap_upper: float
    gap_lower: float
    gap_mid: float
    created_bars_ago: int = 0
    partially_filled: bool = False
    fully_filled: bool = False
    mitigated: bool = False        # price returned to gap
    strength: int = Field(default=5, ge=1, le=10)


class OrderBlock(BaseModel):
    """
    Order Block — institutional order zone.
    Last opposite candle before a significant impulsive move.
    """

    ob_type: OrderBlockType
    zone_upper: float
    zone_lower: float
    zone_mid: float
    created_bars_ago: int = 0
    has_fvg: bool = False          # OB with embedded FVG = stronger
    has_been_tested: bool = False
    test_count: int = 0
    still_valid: bool = True       # price hasn't closed through it
    strength: int = Field(default=5, ge=1, le=10)


class LiquiditySweep(BaseModel):
    """
    Liquidity sweep — price briefly broke a level to grab stops, then reversed.
    """

    liquidity_type: LiquidityType
    swept_level: float
    sweep_high: float
    sweep_low: float
    swept_bars_ago: int = 0
    reversal_confirmed: bool = False   # strong reversal candle after sweep
    followed_by_bos: bool = False      # BOS/CHoCH after sweep = high probability


class SmartMoneyBundle(BaseModel):
    """
    Complete SMC analysis output from Python calculations.
    Passed to Smart Money AI agent as structured input.
    """

    symbol: str
    timeframe: str

    # Market structure
    current_structure: Optional[StructureType] = None
    recent_bos: Optional[StructureBreak] = None
    recent_choch: Optional[StructureBreak] = None

    # FVGs (sorted nearest to current price first)
    active_fvgs: List[FairValueGap] = Field(default_factory=list)
    nearest_fvg: Optional[FairValueGap] = None

    # Order Blocks
    active_order_blocks: List[OrderBlock] = Field(default_factory=list)
    nearest_ob: Optional[OrderBlock] = None

    # Liquidity
    recent_liquidity_sweep: Optional[LiquiditySweep] = None
    buy_side_liquidity_above: Optional[float] = None   # price level
    sell_side_liquidity_below: Optional[float] = None

    # Higher timeframe SMC alignment
    htf_structure: Optional[StructureType] = None
    htf_ob_nearby: bool = False
    htf_fvg_nearby: bool = False

    # Premium / Discount
    in_premium_zone: bool = False    # price above range 50%
    in_discount_zone: bool = False   # price below range 50%
    equilibrium_price: Optional[float] = None
