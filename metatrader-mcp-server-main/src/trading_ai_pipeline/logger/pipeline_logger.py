"""
Pipeline Logger.

Structured JSON logging for every pipeline step.
Logs agent prompts, responses, decisions, and trade outcomes.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from trading_ai_pipeline.core.types.agent_outputs import (
    TechnicalAnalysisOutput,
    PriceActionOutput,
    SmartMoneyOutput,
    ConsensusOutput,
    ReviewerOutput,
    ProbabilityOutput,
    RiskOutput,
    ValidatorOutput,
    TradeDirection,
)


class StructuredFormatter(logging.Formatter):
    """Formats log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if hasattr(record, "data"):
            payload["data"] = record.data  # type: ignore[attr-defined]
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def _setup_file_handler(
    log_dir: str,
    max_bytes: int,
    backup_count: int,
) -> logging.Handler:
    path = Path(log_dir)
    path.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        path / "pipeline.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(StructuredFormatter())
    return handler


class PipelineLogger:
    """
    Central logger for the entire pipeline.
    Call once at startup, then pass the instance through the pipeline.
    """

    def __init__(
        self,
        log_dir: str = "logs",
        level: str = "INFO",
        max_file_size_mb: int = 50,
        backup_count: int = 7,
        log_agent_prompts: bool = True,
        log_agent_responses: bool = True,
        console_output: bool = True,
    ) -> None:
        self.log_agent_prompts = log_agent_prompts
        self.log_agent_responses = log_agent_responses

        self._logger = logging.getLogger("trading_pipeline")
        self._logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self._logger.handlers.clear()

        # File handler
        self._logger.addHandler(
            _setup_file_handler(
                log_dir,
                max_bytes=max_file_size_mb * 1024 * 1024,
                backup_count=backup_count,
            )
        )

        # Console handler
        if console_output:
            console = logging.StreamHandler()
            console.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S",
                )
            )
            self._logger.addHandler(console)

    # ------------------------------------------------------------------
    # Pipeline-level events
    # ------------------------------------------------------------------

    def pipeline_start(self, symbol: str, timeframe: str, run_id: str) -> None:
        self._log("INFO", "Pipeline started", {
            "run_id": run_id, "symbol": symbol, "timeframe": timeframe
        })

    def pipeline_end(
        self,
        run_id: str,
        direction: TradeDirection,
        executed: bool,
        duration_ms: int,
    ) -> None:
        self._log("INFO", "Pipeline completed", {
            "run_id": run_id,
            "direction": direction.value,
            "executed": executed,
            "duration_ms": duration_ms,
        })

    def pipeline_error(self, run_id: str, step: str, error: str) -> None:
        self._log("ERROR", f"Pipeline error at step: {step}", {
            "run_id": run_id, "step": step, "error": error
        })

    # ------------------------------------------------------------------
    # Step-specific loggers
    # ------------------------------------------------------------------

    def log_agent_prompt(self, agent: str, prompt: str, run_id: str) -> None:
        if self.log_agent_prompts:
            self._log("DEBUG", f"Agent prompt: {agent}", {
                "run_id": run_id, "agent": agent, "prompt": prompt
            })

    def log_agent_response(self, agent: str, response: str, run_id: str) -> None:
        if self.log_agent_responses:
            self._log("DEBUG", f"Agent response: {agent}", {
                "run_id": run_id, "agent": agent, "response_preview": response[:200]
            })

    def log_technical(self, output: TechnicalAnalysisOutput, run_id: str) -> None:
        self._log("INFO", "Technical analysis complete", {
            "run_id": run_id,
            "direction": output.trend_direction.value,
            "confidence": output.confidence,
            "rsi": output.rsi_value,
            "ema_status": output.ema_alignment,
            "macd_signal": output.macd_signal,
            "adx": output.adx_value,
        })

    def log_price_action(self, output: PriceActionOutput, run_id: str) -> None:
        self._log("INFO", "Price action analysis complete", {
            "run_id": run_id,
            "bias": output.bias.value,
            "confidence": output.confidence,
            "pattern": output.primary_pattern,
            "key_level_type": output.key_level_type,
        })

    def log_smart_money(self, output: SmartMoneyOutput, run_id: str) -> None:
        self._log("INFO", "Smart money analysis complete", {
            "run_id": run_id,
            "bias": output.market_bias.value,
            "confidence": output.confidence,
            "bos": output.bos_detected,
            "choch": output.choch_detected,
            "fvg": output.fvg_detected,
            "liquidity_sweep": output.liquidity_sweep,
        })

    def log_consensus(self, output: ConsensusOutput, run_id: str) -> None:
        self._log("INFO", "Consensus built", {
            "run_id": run_id,
            "direction": output.direction.value,
            "confidence": output.confidence,
            "signal_strength": output.signal_strength.value,
            "agreement": f"{output.agreement_count}/{output.total_agents}",
            "conflicts": output.conflicts,
            "proceed": output.proceed,
        })

    def log_reviewer(self, output: ReviewerOutput, run_id: str) -> None:
        level = "WARNING" if output.veto else "INFO"
        self._log(level, "Reviewer assessment complete", {
            "run_id": run_id,
            "veto": output.veto,
            "veto_reason": output.veto_reason,
            "concerns": output.concerns,
            "spread_concern": output.spread_concern,
            "news_concern": output.news_concern,
        })

    def log_probability(self, output: ProbabilityOutput, run_id: str) -> None:
        self._log("INFO", "Probability estimated", {
            "run_id": run_id,
            "buy": output.buy_probability,
            "sell": output.sell_probability,
            "no_trade": output.no_trade_probability,
            "recommended": output.recommended_direction.value,
            "final_confidence": output.final_confidence,
            "adjustments": output.adjustments,
        })

    def log_risk(self, output: RiskOutput, run_id: str) -> None:
        level = "WARNING" if not output.approved else "INFO"
        self._log(level, "Risk calculation complete", {
            "run_id": run_id,
            "approved": output.approved,
            "sl": output.stop_loss,
            "tp": output.take_profit,
            "lots": output.position_size_lots,
            "rr": output.rr_ratio,
            "risk_pct": output.risk_percent,
            "spread_points": output.spread_points,
            "rejection": output.rejection_reason,
        })

    def log_validator(self, output: ValidatorOutput, run_id: str) -> None:
        level = "WARNING" if not output.approved else "INFO"
        self._log(level, "Validation complete", {
            "run_id": run_id,
            "approved": output.approved,
            "passed": output.passed_rules,
            "violations": output.violations,
        })

    def log_trade_executed(
        self,
        ticket: int,
        symbol: str,
        direction: TradeDirection,
        lots: float,
        entry: float,
        sl: float,
        tp: float,
        run_id: str,
    ) -> None:
        self._log("INFO", "Trade executed", {
            "run_id": run_id,
            "ticket": ticket,
            "symbol": symbol,
            "direction": direction.value,
            "lots": lots,
            "entry": entry,
            "sl": sl,
            "tp": tp,
        })

    def log_trade_skipped(self, reason: str, run_id: str) -> None:
        self._log("INFO", f"Trade skipped: {reason}", {
            "run_id": run_id, "reason": reason
        })

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _log(
        self,
        level: str,
        message: str,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        record = self._logger.makeRecord(
            self._logger.name,
            getattr(logging, level),
            fn="pipeline_logger",
            lno=0,
            msg=message,
            args=(),
            exc_info=None,
        )
        if data:
            record.data = data  # type: ignore[attr-defined]
        self._logger.handle(record)
