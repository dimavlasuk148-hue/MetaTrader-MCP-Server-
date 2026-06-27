"""
Price Action Detector — pure Python.

Detects support/resistance levels, candle patterns, swing points, and breakouts.
AI reads these results — never detects them independently.
"""

import logging
from typing import List, Optional, Tuple

import numpy as np

from ...core.types.market_data import OHLCV, Candle
from ...core.types.price_action import (
    BreakoutSignal,
    BreakoutType,
    CandlePattern,
    CandlePatternType,
    LevelType,
    PriceActionBundle,
    RangeInfo,
    SupportResistanceLevel,
)

logger = logging.getLogger("PriceActionDetector")


# ─────────────────────────────────────────────
# Swing point detection
# ─────────────────────────────────────────────

def _find_swing_highs(highs: np.ndarray, window: int = 3) -> List[int]:
    """Find indices of swing highs."""
    swings = []
    for i in range(window, len(highs) - window):
        if all(highs[i] >= highs[i - j] for j in range(1, window + 1)) and \
           all(highs[i] >= highs[i + j] for j in range(1, window + 1)):
            swings.append(i)
    return swings


def _find_swing_lows(lows: np.ndarray, window: int = 3) -> List[int]:
    """Find indices of swing lows."""
    swings = []
    for i in range(window, len(lows) - window):
        if all(lows[i] <= lows[i - j] for j in range(1, window + 1)) and \
           all(lows[i] <= lows[i + j] for j in range(1, window + 1)):
            swings.append(i)
    return swings


# ─────────────────────────────────────────────
# Support / Resistance detection
# ─────────────────────────────────────────────

def _cluster_levels(prices: List[float], tolerance_pct: float = 0.001) -> List[Tuple[float, int]]:
    """
    Cluster nearby price levels.
    Returns list of (cluster_price, touch_count) sorted by touch count desc.
    """
    if not prices:
        return []

    clusters: List[Tuple[float, int]] = []
    used = [False] * len(prices)

    for i, price in enumerate(prices):
        if used[i]:
            continue
        cluster = [price]
        used[i] = True
        for j in range(i + 1, len(prices)):
            if not used[j] and abs(prices[j] - price) / price < tolerance_pct:
                cluster.append(prices[j])
                used[j] = True
        clusters.append((float(np.mean(cluster)), len(cluster)))

    return sorted(clusters, key=lambda x: x[1], reverse=True)


def detect_support_resistance(
    ohlcv: OHLCV,
    current_price: float,
    max_levels: int = 5,
    point: float = 0.00001,
) -> Tuple[List[SupportResistanceLevel], List[SupportResistanceLevel]]:
    """
    Detect support and resistance levels from swing points.

    Returns:
        (resistance_levels, support_levels) sorted nearest to current price first.
    """
    highs = np.array(ohlcv.highs())
    lows = np.array(ohlcv.lows())
    closes = np.array(ohlcv.closes())
    n = len(closes)

    # Find swings
    swing_high_idxs = _find_swing_highs(highs, window=3)
    swing_low_idxs = _find_swing_lows(lows, window=3)

    # Cluster swing high prices → resistance
    sh_prices = [float(highs[i]) for i in swing_high_idxs]
    sl_prices = [float(lows[i]) for i in swing_low_idxs]

    tolerance = current_price * 0.0005  # 0.05%
    res_clusters = _cluster_levels(sh_prices, 0.001)
    sup_clusters = _cluster_levels(sl_prices, 0.001)

    zone_width = current_price * 0.001  # 0.1% zone

    resistances = []
    for price, touches in res_clusters[:max_levels * 2]:
        if price <= current_price:
            continue
        resistances.append(
            SupportResistanceLevel(
                level_type=LevelType.RESISTANCE,
                price=price,
                price_zone_upper=price + zone_width,
                price_zone_lower=price - zone_width,
                strength=min(touches * 2, 10),
                is_key_level=touches >= 3,
                was_broken=False,
            )
        )

    supports = []
    for price, touches in sup_clusters[:max_levels * 2]:
        if price >= current_price:
            continue
        supports.append(
            SupportResistanceLevel(
                level_type=LevelType.SUPPORT,
                price=price,
                price_zone_upper=price + zone_width,
                price_zone_lower=price - zone_width,
                strength=min(touches * 2, 10),
                is_key_level=touches >= 3,
                was_broken=False,
            )
        )

    # Sort by proximity to current price
    resistances.sort(key=lambda x: x.price - current_price)
    supports.sort(key=lambda x: current_price - x.price)

    return resistances[:max_levels], supports[:max_levels]


