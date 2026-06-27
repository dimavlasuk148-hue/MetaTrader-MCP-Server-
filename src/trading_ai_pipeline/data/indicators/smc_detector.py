"""
Smart Money Concept (SMC) Detector — pure Python.

Detects BOS, CHoCH, FVG, Order Blocks, and Liquidity Sweeps.
All results are deterministic. AI reads these, never computes them.
"""

import logging
from typing import List, Optional, Tuple

import numpy as np

from ...core.types.market_data import OHLCV
from ...core.types.smart_money import (
    FVGType,
    FairValueGap,
    LiquiditySweep,
    LiquidityType,
    OrderBlock,
    OrderBlockType,
    SmartMoneyBundle,
    StructureBreak,
    StructureType,
)

logger = logging.getLogger("SMCDetector")


# ─────────────────────────────────────────────
# Swing point detection (SMC uses larger window)
# ─────────────────────────────────────────────

def _swing_highs(highs: np.ndarray, window: int = 5) -> List[int]:
    swings = []
    for i in range(window, len(highs) - window):
        if all(highs[i] > highs[i - j] for j in range(1, window + 1)) and \
           all(highs[i] > highs[i + j] for j in range(1, window + 1)):
            swings.append(i)
    return swings


def _swing_lows(lows: np.ndarray, window: int = 5) -> List[int]:
    swings = []
    for i in range(window, len(lows) - window):
        if all(lows[i] < lows[i - j] for j in range(1, window + 1)) and \
           all(lows[i] < lows[i + j] for j in range(1, window + 1)):
            swings.append(i)
    return swings


# ─────────────────────────────────────────────
# BOS and CHoCH detection
# ─────────────────────────────────────────────

def detect_market_structure(
    ohlcv: OHLCV,
    lookback: int = 50,
) -> Tuple[Optional[StructureBreak], Optional[StructureBreak], Optional[StructureType]]:
    """
    Detect the most recent BOS and CHoCH.

    Returns:
        (recent_bos, recent_choch, current_structure_type)
    """
    highs = np.array(ohlcv.highs())
    lows = np.array(ohlcv.lows())
    closes = np.array(ohlcv.closes())
    n = len(closes)

    if n < 20:
        return None, None, None

    sh_idxs = _swing_highs(highs)
    sl_idxs = _swing_lows(lows)

    if len(sh_idxs) < 2 or len(sl_idxs) < 2:
        return None, None, None

    recent_bos: Optional[StructureBreak] = None
    recent_choch: Optional[StructureBreak] = None

    # Determine current higher-high / higher-low sequence (bullish) or lower sequence
    # Use last 3 swing highs and lows
    last_shs = sh_idxs[-3:]
    last_sls = sl_idxs[-3:]

    sh_vals = [float(highs[i]) for i in last_shs]
    sl_vals = [float(lows[i]) for i in last_sls]

    # BOS Bullish: close breaks above the last significant swing high
    latest_sh = float(highs[sh_idxs[-1]])
    latest_sl = float(lows[sl_idxs[-1]])
    current_close = float(closes[-1])

    # Check recent candles for structure break
    for i in range(max(1, n - lookback), n):
        c = closes[i]
        bars_ago = n - 1 - i

        # BOS bullish: close above last swing high
        if c > latest_sh and (recent_bos is None or recent_bos.structure_type != StructureType.BOS_BULLISH):
            recent_bos = StructureBreak(
                structure_type=StructureType.BOS_BULLISH,
                broken_level=latest_sh,
                break_candle_index=bars_ago,
                break_candle_close=float(c),
                confirmed=True,
            )

        # BOS bearish: close below last swing low
        elif c < latest_sl and (recent_bos is None or recent_bos.structure_type != StructureType.BOS_BEARISH):
            recent_bos = StructureBreak(
                structure_type=StructureType.BOS_BEARISH,
                broken_level=latest_sl,
                break_candle_index=bars_ago,
                break_candle_close=float(c),
                confirmed=True,
            )

    # CHoCH: trend reversal — bullish sequence broken bearishly or vice versa
    # Simplified: if last 2 swing highs are decreasing AND last BOS was bullish → CHoCH bearish
    if len(sh_vals) >= 2 and sh_vals[-1] < sh_vals[-2]:
        # Lower highs forming while previously bullish → CHoCH bearish
        recent_choch = StructureBreak(
            structure_type=StructureType.CHOCH_BEARISH,
            broken_level=sh_vals[-2],
            break_candle_index=0,
            break_candle_close=current_close,
            confirmed=True,
        )
    elif len(sl_vals) >= 2 and sl_vals[-1] > sl_vals[-2]:
        # Higher lows forming while previously bearish → CHoCH bullish
        recent_choch = StructureBreak(
            structure_type=StructureType.CHOCH_BULLISH,
            broken_level=sl_vals[-2],
            break_candle_index=0,
            break_candle_close=current_close,
            confirmed=True,
        )

    # Current structure
    current_structure = None
    if recent_choch:
        current_structure = recent_choch.structure_type
    elif recent_bos:
        current_structure = recent_bos.structure_type

    return recent_bos, recent_choch, current_structure


