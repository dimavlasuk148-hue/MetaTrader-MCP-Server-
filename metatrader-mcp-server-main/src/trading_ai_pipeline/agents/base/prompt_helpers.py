"""
Prompt construction helpers.

Serialize Pydantic models into clean, readable text blocks for LLM prompts.
"""

import json
from typing import Any, Optional

from ...core.types.indicators import IndicatorBundle
from ...core.types.price_action import PriceActionBundle
from ...core.types.smart_money import SmartMoneyBundle


def indicators_to_text(bundle: IndicatorBundle) -> str:
    """Serialize IndicatorBundle into a concise text block for LLM prompts."""
    lines = [
        f"Symbol: {bundle.symbol} | Timeframe: {bundle.timeframe} | Candles: {bundle.candles_used}",
        "",
        "=== TREND INDICATORS ===",
    ]

    if bundle.ema:
        e = bundle.ema
        lines.append(
            f"EMA({e.ema_fast_period}/{e.ema_slow_period}): fast={e.ema_fast_value:.5f} slow={e.ema_slow_value:.5f} | "
            f"Trend: {e.trend.value} | "
            f"{'BULLISH CROSSOVER' if e.crossover_bullish else 'BEARISH CROSSOVER' if e.crossover_bearish else 'no recent cross'}"
            + (f" ({e.bars_since_cross} bars ago)" if e.bars_since_cross else "")
        )
        if e.ema_200_value:
            lines.append(
                f"EMA200: {e.ema_200_value:.5f} | Price is {'ABOVE' if e.price_above_ema200 else 'BELOW'} EMA200"
            )

    if bundle.macd:
        m = bundle.macd
        lines.append(
            f"MACD: line={m.macd_line:.5f} signal={m.signal_line:.5f} hist={m.histogram:.5f} | "
            f"{'Above zero' if m.above_zero else 'Below zero'} | "
            f"Momentum: {'expanding' if m.histogram_expanding else 'shrinking' if m.histogram_shrinking else 'neutral'}"
        )
        if m.bullish_divergence:
            lines.append("  *** MACD BULLISH DIVERGENCE DETECTED ***")
        if m.bearish_divergence:
            lines.append("  *** MACD BEARISH DIVERGENCE DETECTED ***")

    if bundle.rsi:
        r = bundle.rsi
        lines.append(
            f"RSI({r.period}): {r.value:.1f} | "
            + ("OVERBOUGHT" if r.is_overbought else "OVERSOLD" if r.is_oversold else "Neutral (30-70)")
        )
        if r.bullish_divergence:
            lines.append("  *** RSI BULLISH DIVERGENCE DETECTED ***")
        if r.bearish_divergence:
            lines.append("  *** RSI BEARISH DIVERGENCE DETECTED ***")

    if bundle.adx:
        a = bundle.adx
        lines.append(
            f"ADX({a.period}): {a.adx_value:.1f} | +DI={a.plus_di:.1f} -DI={a.minus_di:.1f} | "
            f"{'TRENDING' if a.is_trending else 'RANGING'} | Strength: {a.trend_strength.value}"
        )

    lines.append("")
    lines.append("=== VOLATILITY ===")

    if bundle.atr:
        at = bundle.atr
        lines.append(
            f"ATR({at.period}): {at.value:.5f} ({at.value_in_pips:.1f} pips) | Volatility: {at.volatility_label}"
        )

    if bundle.bollinger:
        bb = bundle.bollinger
        lines.append(
            f"Bollinger({bb.period},{bb.std_dev}): upper={bb.upper:.5f} mid={bb.middle:.5f} lower={bb.lower:.5f} | "
            f"BW={bb.bandwidth:.4f} | Price position: {bb.price_position:.2f} (0=lower, 1=upper)"
        )
        if bb.squeeze:
            lines.append("  *** BOLLINGER SQUEEZE (low volatility breakout potential) ***")
        if bb.breakout_up:
            lines.append("  *** PRICE BROKE ABOVE UPPER BAND ***")
        if bb.breakout_down:
            lines.append("  *** PRICE BROKE BELOW LOWER BAND ***")

    if bundle.vwap:
        v = bundle.vwap
        lines.append(
            f"VWAP: {v.vwap:.5f} | Price is {'ABOVE' if v.price_above_vwap else 'BELOW'} VWAP | "
            f"Distance: {v.distance_pips:.5f}"
        )

    if bundle.higher_tf_trend or bundle.higher_tf_ema_trend:
        lines.append("")
        lines.append("=== HIGHER TIMEFRAME CONTEXT ===")
        if bundle.higher_tf_trend:
            lines.append(f"HTF Trend (EMA200): {bundle.higher_tf_trend.value}")
        if bundle.higher_tf_ema_trend:
            lines.append(f"HTF EMA alignment: {bundle.higher_tf_ema_trend.value}")

    return "\n".join(lines)


