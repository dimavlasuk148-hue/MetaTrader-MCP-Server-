"""
Trade Executor — Step 10 of the pipeline.

Sends the validated order to MetaTrader 5 via the existing MCP client.
Operates in dry-run mode by default (no real orders placed).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from trading_ai_pipeline.core.types.agent_outputs import (
    RiskOutput,
    ValidatorOutput,
    TradeDirection,
)
from trading_ai_pipeline.core.types.market_data import SymbolInfo


@dataclass
class ExecutionResult:
    success: bool
    dry_run: bool
    ticket: Optional[int] = None
    entry_price: Optional[float] = None
    error: Optional[str] = None
    order_type: Optional[str] = None
    lots: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None


class TradeExecutor:
    """
    Wraps the MetaTrader 5 order submission.
    Uses the existing metatrader_client infrastructure.
    """

    def __init__(
        self,
        mt5_client,   # metatrader_client.MetaTraderClient instance
        dry_run: bool = True,
    ) -> None:
        self.mt5_client = mt5_client
        self.dry_run = dry_run

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(
        self,
        direction: TradeDirection,
        risk: RiskOutput,
        validator: ValidatorOutput,
        symbol: str,
        comment: str = "TradingAI",
    ) -> ExecutionResult:
        if not validator.approved:
            return ExecutionResult(
                success=False,
                dry_run=self.dry_run,
                error=f"Validator rejected: {validator.rejection_reason}",
            )

        if not risk.approved:
            return ExecutionResult(
                success=False,
                dry_run=self.dry_run,
                error=f"Risk rejected: {risk.rejection_reason}",
            )

        if direction == TradeDirection.NO_TRADE:
            return ExecutionResult(
                success=False,
                dry_run=self.dry_run,
                error="Direction is NO_TRADE — nothing to execute",
            )

        order_type = "BUY" if direction == TradeDirection.BUY else "SELL"

        if self.dry_run:
            return ExecutionResult(
                success=True,
                dry_run=True,
                ticket=999999,              # Simulated ticket
                entry_price=risk.entry_price,
                order_type=order_type,
                lots=risk.position_size_lots,
                sl=risk.stop_loss,
                tp=risk.take_profit,
            )

        # Live execution via MT5 client
        try:
            result = await self._place_order(
                symbol=symbol,
                order_type=order_type,
                lots=risk.position_size_lots,
                sl=risk.stop_loss,
                tp=risk.take_profit,
                comment=comment,
            )
            return result
        except Exception as exc:
            return ExecutionResult(
                success=False,
                dry_run=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # MT5 order submission
    # ------------------------------------------------------------------

    async def _place_order(
        self,
        symbol: str,
        order_type: str,
        lots: float,
        sl: Optional[float],
        tp: Optional[float],
        comment: str,
    ) -> ExecutionResult:
        """
        Calls the existing metatrader_client order API.
        Maps to client_order.py send_order() interface.
        """
        # The existing client uses synchronous MT5 SDK calls
        # We wrap them here for consistency with the async pipeline
        import asyncio
        loop = asyncio.get_event_loop()

        result = await loop.run_in_executor(
            None,
            lambda: self.mt5_client.send_order(
                symbol=symbol,
                order_type=order_type,
                volume=lots,
                sl=sl,
                tp=tp,
                comment=comment,
            )
        )

        if result and hasattr(result, "order") and result.order:
            return ExecutionResult(
                success=True,
                dry_run=False,
                ticket=result.order,
                entry_price=getattr(result, "price", None),
                order_type=order_type,
                lots=lots,
                sl=sl,
                tp=tp,
            )

        error_msg = getattr(result, "comment", "Unknown MT5 error")
        return ExecutionResult(
            success=False,
            dry_run=False,
            error=error_msg,
        )
