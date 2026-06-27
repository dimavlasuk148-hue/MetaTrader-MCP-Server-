"""
Rule Validator — Step 9 of the pipeline.

Final deterministic gate before trade execution.
Checks all hard rules: trading hours, max daily trades, drawdown limits,
news blackout windows, existing positions, and risk parameters.
Pure Python, no AI calls.
"""
from __future__ import annotations

from datetime import datetime, timezone, time
from typing import Optional

from trading_ai_pipeline.core.types.agent_outputs import (
    RiskOutput,
    ProbabilityOutput,
    ValidatorOutput,
    TradeDirection,
)
from trading_ai_pipeline.core.types.market_data import AccountInfo, PositionInfo


class ValidationRule:
    """Base for a single validation check."""
    name: str

    def check(self, ctx: "ValidationContext") -> Optional[str]:
        """Return failure reason string or None if passed."""
        raise NotImplementedError


class ValidationContext:
    def __init__(
        self,
        direction: TradeDirection,
        risk: RiskOutput,
        probability: ProbabilityOutput,
        account: AccountInfo,
        open_positions: list[PositionInfo],
        symbol: str,
        now: Optional[datetime] = None,
        daily_trade_count: int = 0,
        daily_loss: float = 0.0,
        news_blackout_active: bool = False,
    ) -> None:
        self.direction = direction
        self.risk = risk
        self.probability = probability
        self.account = account
        self.open_positions = open_positions
        self.symbol = symbol
        self.now = now or datetime.now(timezone.utc)
        self.daily_trade_count = daily_trade_count
        self.daily_loss = daily_loss
        self.news_blackout_active = news_blackout_active


# ---------------------------------------------------------------------------
# Individual rules
# ---------------------------------------------------------------------------

class RiskApprovedRule(ValidationRule):
    name = "risk_approved"

    def check(self, ctx: ValidationContext) -> Optional[str]:
        if not ctx.risk.approved:
            return f"Risk manager rejected: {ctx.risk.rejection_reason}"
        return None


class ProbabilityThresholdRule(ValidationRule):
    name = "probability_threshold"

    def __init__(self, min_confidence: float = 0.55) -> None:
        self.min_confidence = min_confidence

    def check(self, ctx: ValidationContext) -> Optional[str]:
        if not ctx.probability.proceed:
            return (
                f"Probability estimator says no-proceed "
                f"(confidence: {ctx.probability.final_confidence:.2%})"
            )
        if ctx.probability.final_confidence < self.min_confidence:
            return (
                f"Final confidence {ctx.probability.final_confidence:.2%} "
                f"below threshold {self.min_confidence:.2%}"
            )
        return None


class TradingHoursRule(ValidationRule):
    name = "trading_hours"

    # Avoid low-liquidity periods (UTC)
    BLACKOUT_WINDOWS: list[tuple[time, time]] = [
        (time(21, 45), time(23, 0)),   # Late NY / pre-Asian
        (time(0, 0), time(1, 0)),       # Early Asian low liquidity
    ]

    def check(self, ctx: ValidationContext) -> Optional[str]:
        current_time = ctx.now.time().replace(second=0, microsecond=0)
        for start, end in self.BLACKOUT_WINDOWS:
            if start <= current_time <= end:
                return (
                    f"Trading hours blackout: {start.strftime('%H:%M')} – "
                    f"{end.strftime('%H:%M')} UTC"
                )
        return None


class NewsBlackoutRule(ValidationRule):
    name = "news_blackout"

    def check(self, ctx: ValidationContext) -> Optional[str]:
        if ctx.news_blackout_active:
            return "High-impact news event within blackout window"
        return None


class MaxDailyTradesRule(ValidationRule):
    name = "max_daily_trades"

    def __init__(self, max_trades: int = 5) -> None:
        self.max_trades = max_trades

    def check(self, ctx: ValidationContext) -> Optional[str]:
        if ctx.daily_trade_count >= self.max_trades:
            return (
                f"Daily trade limit reached: "
                f"{ctx.daily_trade_count}/{self.max_trades}"
            )
        return None


class MaxDailyLossRule(ValidationRule):
    name = "max_daily_loss"

    def __init__(self, max_loss_percent: float = 3.0) -> None:
        self.max_loss_percent = max_loss_percent

    def check(self, ctx: ValidationContext) -> Optional[str]:
        if ctx.account.balance and ctx.account.balance > 0:
            loss_pct = (ctx.daily_loss / ctx.account.balance) * 100
            if loss_pct >= self.max_loss_percent:
                return (
                    f"Daily loss limit reached: "
                    f"{loss_pct:.2f}% >= {self.max_loss_percent}%"
                )
        return None


class DuplicatePositionRule(ValidationRule):
    name = "duplicate_position"

    def check(self, ctx: ValidationContext) -> Optional[str]:
        for pos in ctx.open_positions:
            if pos.symbol == ctx.symbol:
                return (
                    f"Already have open position on {ctx.symbol} "
                    f"(ticket: {pos.ticket})"
                )
        return None


class AccountDrawdownRule(ValidationRule):
    name = "account_drawdown"

    def __init__(self, max_drawdown_percent: float = 10.0) -> None:
        self.max_drawdown_percent = max_drawdown_percent

    def check(self, ctx: ValidationContext) -> Optional[str]:
        balance = ctx.account.balance
        equity = ctx.account.equity
        if balance and equity and balance > 0:
            drawdown = ((balance - equity) / balance) * 100
            if drawdown >= self.max_drawdown_percent:
                return (
                    f"Account drawdown {drawdown:.2f}% "
                    f">= limit {self.max_drawdown_percent}%"
                )
        return None


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class RuleValidator:
    """
    Runs all validation rules sequentially.
    Returns ValidatorOutput with pass/fail and list of violations.
    """

    DEFAULT_RULES: list[ValidationRule] = [
        RiskApprovedRule(),
        ProbabilityThresholdRule(),
        TradingHoursRule(),
        NewsBlackoutRule(),
        MaxDailyTradesRule(),
        MaxDailyLossRule(),
        DuplicatePositionRule(),
        AccountDrawdownRule(),
    ]

    def __init__(self, rules: Optional[list[ValidationRule]] = None) -> None:
        self.rules = rules if rules is not None else self.DEFAULT_RULES

    def validate(self, ctx: ValidationContext) -> ValidatorOutput:
        violations: list[str] = []
        passed_rules: list[str] = []

        for rule in self.rules:
            failure = rule.check(ctx)
            if failure:
                violations.append(f"[{rule.name}] {failure}")
            else:
                passed_rules.append(rule.name)

        approved = len(violations) == 0

        return ValidatorOutput(
            approved=approved,
            violations=violations,
            passed_rules=passed_rules,
            total_rules=len(self.rules),
            rejection_reason=violations[0] if violations else None,
        )
