"""
Risk Manager — Step 8 of the pipeline.

All calculations are deterministic Python. No AI involved.
Calculates position size, stop loss, take profit, and risk/reward ratio.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from trading_ai_pipeline.core.types.agent_outputs import (
    TradeDirection,
    ProbabilityOutput,
    RiskOutput,
)
from trading_ai_pipeline.core.types.indicators import IndicatorBundle
from trading_ai_pipeline.core.types.market_data import SymbolInfo, AccountInfo


# Default risk parameters (can be overridden via config)
DEFAULT_RISK_PERCENT = 1.0          # % of balance risked per trade
DEFAULT_MAX_SPREAD_POINTS = 20      # max allowed spread in points
DEFAULT_MIN_RR_RATIO = 1.5          # minimum risk/reward ratio
DEFAULT_ATR_SL_MULTIPLIER = 1.5     # stop loss = ATR * multiplier
DEFAULT_ATR_TP_MULTIPLIER = 2.5     # take profit = ATR * multiplier
MAX_POSITION_SIZE_LOTS = 10.0       # hard cap on lot size
MIN_POSITION_SIZE_LOTS = 0.01       # minimum broker lot size


@dataclass
class RiskParams:
    risk_percent: float = DEFAULT_RISK_PERCENT
    max_spread_points: int = DEFAULT_MAX_SPREAD_POINTS
    min_rr_ratio: float = DEFAULT_MIN_RR_RATIO
    atr_sl_multiplier: float = DEFAULT_ATR_SL_MULTIPLIER
    atr_tp_multiplier: float = DEFAULT_ATR_TP_MULTIPLIER
    max_lots: float = MAX_POSITION_SIZE_LOTS
    min_lots: float = MIN_POSITION_SIZE_LOTS


class RiskManager:
    """
    Deterministic risk calculator.
    Given account info, market data, and ATR — computes SL, TP, and lot size.
    """

    def __init__(self, params: Optional[RiskParams] = None) -> None:
        self.params = params or RiskParams()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate(
        self,
        direction: TradeDirection,
        probability: ProbabilityOutput,
        indicators: IndicatorBundle,
        symbol_info: SymbolInfo,
        account: AccountInfo,
        entry_price: float,
    ) -> RiskOutput:
        spread_points = self._get_spread_points(symbol_info)
        spread_ok = spread_points <= self.params.max_spread_points

        atr = indicators.atr
        if atr is None or atr <= 0:
            return RiskOutput(
                approved=False,
                rejection_reason="ATR not available — cannot calculate SL/TP",
                entry_price=entry_price,
                stop_loss=None,
                take_profit=None,
                position_size_lots=None,
                risk_amount=None,
                risk_percent=None,
                rr_ratio=None,
                spread_points=spread_points,
                spread_ok=spread_ok,
            )

        sl_distance = atr * self.params.atr_sl_multiplier
        tp_distance = atr * self.params.atr_tp_multiplier

        if direction == TradeDirection.BUY:
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        elif direction == TradeDirection.SELL:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
        else:
            return RiskOutput(
                approved=False,
                rejection_reason="Direction is NO_TRADE",
                entry_price=entry_price,
                stop_loss=None,
                take_profit=None,
                position_size_lots=None,
                risk_amount=None,
                risk_percent=None,
                rr_ratio=None,
                spread_points=spread_points,
                spread_ok=spread_ok,
            )

        rr_ratio = tp_distance / sl_distance if sl_distance > 0 else 0.0
        rr_ok = rr_ratio >= self.params.min_rr_ratio

        risk_amount = account.balance * (self.params.risk_percent / 100.0)
        position_size = self._calculate_position_size(
            risk_amount, sl_distance, symbol_info
        )
        position_size = self._clamp_position_size(position_size, symbol_info)

        rejection_reason = None
        approved = True

        if not spread_ok:
            approved = False
            rejection_reason = (
                f"Spread {spread_points} pts exceeds max "
                f"{self.params.max_spread_points} pts"
            )
        elif not rr_ok:
            approved = False
            rejection_reason = (
                f"R/R ratio {rr_ratio:.2f} below minimum {self.params.min_rr_ratio}"
            )
        elif position_size < self.params.min_lots:
            approved = False
            rejection_reason = (
                f"Calculated position size {position_size:.4f} "
                f"below minimum {self.params.min_lots}"
            )

        return RiskOutput(
            approved=approved,
            rejection_reason=rejection_reason,
            entry_price=round(entry_price, symbol_info.digits),
            stop_loss=round(stop_loss, symbol_info.digits),
            take_profit=round(take_profit, symbol_info.digits),
            position_size_lots=round(position_size, 2),
            risk_amount=round(risk_amount, 2),
            risk_percent=self.params.risk_percent,
            rr_ratio=round(rr_ratio, 2),
            spread_points=spread_points,
            spread_ok=spread_ok,
            sl_distance_atr=round(sl_distance / atr, 2),
            tp_distance_atr=round(tp_distance / atr, 2),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_spread_points(self, symbol_info: SymbolInfo) -> int:
        if symbol_info.spread is not None:
            return symbol_info.spread
        if symbol_info.ask and symbol_info.bid and symbol_info.point:
            raw_spread = (symbol_info.ask - symbol_info.bid) / symbol_info.point
            return int(round(raw_spread))
        return 0

    def _calculate_position_size(
        self,
        risk_amount: float,
        sl_distance: float,
        symbol_info: SymbolInfo,
    ) -> float:
        """
        Lot size = risk_amount / (sl_distance_in_price * value_per_lot)
        value_per_lot = contract_size * point_value
        """
        if symbol_info.point is None or symbol_info.point == 0:
            return self.params.min_lots

        # Standard calculation: 1 lot = contract_size units
        contract_size = getattr(symbol_info, "trade_contract_size", 100_000)
        if contract_size is None or contract_size == 0:
            contract_size = 100_000

        # Value per point per lot (in account currency)
        # Simplified: assumes quote currency == account currency
        value_per_point = contract_size * symbol_info.point
        if value_per_point == 0:
            return self.params.min_lots

        sl_points = sl_distance / symbol_info.point
        risk_per_lot = sl_points * value_per_point

        if risk_per_lot == 0:
            return self.params.min_lots

        return risk_amount / risk_per_lot

    def _clamp_position_size(
        self, size: float, symbol_info: SymbolInfo
    ) -> float:
        """Round to broker's lot step and enforce min/max."""
        lot_step = getattr(symbol_info, "volume_step", 0.01) or 0.01
        size = round(size / lot_step) * lot_step
        size = max(self.params.min_lots, min(self.params.max_lots, size))
        return size