# ─────────────────────────────────────────────
# Candle pattern detection
# ─────────────────────────────────────────────

def _detect_hammer(candle: Candle) -> bool:
    """Hammer: small body, long lower wick (>2x body), tiny upper wick."""
    if candle.body_size == 0:
        return False
    return (
        candle.lower_wick >= 2 * candle.body_size
        and candle.upper_wick <= candle.body_size * 0.3
    )


def _detect_shooting_star(candle: Candle) -> bool:
    """Shooting Star: small body, long upper wick, tiny lower wick."""
    if candle.body_size == 0:
        return False
    return (
        candle.upper_wick >= 2 * candle.body_size
        and candle.lower_wick <= candle.body_size * 0.3
    )


def _detect_engulfing(prev: Candle, curr: Candle) -> Tuple[bool, bool]:
    """Bullish/bearish engulfing pattern."""
    bull = (
        prev.is_bearish
        and curr.is_bullish
        and curr.open <= prev.close
        and curr.close >= prev.open
    )
    bear = (
        prev.is_bullish
        and curr.is_bearish
        and curr.open >= prev.close
        and curr.close <= prev.open
    )
    return bull, bear


def _detect_pin_bar(candle: Candle) -> Tuple[bool, bool]:
    """Bullish/bearish pin bar."""
    total = candle.high - candle.low
    if total == 0:
        return False, False
    bull = (
        candle.lower_wick / total >= 0.6
        and candle.body_size / total <= 0.3
    )
    bear = (
        candle.upper_wick / total >= 0.6
        and candle.body_size / total <= 0.3
    )
    return bull, bear


def detect_candle_patterns(
    ohlcv: OHLCV,
    support_levels: List[SupportResistanceLevel],
    resistance_levels: List[SupportResistanceLevel],
    lookback: int = 3,
) -> List[CandlePattern]:
    """Detect candle patterns in the last `lookback` candles."""
    candles = ohlcv.candles
    if len(candles) < 2:
        return []

    patterns: List[CandlePattern] = []
    zone_pct = 0.002  # within 0.2% of level = "at level"

    def _near_level(price: float, levels: List[SupportResistanceLevel]) -> bool:
        return any(abs(price - lvl.price) / lvl.price < zone_pct for lvl in levels)

    # Check last N bars
    start = max(1, len(candles) - lookback)
    for i in range(start, len(candles)):
        curr = candles[i]
        prev = candles[i - 1]
        bar_index = len(candles) - 1 - i  # 0 = latest

        at_support = _near_level(curr.close, support_levels)
        at_resistance = _near_level(curr.close, resistance_levels)

        # Hammer
        if _detect_hammer(curr):
            patterns.append(CandlePattern(
                pattern_type=CandlePatternType.HAMMER,
                bar_index=bar_index,
                price_at_pattern=curr.close,
                is_at_support=at_support,
                is_at_resistance=at_resistance,
                is_at_key_level=at_support or at_resistance,
                bullish_signal=True,
                confirmation_needed=True,
            ))

        # Shooting star
        if _detect_shooting_star(curr):
            patterns.append(CandlePattern(
                pattern_type=CandlePatternType.SHOOTING_STAR,
                bar_index=bar_index,
                price_at_pattern=curr.close,
                is_at_support=at_support,
                is_at_resistance=at_resistance,
                is_at_key_level=at_support or at_resistance,
                bearish_signal=True,
                confirmation_needed=True,
            ))

        # Doji
        if curr.is_doji:
            patterns.append(CandlePattern(
                pattern_type=CandlePatternType.DOJI,
                bar_index=bar_index,
                price_at_pattern=curr.close,
                is_at_key_level=at_support or at_resistance,
                confirmation_needed=True,
            ))

        # Engulfing
        bull_eng, bear_eng = _detect_engulfing(prev, curr)
        if bull_eng:
            patterns.append(CandlePattern(
                pattern_type=CandlePatternType.ENGULFING_BULL,
                bar_index=bar_index,
                price_at_pattern=curr.close,
                is_at_support=at_support,
                is_at_key_level=at_support or at_resistance,
                bullish_signal=True,
                confirmation_needed=False,
            ))
        if bear_eng:
            patterns.append(CandlePattern(
                pattern_type=CandlePatternType.ENGULFING_BEAR,
                bar_index=bar_index,
                price_at_pattern=curr.close,
                is_at_resistance=at_resistance,
                is_at_key_level=at_support or at_resistance,
                bearish_signal=True,
                confirmation_needed=False,
            ))

        # Pin bar
        bull_pin, bear_pin = _detect_pin_bar(curr)
        if bull_pin:
            patterns.append(CandlePattern(
                pattern_type=CandlePatternType.PIN_BAR_BULL,
                bar_index=bar_index,
                price_at_pattern=curr.close,
                is_at_support=at_support,
                is_at_key_level=at_support or at_resistance,
                bullish_signal=True,
                confirmation_needed=True,
            ))
        if bear_pin:
            patterns.append(CandlePattern(
                pattern_type=CandlePatternType.PIN_BAR_BEAR,
                bar_index=bar_index,
                price_at_pattern=curr.close,
                is_at_resistance=at_resistance,
                is_at_key_level=at_support or at_resistance,
                bearish_signal=True,
                confirmation_needed=True,
            ))

    return patterns


