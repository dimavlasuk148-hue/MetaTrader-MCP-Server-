"""
Agent output type definitions.

These are the structured JSON outputs each AI agent must return.
Every agent returns arguments (metrics + interpretation), never raw "buy/sell".
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TradeDirection(str, Enum):
    BUY = "buy"
    SELL = "sell"
    NO_TRADE = "no_trade"


class NoTradeReason(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    CONFLICTING_SIGNALS = "conflicting_signals"
    HIGH_SPREAD = "high_spread"
    UNFAVORABLE_RISK_REWARD = "unfavorable_risk_reward"
    NEWS_RISK = "news_risk"
    MARKET_CLOSED = "market_closed"
    ALREADY_IN_TRADE = "already_in_trade"
    REVIEWER_REJECTED = "reviewer_rejected"
    RULE_VIOLATION = "rule_violation"
    INSUFFICIENT_DATA = "insufficient_data"


# ─────────────────────────────────────────────
# Step 2: Technical Analyst Output
# ─────────────────────────────────────────────

class TechnicalAnalysis(BaseModel):
    """
    Output of the Technical Analyst AI agent.
    Agent interprets pre-calculated indicators; does NOT calculate them.
    """

    # Trend assessment
    trend_direction: str = ""           # "bullish" / "bearish" / "sideways"
    trend_strength: str = ""            # "strong" / "moderate" / "weak"
    trend_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # EMA interpretation
    ema_signal: str = ""                # "bullish alignment" / "death cross" / etc.
    price_relative_to_ema200: str = ""  # "above" / "below" / "at"

    # MACD interpretation
    macd_signal: str = ""               # "bullish crossover" / "bearish divergence" / etc.
    macd_momentum: str = ""             # "expanding" / "fading" / "reversing"

    # RSI interpretation
    rsi_signal: str = ""                # "neutral" / "overbought" / "oversold with divergence"

    # ADX interpretation
    adx_signal: str = ""                # "strong trend" / "ranging" / "trend weakening"

    # Bollinger
    bollinger_signal: str = ""          # "squeeze breakout" / "upper band touch" / etc.

    # Overall verdict
    overall_bias: TradeDirection = TradeDirection.NO_TRADE
    key_observations: List[str] = Field(default_factory=list)   # max 3 bullets
    main_concern: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_reasoning: str = ""


# ─────────────────────────────────────────────
# Step 3: Price Action Analyst Output
# ─────────────────────────────────────────────

class PriceActionAnalysis(BaseModel):
    """
    Output of the Price Action AI agent.
    """

    # Structure
    nearest_key_level: str = ""
    price_at_key_level: bool = False
    key_level_type: str = ""            # "support" / "resistance" / "pivot"
    key_level_price: Optional[float] = None

    # Pattern
    pattern_detected: bool = False
    pattern_name: str = ""
    pattern_signal: str = ""            # "bullish reversal" / "bearish continuation" / etc.
    pattern_confirmation: str = ""      # "confirmed" / "pending" / "failed"

    # Breakout
    breakout_detected: bool = False
    breakout_type: str = ""
    breakout_confirmed: bool = False

    # Range context
    in_range: bool = False
    range_position: str = ""            # "at top of range" / "near midpoint" / etc.

    # Overall
    overall_bias: TradeDirection = TradeDirection.NO_TRADE
    entry_zone_description: str = ""
    key_observations: List[str] = Field(default_factory=list)
    main_concern: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_reasoning: str = ""


# ─────────────────────────────────────────────
# Step 4: Smart Money Analyst Output
# ─────────────────────────────────────────────

class SmartMoneyAnalysis(BaseModel):
    """
    Output of the Smart Money Concept AI agent.
    """

    # Structure
    market_structure: str = ""          # "bullish BOS confirmed" / "CHoCH bearish" / etc.
    structure_significance: str = ""    # "major" / "minor" / "internal"

    # FVG
    fvg_relevant: bool = False
    fvg_description: str = ""
    price_in_fvg: bool = False

    # Order Block
    ob_relevant: bool = False
    ob_description: str = ""
    price_at_ob: bool = False

    # Liquidity
    liquidity_swept: bool = False
    sweep_description: str = ""
    continuation_likely: bool = False

    # HTF alignment
    htf_aligned: bool = False
    htf_description: str = ""

    # Premium / Discount
    zone_type: str = ""                 # "premium" / "discount" / "equilibrium"

    # Overall
    overall_bias: TradeDirection = TradeDirection.NO_TRADE
    entry_confirmation: str = ""
    key_observations: List[str] = Field(default_factory=list)
    main_concern: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_reasoning: str = ""


# ─────────────────────────────────────────────
# Step 5: Consensus Builder Output
# ─────────────────────────────────────────────

class ConsensusResult(BaseModel):
    """
    Merged output from all three analysts.
    Purely deterministic — no AI involved.
    """

    technical_bias: TradeDirection
    price_action_bias: TradeDirection
    smart_money_bias: TradeDirection

    agreement_count: int = 0          # how many agree (0-3)
    majority_direction: TradeDirection = TradeDirection.NO_TRADE
    consensus_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Weighted average (Technical=0.35, PriceAction=0.30, SmartMoney=0.35)
    weighted_confidence_buy: float = 0.0
    weighted_confidence_sell: float = 0.0

    agents_agreeing: List[str] = Field(default_factory=list)
    agents_disagreeing: List[str] = Field(default_factory=list)

    summary: str = ""


# ─────────────────────────────────────────────
# Step 6: Reviewer Verdict
# ─────────────────────────────────────────────

class ReviewerVerdict(BaseModel):
    """
    Output of the Reviewer / Devil's Advocate AI agent.
    Actively looks for reasons NOT to trade.
    """

    approved: bool = False
    rejection_reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    spread_concern: bool = False
    spread_pips: float = 0.0

    news_risk: bool = False
    news_description: str = ""

    counter_signals: List[str] = Field(default_factory=list)
    conflicting_timeframes: bool = False

    final_recommendation: TradeDirection = TradeDirection.NO_TRADE
    confidence_after_review: float = Field(default=0.0, ge=0.0, le=1.0)
    reviewer_notes: str = ""


# ─────────────────────────────────────────────
# Step 7: Probability Estimator Output
# ─────────────────────────────────────────────

class ProbabilityEstimate(BaseModel):
    """
    Final probability breakdown before risk calculation.
    AI agent assigns probabilities based on all prior context.
    """

    prob_buy: float = Field(default=0.0, ge=0.0, le=1.0)
    prob_sell: float = Field(default=0.0, ge=0.0, le=1.0)
    prob_no_trade: float = Field(default=1.0, ge=0.0, le=1.0)

    recommended_direction: TradeDirection = TradeDirection.NO_TRADE
    edge_score: float = Field(default=0.0, ge=0.0, le=1.0)  # prob_winner - 0.5, normalized

    key_factors_for: List[str] = Field(default_factory=list)
    key_factors_against: List[str] = Field(default_factory=list)

    reasoning: str = ""


# ─────────────────────────────────────────────
# Step 8: Risk Manager Output
# ─────────────────────────────────────────────

class RiskParameters(BaseModel):
    """
    Purely Python-calculated risk parameters. No AI involvement.
    """

    direction: TradeDirection
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float] = None
    take_profit_3: Optional[float] = None

    lot_size: float
    risk_amount_usd: float
    risk_percent_of_balance: float

    risk_reward_ratio: float
    stop_loss_pips: float
    take_profit_pips: float

    atr_multiplier_sl: float = 1.5
    max_slippage_pips: float = 3.0

    is_valid: bool = True
    invalidation_reason: Optional[str] = None


# ─────────────────────────────────────────────
# Step 9: Rule Validator Output
# ─────────────────────────────────────────────

class ValidationResult(BaseModel):
    """
    Final rule check before execution. Deterministic Python logic.
    """

    passed: bool = False
    failed_rules: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    # Individual checks
    spread_ok: bool = True
    balance_ok: bool = True
    margin_ok: bool = True
    position_limit_ok: bool = True
    session_ok: bool = True
    risk_reward_ok: bool = True
    direction_consensus_ok: bool = True

    override_possible: bool = False
    override_reason: Optional[str] = None


# ─────────────────────────────────────────────
# Final Trade Decision
# ─────────────────────────────────────────────

class TradeDecision(BaseModel):
    """
    The final unified decision sent to the executor.
    Contains all parameters needed to place or skip the trade.
    """

    execute: bool = False
    direction: TradeDirection = TradeDirection.NO_TRADE
    no_trade_reason: Optional[NoTradeReason] = None

    symbol: str = ""
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    lot_size: float = 0.0

    risk_reward: float = 0.0
    confidence: float = 0.0
    edge_score: float = 0.0

    pipeline_id: str = ""    # unique ID for this analysis run
    decision_summary: Dict[str, str] = Field(default_factory=dict)
