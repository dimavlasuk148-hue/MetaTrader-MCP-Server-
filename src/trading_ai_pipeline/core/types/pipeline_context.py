"""
Pipeline context — the single object that flows through all 11 steps.

Each step reads the context, does its work, and writes its output back.
This is the spine of the entire pipeline.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from .market_data import MarketSnapshot
from .indicators import IndicatorBundle
from .price_action import PriceActionBundle
from .smart_money import SmartMoneyBundle
from .agent_outputs import (
    TechnicalAnalysis,
    PriceActionAnalysis,
    SmartMoneyAnalysis,
    ConsensusResult,
    ReviewerVerdict,
    ProbabilityEstimate,
    RiskParameters,
    ValidationResult,
    TradeDecision,
)


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    TRADE_EXECUTED = "trade_executed"
    NO_TRADE = "no_trade"
    ABORTED = "aborted"
    ERROR = "error"


class StepLog(BaseModel):
    """Audit log entry for one pipeline step."""

    step_name: str
    step_index: int
    status: str = "pending"          # pending / running / done / skipped / error
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    model_used: Optional[str] = None  # which AI model if applicable
    tokens_used: Optional[int] = None
    error_message: Optional[str] = None
    notes: str = ""


class PipelineContext(BaseModel):
    """
    The complete state object that flows through all 11 pipeline steps.

    Steps only append / update their own section.
    No step should modify results from a previous step.
    """

    # Identity
    pipeline_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    symbol: str = ""
    timeframe: str = ""

    # Runtime metadata (set by the orchestrator/runner)
    dry_run: bool = True
    duration_ms: Optional[int] = None
    started_at: Optional[str] = None    # ISO string set at run start
    finished_at: Optional[str] = None   # ISO string set at run end

    # Pipeline state
    status: PipelineStatus = PipelineStatus.PENDING
    current_step: int = 0
    abort_reason: Optional[str] = None
    rejection_reason: Optional[str] = None  # NO_TRADE reason
    error: Optional[str] = None             # ERROR reason

    @property
    def run_id(self) -> str:
        """Alias for pipeline_id used by orchestrator and logger."""
        return self.pipeline_id

    # ── Step 1: Market Data ──────────────────────────────
    market_snapshot: Optional[MarketSnapshot] = None

    # ── Step 1b: Indicators (Python-only) ───────────────
    indicators: Optional[IndicatorBundle] = None
    price_action_data: Optional[PriceActionBundle] = None
    smart_money_data: Optional[SmartMoneyBundle] = None
    # Alias used by orchestrator
    smc_data: Optional[Any] = None

    # ── Step 2: Technical Analyst AI ────────────────────
    technical_analysis: Optional[TechnicalAnalysis] = None
    # Pipeline-native typed output (used by orchestrator)
    technical_output: Optional[Any] = None

    # ── Step 3: Price Action Analyst AI ─────────────────
    price_action_analysis: Optional[PriceActionAnalysis] = None
    price_action_output: Optional[Any] = None

    # ── Step 4: Smart Money Analyst AI ──────────────────
    smart_money_analysis: Optional[SmartMoneyAnalysis] = None
    smart_money_output: Optional[Any] = None

    # ── Step 5: Consensus Builder (deterministic) ───────
    consensus: Optional[Any] = None

    # ── Step 6: Reviewer AI ─────────────────────────────
    reviewer_verdict: Optional[ReviewerVerdict] = None
    reviewer_output: Optional[Any] = None

    # ── Step 7: Probability Estimator AI ────────────────
    probability: Optional[Any] = None

    # ── Step 8: Risk Manager (deterministic) ────────────
    risk_parameters: Optional[RiskParameters] = None
    risk_output: Optional[Any] = None

    # ── Step 9: Rule Validator (deterministic) ──────────
    validation: Optional[ValidationResult] = None
    validator_output: Optional[Any] = None

    # ── Step 10: Trade Decision ──────────────────────────
    trade_decision: Optional[TradeDecision] = None
    execution_result: Optional[Any] = None

    # ── Step 11: Execution Result ────────────────────────
    execution_ticket: Optional[int] = None
    execution_error: Optional[str] = None
    executed_at: Optional[datetime] = None

    # ── Step 1: Market data (orchestrator alias) ─────────
    market_data: Optional[Any] = None

    # ── Audit trail ──────────────────────────────────────
    step_logs: List[StepLog] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)

    def log_step_start(self, step_index: int, step_name: str, model: Optional[str] = None) -> None:
        entry = StepLog(
            step_name=step_name,
            step_index=step_index,
            status="running",
            started_at=datetime.utcnow(),
            model_used=model,
        )
        self.step_logs.append(entry)
        self.current_step = step_index

    def log_step_done(self, step_index: int, notes: str = "", tokens: Optional[int] = None) -> None:
        for log in reversed(self.step_logs):
            if log.step_index == step_index:
                log.status = "done"
                log.finished_at = datetime.utcnow()
                log.notes = notes
                log.tokens_used = tokens
                if log.started_at:
                    delta = (log.finished_at - log.started_at).total_seconds() * 1000
                    log.duration_ms = round(delta, 2)
                break

    def log_step_error(self, step_index: int, error: str) -> None:
        for log in reversed(self.step_logs):
            if log.step_index == step_index:
                log.status = "error"
                log.finished_at = datetime.utcnow()
                log.error_message = error
                break

    def abort(self, reason: str) -> None:
        self.status = PipelineStatus.ABORTED
        self.abort_reason = reason

    def to_summary(self) -> Dict[str, Any]:
        """Compact summary for logging / memory storage."""
        return {
            "pipeline_id": self.pipeline_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "steps_completed": len([s for s in self.step_logs if s.status == "done"]),
            "decision": self.trade_decision.direction if self.trade_decision else "none",
            "executed": self.execution_ticket is not None,
            "abort_reason": self.abort_reason,
        }
