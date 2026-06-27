"""
Indicator Calculator — pure Python / NumPy / Pandas.

This module calculates ALL technical indicators deterministically.
AI agents receive these results — they never calculate indicators themselves.
No AI calls here. This must be fast, testable, and reliable.
"""

import logging
from typing import List, Optional

import numpy as np

from ...core.types.market_data import OHLCV, Timeframe
from ...core.types.indicators import (
    ADXData,
    ATRData,
    BollingerBands,
    EMACrossSignal,
    IndicatorBundle,
    MACDSignal,
    RSISignal,
    SignalStrength,
    TrendDirection,
    VWAPData,
)

logger = logging.getLogger("IndicatorCalculator")


# ─────────────────────────────────────────────
# Low-level numpy helpers
# ─────────────────────────────────────────────

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average."""
    alpha = 2.0 / (period + 1)
    result = np.empty_like(series, dtype=float)
    result[:] = np.nan
    # Find first valid index
    start = period - 1
    if start >= len(series):
        return result
    result[start] = np.mean(series[:period])
    for i in range(start + 1, len(series)):
        result[i] = alpha * series[i] + (1 - alpha) * result[i - 1]
    return result


def _sma(series: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average."""
    result = np.full_like(series, np.nan, dtype=float)
    for i in range(period - 1, len(series)):
        result[i] = np.mean(series[i - period + 1 : i + 1])
    return result


def _true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """True Range calculation."""
    n = len(high)
    tr = np.empty(n, dtype=float)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
    return tr


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Average True Range."""
    tr = _true_range(high, low, close)
    return _ema(tr, period)


def _rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """RSI calculation."""
    if len(close) < period + 1:
        return np.full(len(close), np.nan)
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.full(len(close), np.nan)
    avg_loss = np.full(len(close), np.nan)

    avg_gain[period] = np.mean(gains[:period])
    avg_loss[period] = np.mean(losses[:period])

    for i in range(period + 1, len(close)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period

    rs = np.where(avg_loss == 0, np.inf, avg_gain / avg_loss)
    rsi = 100 - (100 / (1 + rs))
    rsi[:period] = np.nan
    return rsi


def _macd(
    close: np.ndarray,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """MACD line, signal line, histogram."""
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _bollinger(
    close: np.ndarray, period: int = 20, std_dev: float = 2.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Bollinger Bands: upper, middle (SMA), lower."""
    middle = _sma(close, period)
    std = np.array(
        [
            np.std(close[max(0, i - period + 1) : i + 1]) if i >= period - 1 else np.nan
            for i in range(len(close))
        ]
    )
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return upper, middle, lower


def _adx(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int = 14,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """ADX, +DI, -DI."""
    n = len(high)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)

    for i in range(1, n):
        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]
        plus_dm[i] = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm[i] = down_move if (down_move > up_move and down_move > 0) else 0.0

    tr = _true_range(high, low, close)
    smoothed_tr = _ema(tr, period)
    smoothed_plus = _ema(plus_dm, period)
    smoothed_minus = _ema(minus_dm, period)

    with np.errstate(divide="ignore", invalid="ignore"):
        plus_di = 100 * np.where(smoothed_tr != 0, smoothed_plus / smoothed_tr, 0.0)
        minus_di = 100 * np.where(smoothed_tr != 0, smoothed_minus / smoothed_tr, 0.0)
        dx = 100 * np.where(
            (plus_di + minus_di) != 0,
            np.abs(plus_di - minus_di) / (plus_di + minus_di),
            0.0,
        )

    adx = _ema(dx, period)
    return adx, plus_di, minus_di


# ─────────────────────────────────────────────
# Divergence detection helpers
# ─────────────────────────────────────────────

