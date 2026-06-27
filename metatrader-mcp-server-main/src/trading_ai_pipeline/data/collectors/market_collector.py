"""
Market Data Collector — Step 1 of the pipeline.

Fetches raw OHLCV data, symbol info, and current prices from MT5.
Builds the MarketSnapshot. No indicators here — pure data collection.
"""

import logging
from datetime import datetime
from typing import Optional

from ...core.types.market_data import (
    Candle,
    OHLCV,
    SymbolInfo,
    MarketSnapshot,
    Timeframe,
)

logger = logging.getLogger("MarketCollector")

# Map of timeframe string → count of candles for higher/lower TF context
_HIGHER_TF_MAP: dict[Timeframe, Optional[Timeframe]] = {
    Timeframe.M1: Timeframe.M15,
    Timeframe.M5: Timeframe.H1,
    Timeframe.M15: Timeframe.H4,
    Timeframe.M30: Timeframe.H4,
    Timeframe.H1: Timeframe.D1,
    Timeframe.H4: Timeframe.W1,
    Timeframe.D1: Timeframe.W1,
    Timeframe.W1: None,
    Timeframe.MN1: None,
}

_LOWER_TF_MAP: dict[Timeframe, Optional[Timeframe]] = {
    Timeframe.M1: None,
    Timeframe.M5: Timeframe.M1,
    Timeframe.M15: Timeframe.M5,
    Timeframe.M30: Timeframe.M15,
    Timeframe.H1: Timeframe.M15,
    Timeframe.H4: Timeframe.H1,
    Timeframe.D1: Timeframe.H4,
    Timeframe.W1: Timeframe.D1,
    Timeframe.MN1: Timeframe.W1,
}


def _mt5_tf_string(tf: Timeframe) -> str:
    """Convert Timeframe enum to MT5 timeframe string."""
    return tf.value


def _parse_candles(df) -> list[Candle]:
    """Convert MT5 DataFrame to list of Candle objects."""
    candles = []
    for _, row in df.iterrows():
        try:
            time_val = row["time"]
            if hasattr(time_val, "to_pydatetime"):
                time_val = time_val.to_pydatetime()
            candles.append(
                Candle(
                    time=time_val,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("tick_volume", row.get("volume", 0))),
                    spread=float(row.get("spread", 0)) if "spread" in row else None,
                )
            )
        except Exception as e:
            logger.warning(f"Skipping malformed candle row: {e}")
    return candles


def _fetch_ohlcv(mt5_client, symbol: str, timeframe: Timeframe, count: int) -> Optional[OHLCV]:
    """Fetch OHLCV data from MT5 and return OHLCV model."""
    try:
        tf_str = _mt5_tf_string(timeframe)
        df = mt5_client.market.get_candles_latest(symbol, tf_str, count)
        if df is None or df.empty:
            logger.warning(f"No candles returned for {symbol} {tf_str}")
            return None
        candles = _parse_candles(df)
        return OHLCV(symbol=symbol, timeframe=timeframe, candles=candles)
    except Exception as e:
        logger.error(f"Error fetching OHLCV {symbol} {timeframe}: {e}")
        return None


def _fetch_symbol_info(mt5_client, symbol: str) -> Optional[SymbolInfo]:
    """Fetch symbol metadata from MT5."""
    try:
        info = mt5_client.market.get_symbol_info(symbol)
        if not info:
            return None
        return SymbolInfo(
            name=info.get("name", symbol),
            description=info.get("description", ""),
            currency_base=info.get("currency_base", ""),
            currency_profit=info.get("currency_profit", ""),
            digits=int(info.get("digits", 5)),
            point=float(info.get("point", 0.00001)),
            spread=float(info.get("spread", 0)),
            spread_float=bool(info.get("spread_float", True)),
            trade_contract_size=float(info.get("trade_contract_size", 100000)),
            volume_min=float(info.get("volume_min", 0.01)),
            volume_max=float(info.get("volume_max", 100.0)),
            volume_step=float(info.get("volume_step", 0.01)),
            trade_allowed=bool(info.get("trade_mode", 0) != 0),
        )
    except Exception as e:
        logger.error(f"Error fetching symbol info for {symbol}: {e}")
        return None


def collect_market_snapshot(
    mt5_client,
    symbol: str,
    timeframe: Timeframe,
    candle_count: int = 300,
    include_lower_tf: bool = True,
    include_higher_tf: bool = True,
) -> Optional[MarketSnapshot]:
    """
    Collect a complete MarketSnapshot for a symbol.

    Args:
        mt5_client:       MT5Client instance (connected).
        symbol:           Trading symbol, e.g. "EURUSD".
        timeframe:        Primary analysis timeframe.
        candle_count:     Number of candles for primary TF.
        include_lower_tf: Also fetch lower timeframe data.
        include_higher_tf: Also fetch higher timeframe data.

    Returns:
        MarketSnapshot or None if data collection failed.
    """
    logger.info(f"Collecting market snapshot: {symbol} {timeframe.value}")

    # Symbol info
    symbol_info = _fetch_symbol_info(mt5_client, symbol)
    if symbol_info is None:
        logger.error(f"Could not fetch symbol info for {symbol}")
        return None

    # Primary OHLCV
    ohlcv_primary = _fetch_ohlcv(mt5_client, symbol, timeframe, candle_count)
    if ohlcv_primary is None or ohlcv_primary.count < 50:
        logger.error(f"Insufficient candle data for {symbol} {timeframe.value}")
        return None

    # Higher TF (for context)
    ohlcv_higher: Optional[OHLCV] = None
    if include_higher_tf:
        higher_tf = _HIGHER_TF_MAP.get(timeframe)
        if higher_tf:
            ohlcv_higher = _fetch_ohlcv(mt5_client, symbol, higher_tf, 100)

    # Lower TF (for precision entry)
    ohlcv_lower: Optional[OHLCV] = None
    if include_lower_tf:
        lower_tf = _LOWER_TF_MAP.get(timeframe)
        if lower_tf:
            ohlcv_lower = _fetch_ohlcv(mt5_client, symbol, lower_tf, 100)

    # Current price
    bid = 0.0
    ask = 0.0
    try:
        price_data = mt5_client.market.get_symbol_price(symbol)
        if price_data:
            bid = float(price_data.get("bid", 0))
            ask = float(price_data.get("ask", 0))
    except Exception as e:
        logger.warning(f"Could not fetch live price for {symbol}: {e}")

    snapshot = MarketSnapshot(
        symbol=symbol,
        primary_timeframe=timeframe,
        symbol_info=symbol_info,
        ohlcv_primary=ohlcv_primary,
        ohlcv_higher=ohlcv_higher,
        ohlcv_lower=ohlcv_lower,
        current_bid=bid,
        current_ask=ask,
        collected_at=datetime.utcnow(),
    )

    logger.info(
        f"Snapshot collected: {symbol} {timeframe.value} "
        f"| {ohlcv_primary.count} candles "
        f"| bid={bid:.5f} ask={ask:.5f}"
    )
    return snapshot
