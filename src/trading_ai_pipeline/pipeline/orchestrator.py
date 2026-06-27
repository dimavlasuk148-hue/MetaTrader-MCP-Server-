"""
Pipeline Orchestrator.

Runs all 11 steps in sequence for a single analysis cycle.
Wires together every component: data collection, AI agents,
consensus, review, probability, risk, validation, and execution.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from trading_ai_pipeline.core.config.settings import PipelineConfig
from trading_ai_pipeline.core.types.agent_outputs import TradeDirection
from trading_ai_pipeline.core.types.pipeline_context import PipelineContext, PipelineStatus
from trading_ai_pipeline.data.collectors.market_collector import MarketDataCollector
from trading_ai_pipeline.data.indicators.calculator import IndicatorCalculator
from trading_ai_pipeline.data.indicators.price_action_detector import PriceActionDetector
from trading_ai_pipeline.data.indicators.smc_detector import SMCDetector
from trading_ai_pipeline.agents.technical.technical_agent import TechnicalAgent
from trading_ai_pipeline.agents.price_action.price_action_agent import PriceActionAgent
from trading_ai_pipeline.agents.smart_money.smart_money_agent import SmartMoneyAgent
from trading_ai_pipeline.agents.base.reviewer_agent import ReviewerAgent
from trading_ai_pipeline.pipeline.steps.consensus_builder import ConsensusBuilder
from trading_ai_pipeline.pipeline.steps.probability_estimator import ProbabilityEstimator
from trading_ai_pipeline.pipeline.steps.rule_validator import RuleValidator, ValidationContext
from trading_ai_pipeline.risk.risk_manager import RiskManager, RiskParams
from trading_ai_pipeline.executor.trade_executor import TradeExecutor
from trading_ai_pipeline.logger.pipeline_logger import PipelineLogger
from trading_ai_pipeline.memory.trade_memory import TradeMemory, TradeRecord


class PipelineOrchestrator:
    """
    Coordinates a single full pipeline run:
    Steps 1-11 from market data collection to trade execution.
    """

    def __init__(
        self,
        config: PipelineConfig,
        mt5_client,
        logger: Optional[PipelineLogger] = None,
        memory: Optional[TradeMemory] = None,
    ) -> None:
        self.config = config

        # Infrastructure
        self.logger = logger or PipelineLogger(
            log_dir=config.logging.log_dir,
            level=config.logging.level,
            max_file_size_mb=config.logging.max_file_size_mb,
            backup_count=config.logging.backup_count,
            log_agent_prompts=config.logging.log_agent_prompts,
            log_agent_responses=config.logging.log_agent_responses,
        )
        self.memory = memory or TradeMemory(
            storage_path=config.memory.storage_path,
            max_entries=config.memory.max_history_entries,
        )

        # Step 1 — Data collection
        self.collector = MarketDataCollector(mt5_client)

        # Steps 2-4 — Python indicator calculators (no AI)
        self.indicator_calc = IndicatorCalculator()
        self.pa_detector = PriceActionDetector()
        self.smc_detector = SMCDetector()

        # AI provider config
        ai_cfg = {
            "provider": config.ai.provider,
            "model": config.ai.model,
            "base_url": config.ai.base_url,
            "api_key": config.ai.api_key,
            "temperature": config.ai.temperature,
            "max_tokens": config.ai.max_tokens,
            "timeout": config.ai.timeout_seconds,
            "retry_attempts": config.ai.retry_attempts,
        }

        # Steps 2-4 — AI agents (interpret pre-calculated data)
        self.technical_agent = TechnicalAgent(ai_cfg, self.logger)
        self.price_action_agent = PriceActionAgent(ai_cfg, self.logger)
        self.smart_money_agent = SmartMoneyAgent(ai_cfg, self.logger)

        # Step 6 — Reviewer
        self.reviewer = ReviewerAgent(ai_cfg, self.logger)

        # Steps 5, 7, 8, 9 — Deterministic pipeline steps
        self.consensus_builder = ConsensusBuilder(
            min_confidence=config.consensus.min_confidence,
            min_agreement=config.consensus.min_agent_agreement,
            weights={
                "technical": config.consensus.technical_weight,
                "price_action": config.consensus.price_action_weight,
                "smart_money": config.consensus.smart_money_weight,
            },
        )
        self.probability_estimator = ProbabilityEstimator()
        self.risk_manager = RiskManager(
            RiskParams(
                risk_percent=config.risk.risk_percent,
                max_spread_points=config.risk.max_spread_points,
                min_rr_ratio=config.risk.min_rr_ratio,
                atr_sl_multiplier=config.risk.atr_sl_multiplier,
                atr_tp_multiplier=config.risk.atr_tp_multiplier,
                max_lots=config.risk.max_lots,
                min_lots=config.risk.min_lots,
            )
        )
        self.rule_validator = RuleValidator()

        # Step 10 — Executor
        self.executor = TradeExecutor(mt5_client, dry_run=config.dry_run)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def run(
        self,
        daily_trade_count: int = 0,
        daily_loss: float = 0.0,
        news_blackout_active: bool = False,
    ) -> PipelineContext:
        run_id = str(uuid.uuid4())[:8]
        symbol = self.config.symbol.symbol
        timeframe = self.config.symbol.timeframe
        start_ms = int(time.monotonic() * 1000)

        ctx = PipelineContext(
            pipeline_id=run_id,
            symbol=symbol,
            timeframe=timeframe,
            started_at=datetime.now(timezone.utc).isoformat(),
            status=PipelineStatus.RUNNING,
            dry_run=self.config.dry_run,
        )

        self.logger.pipeline_start(symbol, timeframe, run_id)

        try:
            # ----------------------------------------------------------
            # STEP 1: Collect market data
            # ----------------------------------------------------------
            market_data = await self.collector.collect(
                symbol=symbol,
                timeframe=timeframe,
                bars=self.config.symbol.bars_required,
                secondary_timeframe=self.config.symbol.secondary_timeframe,
            )
            ctx.market_data = market_data

            # ----------------------------------------------------------
            # STEP 2: Calculate indicators (Python only, no AI)
            # ----------------------------------------------------------
            indicators = self.indicator_calc.calculate(market_data.ohlcv)
            pa_data = self.pa_detector.detect(market_data.ohlcv)
            smc_data = self.smc_detector.detect(market_data.ohlcv)
            ctx.indicators = indicators
            ctx.price_action_data = pa_data
            ctx.smc_data = smc_data

            # Retrieve memory context for AI agents
            memory_summary = self.memory.summary_for_agent(symbol)

            # ----------------------------------------------------------
            # STEPS 3-4: Run all three AI agents in parallel
            # ----------------------------------------------------------
            technical_out, pa_out, smc_out = await asyncio.gather(
                self.technical_agent.analyze(
                    market_data, indicators, memory_summary, run_id
                ),
                self.price_action_agent.analyze(
                    market_data, pa_data, indicators, memory_summary, run_id
                ),
                self.smart_money_agent.analyze(
                    market_data, smc_data, indicators, memory_summary, run_id
                ),
            )

            ctx.technical_output = technical_out
            ctx.price_action_output = pa_out
            ctx.smart_money_output = smc_out

            self.logger.log_technical(technical_out, run_id)
            self.logger.log_price_action(pa_out, run_id)
            self.logger.log_smart_money(smc_out, run_id)

            # ----------------------------------------------------------
            # STEP 5: Build consensus
            # ----------------------------------------------------------
            consensus = self.consensus_builder.build(technical_out, pa_out, smc_out)
            ctx.consensus = consensus
            self.logger.log_consensus(consensus, run_id)

            if not consensus.proceed:
                return self._finish_no_trade(
                    ctx, run_id, start_ms,
                    consensus.rejection_reason or "Consensus failed"
                )

            # ----------------------------------------------------------
            # STEP 6: Reviewer (devil's advocate)
            # ----------------------------------------------------------
            reviewer_out = await self.reviewer.review(
                consensus=consensus,
                technical=technical_out,
                price_action=pa_out,
                smart_money=smc_out,
                market_data=market_data,
                run_id=run_id,
            )
            ctx.reviewer_output = reviewer_out
            self.logger.log_reviewer(reviewer_out, run_id)

            # ----------------------------------------------------------
            # STEP 7: Estimate probability
            # ----------------------------------------------------------
            probability = self.probability_estimator.estimate(consensus, reviewer_out)
            ctx.probability = probability
            self.logger.log_probability(probability, run_id)

            if not probability.proceed:
                return self._finish_no_trade(
                    ctx, run_id, start_ms,
                    f"Probability below threshold "
                    f"(confidence: {probability.final_confidence:.2%})"
                )

            # ----------------------------------------------------------
            # STEP 8: Risk calculation
            # ----------------------------------------------------------
            account = await self._get_account()
            symbol_info = market_data.symbol_info
            entry_price = market_data.current_price

            risk = self.risk_manager.calculate(
                direction=probability.recommended_direction,
                probability=probability,
                indicators=indicators,
                symbol_info=symbol_info,
                account=account,
                entry_price=entry_price,
            )
            ctx.risk_output = risk
            self.logger.log_risk(risk, run_id)

            # ----------------------------------------------------------
            # STEP 9: Rule validation
            # ----------------------------------------------------------
            open_positions = await self._get_open_positions()
            validation_ctx = ValidationContext(
                direction=probability.recommended_direction,
                risk=risk,
                probability=probability,
                account=account,
                open_positions=open_positions,
                symbol=symbol,
                daily_trade_count=daily_trade_count,
                daily_loss=daily_loss,
                news_blackout_active=news_blackout_active,
            )
            validator_out = self.rule_validator.validate(validation_ctx)
            ctx.validator_output = validator_out
            self.logger.log_validator(validator_out, run_id)

            if not validator_out.approved:
                return self._finish_no_trade(
                    ctx, run_id, start_ms, validator_out.rejection_reason or "Validation failed"
                )

            # ----------------------------------------------------------
            # STEP 10: Execute trade
            # ----------------------------------------------------------
            execution = await self.executor.execute(
                direction=probability.recommended_direction,
                risk=risk,
                validator=validator_out,
                symbol=symbol,
                comment=f"AI_{run_id}",
            )
            ctx.execution_result = execution

            if execution.success:
                self.logger.log_trade_executed(
                    ticket=execution.ticket,
                    symbol=symbol,
                    direction=probability.recommended_direction,
                    lots=execution.lots,
                    entry=execution.entry_price,
                    sl=execution.sl,
                    tp=execution.tp,
                    run_id=run_id,
                )
                ctx.status = PipelineStatus.TRADE_EXECUTED
            else:
                self.logger.log_trade_skipped(
                    f"Execution failed: {execution.error}", run_id
                )
                ctx.status = PipelineStatus.NO_TRADE
                ctx.rejection_reason = execution.error

            # ----------------------------------------------------------
            # STEP 11: Record to memory
            # ----------------------------------------------------------
            self._record_to_memory(ctx, run_id)

        except Exception as exc:
            step = getattr(ctx, "_current_step", "unknown")
            self.logger.pipeline_error(run_id, step, str(exc))
            ctx.status = PipelineStatus.ERROR
            ctx.error = str(exc)

        finally:
            elapsed = int(time.monotonic() * 1000) - start_ms
            ctx.duration_ms = elapsed
            ctx.finished_at = datetime.now(timezone.utc).isoformat()
            self.logger.pipeline_end(
                run_id=run_id,
                direction=self._ctx_direction(ctx),
                executed=ctx.status == PipelineStatus.TRADE_EXECUTED,
                duration_ms=elapsed,
            )

        return ctx

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _finish_no_trade(
        self,
        ctx: PipelineContext,
        run_id: str,
        start_ms: int,
        reason: str,
    ) -> PipelineContext:
        ctx.status = PipelineStatus.NO_TRADE
        ctx.rejection_reason = reason
        self.logger.log_trade_skipped(reason, run_id)
        self._record_to_memory(ctx, run_id)
        elapsed = int(time.monotonic() * 1000) - start_ms
        ctx.duration_ms = elapsed
        ctx.finished_at = datetime.now(timezone.utc).isoformat()
        self.logger.pipeline_end(
            run_id=run_id,
            direction=TradeDirection.NO_TRADE,
            executed=False,
            duration_ms=elapsed,
        )
        return ctx

    def _record_to_memory(self, ctx: PipelineContext, run_id: str) -> None:
        executed = ctx.status == PipelineStatus.TRADE_EXECUTED
        execution = getattr(ctx, "execution_result", None)
        probability = getattr(ctx, "probability", None)
        risk = getattr(ctx, "risk_output", None)
        technical = getattr(ctx, "technical_output", None)
        pa = getattr(ctx, "price_action_output", None)
        smc = getattr(ctx, "smart_money_output", None)
        consensus = getattr(ctx, "consensus", None)
        reviewer = getattr(ctx, "reviewer_output", None)
        direction = self._ctx_direction(ctx)

        record = TradeRecord(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=ctx.symbol,
            timeframe=ctx.timeframe,
            direction=direction.value,
            final_confidence=probability.final_confidence if probability else 0.0,
            executed=executed,
            ticket=execution.ticket if execution and executed else None,
            entry_price=risk.entry_price if risk else None,
            stop_loss=risk.stop_loss if risk else None,
            take_profit=risk.take_profit if risk else None,
            lots=risk.position_size_lots if risk else None,
            rr_ratio=risk.rr_ratio if risk else None,
            rejection_reason=ctx.rejection_reason,
            technical_direction=technical.trend_direction.value if technical else None,
            price_action_direction=pa.bias.value if pa else None,
            smart_money_direction=smc.market_bias.value if smc else None,
            consensus_confidence=consensus.confidence if consensus else None,
            reviewer_veto=reviewer.veto if reviewer else None,
            reviewer_concerns_count=len(reviewer.concerns) if reviewer else None,
        )
        self.memory.record(record)

    def _ctx_direction(self, ctx: PipelineContext) -> TradeDirection:
        if probability := getattr(ctx, "probability", None):
            return probability.recommended_direction
        return TradeDirection.NO_TRADE

    async def _get_account(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.executor.mt5_client.get_account_info()
        )

    async def _get_open_positions(self) -> list:
        loop = asyncio.get_event_loop()
        positions = await loop.run_in_executor(
            None, lambda: self.executor.mt5_client.get_positions()
        )
        return positions or []