def _detect_divergence(
    close: np.ndarray, indicator: np.ndarray, lookback: int = 10
) -> tuple[bool, bool]:
    """
    Simple divergence detection on last `lookback` bars.
    Returns (bullish_divergence, bearish_divergence).
    """
    if len(close) < lookback or len(indicator) < lookback:
        return False, False

    c = close[-lookback:]
    ind = indicator[-lookback:]

    # Remove NaN
    valid = ~np.isnan(ind)
    if valid.sum() < 4:
        return False, False

    # Bullish: price makes lower low, indicator makes higher low
    bull = c[-1] < c[0] and ind[-1] > ind[0]
    # Bearish: price makes higher high, indicator makes lower high
    bear = c[-1] > c[0] and ind[-1] < ind[0]

    return bull, bear


# ─────────────────────────────────────────────
# VWAP calculation
# ─────────────────────────────────────────────

def _calc_vwap(ohlcv: OHLCV) -> Optional[VWAPData]:
    """Calculate VWAP with 1 and 2 standard deviation bands."""
    if ohlcv.count < 2:
        return None

    closes = np.array(ohlcv.closes())
    highs = np.array(ohlcv.highs())
    lows = np.array(ohlcv.lows())
    volumes = np.array(ohlcv.volumes())

    typical = (highs + lows + closes) / 3.0
    cumulative_tpv = np.cumsum(typical * volumes)
    cumulative_vol = np.cumsum(volumes)

    with np.errstate(divide="ignore", invalid="ignore"):
        vwap_arr = np.where(cumulative_vol > 0, cumulative_tpv / cumulative_vol, np.nan)

    vwap = float(vwap_arr[-1]) if not np.isnan(vwap_arr[-1]) else float(typical[-1])

    # Deviation bands
    variance = np.where(
        cumulative_vol > 0,
        np.cumsum(volumes * (typical - vwap) ** 2) / cumulative_vol,
        0.0,
    )
    std = float(np.sqrt(max(variance[-1], 0)))

    current = closes[-1]
    return VWAPData(
        vwap=vwap,
        dev_1_upper=vwap + std,
        dev_1_lower=vwap - std,
        dev_2_upper=vwap + 2 * std,
        dev_2_lower=vwap - 2 * std,
        price_above_vwap=current > vwap,
        distance_pips=abs(current - vwap),
    )


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def calculate_indicators(
    ohlcv: OHLCV,
    higher_tf_ohlcv: Optional[OHLCV] = None,
    ema_fast: int = 9,
    ema_slow: int = 21,
    ema_trend: int = 200,
) -> IndicatorBundle:
    """
    Calculate all technical indicators for a given OHLCV dataset.

    Args:
        ohlcv:            Primary timeframe OHLCV data.
        higher_tf_ohlcv:  Optional higher timeframe OHLCV for trend context.
        ema_fast:         Fast EMA period.
        ema_slow:         Slow EMA period.
        ema_trend:        Trend EMA period (200 by default).

    Returns:
        IndicatorBundle with all indicators filled in.
    """
    closes = np.array(ohlcv.closes())
    highs = np.array(ohlcv.highs())
    lows = np.array(ohlcv.lows())
    n = len(closes)

    bundle = IndicatorBundle(
        symbol=ohlcv.symbol,
        timeframe=ohlcv.timeframe.value,
        candles_used=n,
    )

    if n < 30:
        logger.warning(f"Too few candles ({n}) for reliable indicator calculation")
        return bundle

    # ── EMA ─────────────────────────────────────
    ema_fast_arr = _ema(closes, ema_fast)
    ema_slow_arr = _ema(closes, ema_slow)
    ema_200_arr = _ema(closes, ema_trend) if n >= ema_trend else np.full(n, np.nan)

    ema_fast_val = float(ema_fast_arr[-1]) if not np.isnan(ema_fast_arr[-1]) else 0.0
    ema_slow_val = float(ema_slow_arr[-1]) if not np.isnan(ema_slow_arr[-1]) else 0.0
    ema_200_val = float(ema_200_arr[-1]) if not np.isnan(ema_200_arr[-1]) else None

    # Detect crossover (last 3 bars)
    cross_bull = False
    cross_bear = False
    bars_since = None
    if n >= ema_slow + 3:
        for i in range(1, min(6, n)):
            prev_fast = ema_fast_arr[-(i + 1)]
            prev_slow = ema_slow_arr[-(i + 1)]
            cur_fast = ema_fast_arr[-i]
            cur_slow = ema_slow_arr[-i]
            if not any(np.isnan([prev_fast, prev_slow, cur_fast, cur_slow])):
                if prev_fast < prev_slow and cur_fast > cur_slow:
                    cross_bull = True
                    bars_since = i
                    break
                if prev_fast > prev_slow and cur_fast < cur_slow:
                    cross_bear = True
                    bars_since = i
                    break

    # Trend direction from EMA alignment
    if ema_fast_val > ema_slow_val:
        if ema_200_val and closes[-1] > ema_200_val:
            trend = TrendDirection.BULLISH
        else:
            trend = TrendDirection.BULLISH
    elif ema_fast_val < ema_slow_val:
        trend = TrendDirection.BEARISH
    else:
        trend = TrendDirection.SIDEWAYS

    bundle.ema = EMACrossSignal(
        ema_fast_period=ema_fast,
        ema_slow_period=ema_slow,
        ema_fast_value=ema_fast_val,
        ema_slow_value=ema_slow_val,
        ema_200_value=ema_200_val,
        price_above_ema200=(closes[-1] > ema_200_val) if ema_200_val else None,
        crossover_bullish=cross_bull,
        crossover_bearish=cross_bear,
        trend=trend,
        bars_since_cross=bars_since,
    )

    # ── MACD ────────────────────────────────────
    if n >= 35:
        macd_line, sig_line, histogram = _macd(closes)
        ml = float(macd_line[-1]) if not np.isnan(macd_line[-1]) else 0.0
        sl = float(sig_line[-1]) if not np.isnan(sig_line[-1]) else 0.0
        hist = float(histogram[-1]) if not np.isnan(histogram[-1]) else 0.0
        hist_prev = float(histogram[-2]) if n >= 2 and not np.isnan(histogram[-2]) else None

        bull_div, bear_div = _detect_divergence(closes, macd_line)

        bundle.macd = MACDSignal(
            macd_line=ml,
            signal_line=sl,
            histogram=hist,
            histogram_prev=hist_prev,
            above_zero=ml > 0,
            bullish_divergence=bull_div,
            bearish_divergence=bear_div,
            histogram_expanding=(hist_prev is not None and abs(hist) > abs(hist_prev)),
            histogram_shrinking=(hist_prev is not None and abs(hist) < abs(hist_prev)),
        )

    # ── RSI ─────────────────────────────────────
    if n >= 20:
        rsi_arr = _rsi(closes, 14)
        rsi_val = float(rsi_arr[-1]) if not np.isnan(rsi_arr[-1]) else 50.0
        bull_div_rsi, bear_div_rsi = _detect_divergence(closes, rsi_arr)

        bundle.rsi = RSISignal(
            period=14,
            value=rsi_val,
            is_overbought=rsi_val > 70,
            is_oversold=rsi_val < 30,
            is_neutral=30 <= rsi_val <= 70,
            bullish_divergence=bull_div_rsi,
            bearish_divergence=bear_div_rsi,
        )

    # ── ATR ─────────────────────────────────────
    atr_arr = _atr(highs, lows, closes, 14)
    atr_val = float(atr_arr[-1]) if not np.isnan(atr_arr[-1]) else 0.0

    avg_atr = float(np.nanmean(atr_arr[-50:])) if n >= 50 else atr_val
    if atr_val < avg_atr * 0.7:
        vol_label = "low"
    elif atr_val > avg_atr * 1.5:
        vol_label = "high"
    elif atr_val > avg_atr * 2.0:
        vol_label = "extreme"
    else:
        vol_label = "normal"

    bundle.atr = ATRData(
        period=14,
        value=atr_val,
        value_in_pips=atr_val,  # caller adjusts for point size
        volatility_label=vol_label,
    )

    # ── ADX ─────────────────────────────────────
    if n >= 30:
        adx_arr, plus_di_arr, minus_di_arr = _adx(highs, lows, closes, 14)
        adx_val = float(adx_arr[-1]) if not np.isnan(adx_arr[-1]) else 0.0
        pdi = float(plus_di_arr[-1]) if not np.isnan(plus_di_arr[-1]) else 0.0
        mdi = float(minus_di_arr[-1]) if not np.isnan(minus_di_arr[-1]) else 0.0

        if adx_val >= 40:
            strength = SignalStrength.STRONG
        elif adx_val >= 25:
            strength = SignalStrength.MODERATE
        elif adx_val >= 15:
            strength = SignalStrength.WEAK
        else:
            strength = SignalStrength.NEUTRAL

        bundle.adx = ADXData(
            period=14,
            adx_value=adx_val,
            plus_di=pdi,
            minus_di=mdi,
            trend_strength=strength,
            is_trending=adx_val >= 25,
            is_ranging=adx_val < 25,
        )

    # ── Bollinger Bands ──────────────────────────
    if n >= 25:
        bb_upper, bb_mid, bb_lower = _bollinger(closes, 20, 2.0)
        bbu = float(bb_upper[-1]) if not np.isnan(bb_upper[-1]) else closes[-1]
        bbm = float(bb_mid[-1]) if not np.isnan(bb_mid[-1]) else closes[-1]
        bbl = float(bb_lower[-1]) if not np.isnan(bb_lower[-1]) else closes[-1]

        bw = (bbu - bbl) / bbm if bbm != 0 else 0.0
        avg_bw = float(np.nanmean([(bb_upper[i] - bb_lower[i]) / bb_mid[i]
                                    for i in range(max(0, n - 50), n)
                                    if not np.isnan(bb_mid[i]) and bb_mid[i] != 0]))

        pos = (closes[-1] - bbl) / (bbu - bbl) if (bbu - bbl) > 0 else 0.5

        bundle.bollinger = BollingerBands(
            period=20,
            std_dev=2.0,
            upper=bbu,
            middle=bbm,
            lower=bbl,
            bandwidth=bw,
            price_position=pos,
            squeeze=bw < avg_bw * 0.75,
            breakout_up=closes[-1] > bbu,
            breakout_down=closes[-1] < bbl,
        )

    # ── VWAP ────────────────────────────────────
    bundle.vwap = _calc_vwap(ohlcv)

    # ── Higher TF context ───────────────────────
    if higher_tf_ohlcv and higher_tf_ohlcv.count >= 30:
        htf_closes = np.array(higher_tf_ohlcv.closes())
        htf_ema_fast = _ema(htf_closes, ema_fast)
        htf_ema_slow = _ema(htf_closes, ema_slow)

        if not any(np.isnan([htf_ema_fast[-1], htf_ema_slow[-1]])):
            if htf_ema_fast[-1] > htf_ema_slow[-1]:
                bundle.higher_tf_ema_trend = TrendDirection.BULLISH
            elif htf_ema_fast[-1] < htf_ema_slow[-1]:
                bundle.higher_tf_ema_trend = TrendDirection.BEARISH
            else:
                bundle.higher_tf_ema_trend = TrendDirection.SIDEWAYS

        htf_ema200 = _ema(htf_closes, ema_trend) if len(htf_closes) >= ema_trend else None
        if htf_ema200 is not None and not np.isnan(htf_ema200[-1]):
            bundle.higher_tf_trend = (
                TrendDirection.BULLISH if htf_closes[-1] > htf_ema200[-1]
                else TrendDirection.BEARISH
            )

    return bundle