# ─────────────────────────────────────────────
# Range detection
# ─────────────────────────────────────────────

def detect_range(ohlcv: OHLCV, lookback: int = 20, point: float = 0.00001) -> Optional[RangeInfo]:
    """Detect if price is in a consolidation range."""
    if ohlcv.count < lookback:
        return None

    recent = ohlcv.candles[-lookback:]
    highs = [c.high for c in recent]
    lows = [c.low for c in recent]

    range_high = max(highs)
    range_low = min(lows)
    spread = range_high - range_low
    avg_price = (range_high + range_low) / 2

    # In a range if spread is < 1% of price and ADX would be low
    is_range = (spread / avg_price) < 0.015 if avg_price > 0 else False

    return RangeInfo(
        range_high=range_high,
        range_low=range_low,
        range_mid=(range_high + range_low) / 2,
        width_pips=spread / point if point > 0 else spread,
        bars_in_range=lookback,
        is_active=is_range,
    )


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def detect_price_action(
    ohlcv: OHLCV,
    current_price: float,
    point: float = 0.00001,
) -> PriceActionBundle:
    """
    Run full price action analysis on an OHLCV dataset.

    Returns:
        PriceActionBundle with all price action structures filled in.
    """
    highs = np.array(ohlcv.highs())
    lows = np.array(ohlcv.lows())
    n = len(ohlcv.candles)

    # Support / Resistance
    resistances, supports = detect_support_resistance(ohlcv, current_price, point=point)

    # Distances to nearest levels
    dist_res = None
    dist_sup = None
    if resistances:
        dist_res = (resistances[0].price - current_price) / point
    if supports:
        dist_sup = (current_price - supports[0].price) / point

    # Candle patterns
    patterns = detect_candle_patterns(ohlcv, supports, resistances)

    # Range
    range_info = detect_range(ohlcv, lookback=20, point=point)
    in_range = range_info.is_active if range_info else False

    # Swing points
    swing_high_idxs = _find_swing_highs(highs)
    swing_low_idxs = _find_swing_lows(lows)

    last_sh = None
    last_sh_bars = None
    if swing_high_idxs:
        last_sh = float(highs[swing_high_idxs[-1]])
        last_sh_bars = n - 1 - swing_high_idxs[-1]

    last_sl = None
    last_sl_bars = None
    if swing_low_idxs:
        last_sl = float(lows[swing_low_idxs[-1]])
        last_sl_bars = n - 1 - swing_low_idxs[-1]

    return PriceActionBundle(
        symbol=ohlcv.symbol,
        timeframe=ohlcv.timeframe.value,
        nearest_resistance_levels=resistances,
        nearest_support_levels=supports,
        recent_patterns=patterns,
        active_range=range_info,
        in_range=in_range,
        last_swing_high=last_sh,
        last_swing_low=last_sl,
        swing_high_bars_ago=last_sh_bars,
        swing_low_bars_ago=last_sl_bars,
        current_price=current_price,
        distance_to_nearest_resistance_pips=dist_res,
        distance_to_nearest_support_pips=dist_sup,
    )
