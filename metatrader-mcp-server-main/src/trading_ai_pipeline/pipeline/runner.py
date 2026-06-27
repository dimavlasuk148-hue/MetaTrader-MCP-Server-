"""
Pipeline Runner.

Long-running loop that triggers the orchestrator on a configurable interval.
Tracks daily state (trade count, daily loss) and resets at midnight UTC.
"""
from __future__ import annotations

import asyncio
import signal
from datetime import datetime, timezone, date
from typing import Optional

from trading_ai_pipeline.core.config.settings import PipelineConfig, load_config
from trading_ai_pipeline.core.types.pipeline_context import PipelineStatus
from trading_ai_pipeline.logger.pipeline_logger import PipelineLogger
from trading_ai_pipeline.memory.trade_memory import TradeMemory
from trading_ai_pipeline.pipeline.orchestrator import PipelineOrchestrator


class DailyState:
    """Resets at UTC midnight."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.date = date.today()
        self.trade_count: int = 0
        self.daily_loss: float = 0.0

    def check_reset(self) -> None:
        today = date.today()
        if today != self.date:
            self.reset()

    def record_trade(self) -> None:
        self.trade_count += 1

    def record_loss(self, amount: float) -> None:
        if amount < 0:
            self.daily_loss += abs(amount)


class PipelineRunner:
    """
    Manages the continuous pipeline loop.
    Handles graceful shutdown on SIGINT / SIGTERM.
    """

    def __init__(
        self,
        config: PipelineConfig,
        mt5_client,
        logger: Optional[PipelineLogger] = None,
        memory: Optional[TradeMemory] = None,
    ) -> None:
        self.config = config
        self.logger = logger or PipelineLogger(
            log_dir=config.logging.log_dir,
            level=config.logging.level,
        )
        self.memory = memory or TradeMemory(
            storage_path=config.memory.storage_path
        )
        self.orchestrator = PipelineOrchestrator(
            config=config,
            mt5_client=mt5_client,
            logger=self.logger,
            memory=self.memory,
        )
        self._running = False
        self._daily = DailyState()

    async def start(self) -> None:
        self._running = True
        self._register_signals()

        mode = "DRY-RUN" if self.config.dry_run else "LIVE"
        self.logger._log(
            "INFO",
            f"Pipeline runner started [{mode}]",
            {
                "symbol": self.config.symbol.symbol,
                "timeframe": self.config.symbol.timeframe,
                "interval_seconds": self.config.pipeline_interval_seconds,
                "ai_provider": self.config.ai.provider,
                "ai_model": self.config.ai.model,
            },
        )

        while self._running:
            self._daily.check_reset()

            ctx = await self.orchestrator.run(
                daily_trade_count=self._daily.trade_count,
                daily_loss=self._daily.daily_loss,
            )

            if ctx.status == PipelineStatus.TRADE_EXECUTED:
                self._daily.record_trade()

            await asyncio.sleep(self.config.pipeline_interval_seconds)

        self.logger._log("INFO", "Pipeline runner stopped", {})

    def stop(self) -> None:
        self._running = False

    def _register_signals(self) -> None:
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.stop)
            except (NotImplementedError, RuntimeError):
                pass  # Windows compatibility


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main(config_path: Optional[str] = None) -> None:
    config = load_config(config_path)

    # Import MT5 client from the existing package
    from metatrader_client import MetaTraderClient
    from metatrader_client.connection.config import ConnectionConfig

    connection_cfg = ConnectionConfig(
        host=config.mt5.host,
        port=config.mt5.port,
    )
    mt5_client = MetaTraderClient(connection_cfg)

    runner = PipelineRunner(config=config, mt5_client=mt5_client)
    await runner.start()


if __name__ == "__main__":
    import sys
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(cfg_path))