# ─────────────────────────────────────────────
# Fair Value Gap detection
# ─────────────────────────────────────────────

def detect_fvgs(ohlcv: OHLCV, lookback: int = 50, max_fvgs: int = 5) -> List[FairValueGap]:
    """
    Detect active (unfilled) Fair Value Gaps.

    FVG Bullish: candle[i-2].high < candle[i].low  (gap between them)
    FVG Bearish: candle[i-2].low  > candle[i].high (gap between them)
    """
    candles = ohlcv.candles
    n = len(candles)
    if n < 3:
        return []

    fvgs: List[FairValueGap] = []
    current_price = candles[-1].close

    start = max(2, n - lookback)
    for i in range(start, n):
        c0 = candles[i - 2]
        c1 = candles[i - 1]  # impulse candle
        c2 = candles[i]
        bars_ago = n - 1 - i

        # Bullish FVG
        if c0.high < c2.low:
            gap_lower = c0.high
            gap_upper = c2.low
            gap_mid = (gap_upper + gap_lower) / 2
            partially_filled = gap_lower <= current_price <= gap_upper
            fully_filled = current_price < gap_lower
            fvgs.append(FairValueGap(
                fvg_type=FVGType.BULLISH,
                gap_upper=gap_upper,
                gap_lower=gap_lower,
                gap_mid=gap_mid,
                created_bars_ago=bars_ago,
                partially_filled=partially_filled,
                fully_filled=fully_filled,
                mitigated=fully_filled or partially_filled,
                strength=min(int((gap_upper - gap_lower) / c1.body_size * 5) + 1, 10)
                    if c1.body_size > 0 else 5,
            ))

        # Bearish FVG
        elif c0.low > c2.high:
            gap_upper = c0.low
            gap_lower = c2.high
            gap_mid = (gap_upper + gap_lower) / 2
            partially_filled = gap_lower <= current_price <= gap_upper
            fully_filled = current_price > gap_upper
            fvgs.append(FairValueGap(
                fvg_type=FVGType.BEARISH,
                gap_upper=gap_upper,
                gap_lower=gap_lower,
                gap_mid=gap_mid,
                created_bars_ago=bars_ago,
                partially_filled=partially_filled,
                fully_filled=fully_filled,
                mitigated=fully_filled or partially_filled,
                strength=min(int((gap_upper - gap_lower) / c1.body_size * 5) + 1, 10)
                    if c1.body_size > 0 else 5,
            ))

    # Filter out fully filled, sort by proximity
    active = [f for f in fvgs if not f.fully_filled]
    active.sort(key=lambda f: abs(f.gap_mid - current_price))
    return active[:max_fvgs]


# ─────────────────────────────────────────────
# Order Block detection
# ─────────────────────────────────────────────

def detect_order_blocks(ohlcv: OHLCV, lookback: int = 50, max_obs: int = 5) -> List[OrderBlock]:
    """
    Detect Order Blocks (last opposite candle before an impulsive move).

    Bullish OB: last bearish candle before a significant bullish impulse.
    Bearish OB: last bullish candle before a significant bearish impulse.
    """
    candles = ohlcv.candles
    n = len(candles)
    if n < 5:
        return []

    obs: List[OrderBlock] = []
    current_price = candles[-1].close
    closes = np.array(ohlcv.closes())

    # Measure average body size for "significant impulse" threshold
    bodies = [abs(c.close - c.open) for c in candles[-50:] if abs(c.close - c.open) > 0]
    avg_body = float(np.mean(bodies)) if bodies else 0.0001
    impulse_threshold = avg_body * 2.5

    start = max(3, n - lookback)
    for i in range(start, n - 2):
        curr = candles[i]
        next1 = candles[i + 1]
        next2 = candles[i + 2] if i + 2 < n else None
        bars_ago = n - 1 - i

        # Bullish OB: bearish candle followed by strong bullish move
        if curr.is_bearish:
            fwd_close = next2.close if next2 else next1.close
            if fwd_close - next1.open > impulse_threshold and next1.is_bullish:
                zone_upper = curr.open   # top of bearish candle
                zone_lower = curr.close  # bottom of bearish candle (close)
                still_valid = current_price > zone_lower  # price hasn't closed below
                if still_valid:
                    obs.append(OrderBlock(
                        ob_type=OrderBlockType.BULLISH,
                        zone_upper=zone_upper,
                        zone_lower=zone_lower,
                        zone_mid=(zone_upper + zone_lower) / 2,
                        created_bars_ago=bars_ago,
                        still_valid=still_valid,
                        strength=min(int(impulse_threshold / avg_body * 2), 10),
                    ))

        # Bearish OB: bullish candle followed by strong bearish move
        if curr.is_bullish:
            fwd_close = next2.close if next2 else next1.close
            if next1.open - fwd_close > impulse_threshold and next1.is_bearish:
                zone_upper = curr.close  # top of bullish candle
                zone_lower = curr.open   # bottom of bullish candle
                still_valid = current_price < zone_upper
                if still_valid:
                    obs.append(OrderBlock(
                        ob_type=OrderBlockType.BEARISH,
                        zone_upper=zone_upper,
                        zone_lower=zone_lower,
                        zone_mid=(zone_upper + zone_lower) / 2,
                        created_bars_ago=bars_ago,
                        still_valid=still_valid,
                        strength=min(int(impulse_threshold / avg_body * 2), 10),
                    ))

    obs.sort(key=lambda ob: abs(ob.zone_mid - current_price))
    return obs[:max_obs]