def price_action_to_text(bundle: PriceActionBundle) -> str:
    """Serialize PriceActionBundle into text for LLM prompts."""
    lines = [
        f"Symbol: {bundle.symbol} | Timeframe: {bundle.timeframe}",
        f"Current Price: {bundle.current_price:.5f}",
        "",
        "=== KEY LEVELS ===",
    ]

    if bundle.nearest_resistance_levels:
        lines.append("Resistance levels (nearest first):")
        for lvl in bundle.nearest_resistance_levels[:3]:
            dist = f"{bundle.distance_to_nearest_resistance_pips:.1f} pips" if bundle.distance_to_nearest_resistance_pips else "?"
            lines.append(
                f"  R: {lvl.price:.5f} (zone {lvl.price_zone_lower:.5f}-{lvl.price_zone_upper:.5f}) | "
                f"Strength: {lvl.strength}/10 | Key: {lvl.is_key_level}"
            )
    else:
        lines.append("No resistance levels detected")

    if bundle.nearest_support_levels:
        lines.append("Support levels (nearest first):")
        for lvl in bundle.nearest_support_levels[:3]:
            lines.append(
                f"  S: {lvl.price:.5f} (zone {lvl.price_zone_lower:.5f}-{lvl.price_zone_upper:.5f}) | "
                f"Strength: {lvl.strength}/10 | Key: {lvl.is_key_level}"
            )
    else:
        lines.append("No support levels detected")

    lines.append("")
    lines.append("=== CANDLE PATTERNS (last 3 bars) ===")
    if bundle.recent_patterns:
        for p in bundle.recent_patterns:
            signal = "BULLISH" if p.bullish_signal else "BEARISH" if p.bearish_signal else "neutral"
            lines.append(
                f"  {p.pattern_type.value} at {p.price_at_pattern:.5f} | "
                f"Signal: {signal} | At key level: {p.is_at_key_level} | "
                f"Confirmed: {not p.confirmation_needed}"
            )
    else:
        lines.append("  No significant candle patterns detected")

    lines.append("")
    lines.append("=== SWING STRUCTURE ===")
    if bundle.last_swing_high:
        lines.append(f"Last Swing High: {bundle.last_swing_high:.5f} ({bundle.swing_high_bars_ago} bars ago)")
    if bundle.last_swing_low:
        lines.append(f"Last Swing Low: {bundle.last_swing_low:.5f} ({bundle.swing_low_bars_ago} bars ago)")

    if bundle.in_range and bundle.active_range:
        r = bundle.active_range
        lines.append("")
        lines.append("=== RANGE ===")
        lines.append(
            f"PRICE IN RANGE: {r.range_low:.5f} - {r.range_high:.5f} | "
            f"Mid: {r.range_mid:.5f} | Width: {r.width_pips:.1f} pips"
        )

    return "\n".join(lines)


def smart_money_to_text(bundle: SmartMoneyBundle) -> str:
    """Serialize SmartMoneyBundle into text for LLM prompts."""
    lines = [
        f"Symbol: {bundle.symbol} | Timeframe: {bundle.timeframe}",
        "",
        "=== MARKET STRUCTURE ===",
    ]

    if bundle.current_structure:
        lines.append(f"Current Structure: {bundle.current_structure.value.upper()}")
    else:
        lines.append("Current Structure: UNDEFINED")

    if bundle.recent_bos:
        b = bundle.recent_bos
        lines.append(
            f"Recent BOS: {b.structure_type.value} | Level broken: {b.broken_level:.5f} | "
            f"{b.break_candle_index} bars ago | Confirmed: {b.confirmed}"
        )
    if bundle.recent_choch:
        c = bundle.recent_choch
        lines.append(
            f"Recent CHoCH: {c.structure_type.value} | Level: {c.broken_level:.5f} | "
            f"{c.break_candle_index} bars ago | Confirmed: {c.confirmed}"
        )

    lines.append("")
    lines.append("=== FAIR VALUE GAPS ===")
    if bundle.active_fvgs:
        for fvg in bundle.active_fvgs[:3]:
            lines.append(
                f"  FVG {fvg.fvg_type.value.upper()}: {fvg.gap_lower:.5f}-{fvg.gap_upper:.5f} | "
                f"Mid: {fvg.gap_mid:.5f} | Filled: {'partial' if fvg.partially_filled else 'no'} | "
                f"Strength: {fvg.strength}/10 | {fvg.created_bars_ago} bars ago"
            )
    else:
        lines.append("  No active FVGs")

    lines.append("")
    lines.append("=== ORDER BLOCKS ===")
    if bundle.active_order_blocks:
        for ob in bundle.active_order_blocks[:3]:
            lines.append(
                f"  OB {ob.ob_type.value.upper()}: {ob.zone_lower:.5f}-{ob.zone_upper:.5f} | "
                f"Mid: {ob.zone_mid:.5f} | Tested: {ob.has_been_tested} | "
                f"Valid: {ob.still_valid} | {ob.created_bars_ago} bars ago"
            )
    else:
        lines.append("  No active order blocks")

    lines.append("")
    lines.append("=== LIQUIDITY ===")
    if bundle.buy_side_liquidity_above:
        lines.append(f"Buy-side liquidity (above): {bundle.buy_side_liquidity_above:.5f}")
    if bundle.sell_side_liquidity_below:
        lines.append(f"Sell-side liquidity (below): {bundle.sell_side_liquidity_below:.5f}")
    if bundle.recent_liquidity_sweep:
        sw = bundle.recent_liquidity_sweep
        lines.append(
            f"LIQUIDITY SWEEP: {sw.liquidity_type.value} | Level: {sw.swept_level:.5f} | "
            f"{sw.swept_bars_ago} bars ago | Reversal confirmed: {sw.reversal_confirmed}"
        )

    lines.append("")
    lines.append("=== ZONES ===")
    if bundle.equilibrium_price:
        lines.append(f"Equilibrium (50% of range): {bundle.equilibrium_price:.5f}")
    lines.append(
        f"Price in: {'PREMIUM (institutional selling zone)' if bundle.in_premium_zone else 'DISCOUNT (institutional buying zone)' if bundle.in_discount_zone else 'EQUILIBRIUM'}"
    )

    if bundle.htf_structure:
        lines.append("")
        lines.append(f"Higher TF Structure: {bundle.htf_structure.value.upper()}")

    return "\n".join(lines)