# ─────────────────────────────────────────────
# Liquidity Sweep detection
# ─────────────────────────────────────────────

def detect_liquidity_sweeps(ohlcv: OHLCV, lookback: int = 30) -> Optional[LiquiditySweep]:
    """
    Detect the most recent liquidity sweep (stop hunt) in price action.
    """
    candles = ohlcv.candles
    n = len(candles)
    if n < 10:
        return None

    highs = np.array(ohlcv.highs())
    lows = np.array(ohlcv.lows())

    sh_idxs = _swing_highs(highs, window=3)
    sl_idxs = _swing_lows(lows, window=3)

    if len(sh_idxs) < 2 or len(sl_idxs) < 2:
        return None

    # Check last `lookback` candles for a wick beyond prior swing then close back
    start = max(1, n - lookback)
    current_close = float(candles[-1].close)

    for i in range(n - 1, start, -1):
        c = candles[i]
        bars_ago = n - 1 - i

        # Buy-side liquidity sweep: wick above prior swing high, then closed back below
        prior_sh = float(highs[sh_idxs[-1]]) if sh_idxs else None
        if prior_sh and c.high > prior_sh and c.close < prior_sh:
            return LiquiditySweep(
                liquidity_type=LiquidityType.BUY_SIDE,
                swept_level=prior_sh,
                sweep_high=c.high,
                sweep_low=c.low,
                swept_bars_ago=bars_ago,
                reversal_confirmed=c.is_bearish and c.body_size > (c.high - c.low) * 0.4,
            )

        # Sell-side liquidity sweep: wick below prior swing low, then closed back above
        prior_sl = float(lows[sl_idxs[-1]]) if sl_idxs else None
        if prior_sl and c.low < prior_sl and c.close > prior_sl:
            return LiquiditySweep(
                liquidity_type=LiquidityType.SELL_SIDE,
                swept_level=prior_sl,
                sweep_high=c.high,
                sweep_low=c.low,
                swept_bars_ago=bars_ago,
                reversal_confirmed=c.is_bullish and c.body_size > (c.high - c.low) * 0.4,
            )

    return None


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def detect_smart_money(
    ohlcv: OHLCV,
    current_price: float,
    higher_tf_ohlcv: Optional[OHLCV] = None,
) -> SmartMoneyBundle:
    """
    Run full SMC analysis on an OHLCV dataset.

    Returns:
        SmartMoneyBundle with all SMC structures filled in.
    """
    recent_bos, recent_choch, current_structure = detect_market_structure(ohlcv)
    active_fvgs = detect_fvgs(ohlcv)
    active_obs = detect_order_blocks(ohlcv)
    sweep = detect_liquidity_sweeps(ohlcv)

    # Nearest FVG and OB
    nearest_fvg = active_fvgs[0] if active_fvgs else None
    nearest_ob = active_obs[0] if active_obs else None

    # Buy/sell side liquidity levels (from swing points)
    highs = np.array(ohlcv.highs())
    lows = np.array(ohlcv.lows())
    sh_idxs = _swing_highs(highs)
    sl_idxs = _swing_lows(lows)

    bsl = float(highs[sh_idxs[-1]]) if sh_idxs else None  # buy side liquidity above
    ssl = float(lows[sl_idxs[-1]]) if sl_idxs else None   # sell side liquidity below

    # Premium / Discount zones
    in_premium = False
    in_discount = False
    equilibrium = None
    if bsl and ssl:
        equilibrium = (bsl + ssl) / 2
        in_premium = current_price > equilibrium
        in_discount = current_price < equilibrium

    # Higher TF structure
    htf_structure = None
    if higher_tf_ohlcv:
        htf_bos, htf_choch, htf_struct = detect_market_structure(higher_tf_ohlcv)
        htf_structure = htf_struct

    return SmartMoneyBundle(
        symbol=ohlcv.symbol,
        timeframe=ohlcv.timeframe.value,
        current_structure=current_structure,
        recent_bos=recent_bos,
        recent_choch=recent_choch,
        active_fvgs=active_fvgs,
        nearest_fvg=nearest_fvg,
        active_order_blocks=active_obs,
        nearest_ob=nearest_ob,
        recent_liquidity_sweep=sweep,
        buy_side_liquidity_above=bsl,
        sell_side_liquidity_below=ssl,
        htf_structure=htf_structure,
        in_premium_zone=in_premium,
        in_discount_zone=in_discount,
        equilibrium_price=equilibrium,
    )
