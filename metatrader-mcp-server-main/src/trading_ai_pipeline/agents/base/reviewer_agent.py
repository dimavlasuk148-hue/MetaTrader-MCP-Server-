"""
Reviewer / Devil's Advocate AI Agent — Step 6 of the pipeline.

Receives all three analyst outputs + consensus.
Actively looks for reasons NOT to take the trade.
Returns ReviewerVerdict.
"""

import json
from typing import Any, Dict, Type

from .base_agent import AgentConfig, BaseAgent
from ...core.types.agent_outputs import ReviewerVerdict, TradeDirection

_OUTPUT_SCHEMA_JSON = json.dumps({
    "approved": False,
    "rejection_reasons": ["reason 1", "reason 2"],
    "warnings": ["warning 1"],
    "spread_concern": False,
    "spread_pips": 0.0,
    "news_risk": False,
    "news_description": "",
    "counter_signals": ["counter signal 1"],
    "conflicting_timeframes": False,
    "final_recommendation": "buy | sell | no_trade",
    "confidence_after_review": 0.0,
    "reviewer_notes": "detailed explanation of your verdict"
}, indent=2)


class ReviewerAgent(BaseAgent[ReviewerVerdict]):
    """
    Devil's Advocate AI agent. Challenges the consensus and looks for flaws.
    """

    @property
    def output_schema(self) -> Type[ReviewerVerdict]:
        return ReviewerVerdict

    @property
    def system_prompt(self) -> str:
        return f"""You are a Risk Reviewer and Devil's Advocate for a professional trading system.

Three analysts (Technical, Price Action, Smart Money) have analyzed the market and reached a consensus.
Your job is to CHALLENGE their conclusion and find reasons NOT to trade.

YOUR ROLE:
- You are the last line of defense before a real trade is placed
- You must actively look for flaws, risks, and counterarguments
- A GOOD reviewer SAVES money by preventing bad trades
- You do NOT simply rubber-stamp the consensus
- You must be STRICT about risk management

CHECK FOR THESE RED FLAGS:
1. High spread (> 3 pips for majors, > 8 pips for exotics): reject
2. Conflicting signals between analysts (one says buy, another sell): reduce confidence
3. Very low consensus confidence (< 0.55): lean toward no_trade
4. Low risk/reward ratio (implied by tight TP vs large SL): reject
5. Counter-trend trade without strong confirmation: warn
6. Trading near major session open/close where spreads widen: warn
7. News events pending in next 2 hours: strong warning
8. Divergence between timeframes: warn
9. Price at extreme overbought/oversold already in trade direction: warn
10. Overtrading same symbol without previous trade resolution: warn

APPROVAL CRITERIA:
- Approve: majority of checks pass, confidence >= 0.6, no hard rejections
- Reject: ANY hard rejection rule triggered, OR confidence < 0.5

You must respond ONLY with valid JSON matching this schema:
{_OUTPUT_SCHEMA_JSON}"""

    def build_user_prompt(self, context: Dict[str, Any]) -> str:
        symbol = context.get("symbol", "UNKNOWN")
        timeframe = context.get("timeframe", "UNKNOWN")
        consensus = context.get("consensus")
        technical = context.get("technical_analysis")
        price_action = context.get("price_action_analysis")
        smart_money = context.get("smart_money_analysis")
        spread_pips = context.get("spread_pips", 0.0)
        account_balance = context.get("account_balance", 0.0)
        open_positions = context.get("open_positions_count", 0)
        current_hour_utc = context.get("current_hour_utc", 12)

        lines = [
            f"REVIEW REQUEST: {symbol} | {timeframe}",
            f"Current spread: {spread_pips:.1f} pips",
            f"Account balance: ${account_balance:.2f}",
            f"Open positions: {open_positions}",
            f"Current UTC hour: {current_hour_utc}:00",
            "",
            "=== CONSENSUS SUMMARY ===",
        ]

        if consensus:
            lines.extend([
                f"Technical bias: {consensus.technical_bias.value}",
                f"Price Action bias: {consensus.price_action_bias.value}",
                f"Smart Money bias: {consensus.smart_money_bias.value}",
                f"Majority direction: {consensus.majority_direction.value}",
                f"Agreement: {consensus.agreement_count}/3 analysts",
                f"Consensus confidence: {consensus.consensus_confidence:.2f}",
                f"Weighted buy confidence: {consensus.weighted_confidence_buy:.2f}",
                f"Weighted sell confidence: {consensus.weighted_confidence_sell:.2f}",
            ])

        if technical:
            lines.extend([
                "",
                "=== TECHNICAL ANALYST CONCERNS ===",
                f"Main concern: {technical.main_concern or 'none'}",
                f"Key observations: {', '.join(technical.key_observations)}",
            ])

        if price_action:
            lines.extend([
                "",
                "=== PRICE ACTION ANALYST CONCERNS ===",
                f"Main concern: {price_action.main_concern or 'none'}",
                f"Entry zone: {price_action.entry_zone_description}",
            ])

        if smart_money:
            lines.extend([
                "",
                "=== SMART MONEY ANALYST CONCERNS ===",
                f"Main concern: {smart_money.main_concern or 'none'}",
                f"HTF aligned: {smart_money.htf_aligned}",
                f"Zone type: {smart_money.zone_type}",
            ])

        lines.extend([
            "",
            "Your task: Challenge this consensus. Find reasons NOT to trade.",
            "Be strict. Real money is at stake.",
            "Respond with valid JSON only.",
        ])

        return "\n".join(lines)


# ─────────────────────────────────────────────
# Probability Estimator Agent
# ─────────────────────────────────────────────

_PROB_SCHEMA_JSON = json.dumps({
    "prob_buy": 0.0,
    "prob_sell": 0.0,
    "prob_no_trade": 1.0,
    "recommended_direction": "buy | sell | no_trade",
    "edge_score": 0.0,
    "key_factors_for": ["factor 1", "factor 2"],
    "key_factors_against": ["factor 1"],
    "reasoning": "step by step probability reasoning"
}, indent=2)

from ...core.types.agent_outputs import ProbabilityEstimate


class ProbabilityEstimatorAgent(BaseAgent[ProbabilityEstimate]):
    """
    AI agent that assigns final trade probabilities after all analysis.
    """

    @property
    def output_schema(self) -> Type[ProbabilityEstimate]:
        return ProbabilityEstimate

    @property
    def system_prompt(self) -> str:
        return f"""You are a quantitative probability estimator for a professional trading system.

You receive analysis from three specialists and a reviewer's verdict.
Your job is to assign PROBABILITIES to possible outcomes: Buy, Sell, or No Trade.

RULES:
1. prob_buy + prob_sell + prob_no_trade MUST equal exactly 1.0
2. edge_score = max(prob_buy, prob_sell) - 0.5 (range: 0.0 to 0.5)
3. If reviewer rejected: prob_no_trade should be >= 0.6
4. If all 3 analysts agree: the agreeing direction gets higher probability
5. Consider the reviewer's warnings in your assessment
6. Be honest about uncertainty — a 55/45 split is common for borderline cases

recommended_direction:
- "buy" if prob_buy > prob_sell AND prob_buy > prob_no_trade
- "sell" if prob_sell > prob_buy AND prob_sell > prob_no_trade
- "no_trade" otherwise

You must respond ONLY with valid JSON matching this schema:
{_PROB_SCHEMA_JSON}"""

    def build_user_prompt(self, context: Dict[str, Any]) -> str:
        symbol = context.get("symbol", "UNKNOWN")
        timeframe = context.get("timeframe", "UNKNOWN")
        consensus = context.get("consensus")
        reviewer = context.get("reviewer_verdict")

        lines = [
            f"Estimate trade probabilities for: {symbol} | {timeframe}",
            "",
            "=== CONSENSUS ===",
        ]

        if consensus:
            lines.extend([
                f"Direction: {consensus.majority_direction.value}",
                f"Agreement: {consensus.agreement_count}/3",
                f"Confidence: {consensus.consensus_confidence:.2f}",
                f"Weighted buy: {consensus.weighted_confidence_buy:.2f}",
                f"Weighted sell: {consensus.weighted_confidence_sell:.2f}",
                f"Summary: {consensus.summary}",
            ])

        if reviewer:
            lines.extend([
                "",
                "=== REVIEWER VERDICT ===",
                f"Approved: {reviewer.approved}",
                f"Rejection reasons: {', '.join(reviewer.rejection_reasons) if reviewer.rejection_reasons else 'none'}",
                f"Warnings: {', '.join(reviewer.warnings) if reviewer.warnings else 'none'}",
                f"Confidence after review: {reviewer.confidence_after_review:.2f}",
                f"Final recommendation: {reviewer.final_recommendation.value}",
            ])

        lines.extend([
            "",
            "Assign probabilities. Remember: prob_buy + prob_sell + prob_no_trade = 1.0",
            "Respond with valid JSON only.",
        ])

        return "\n".join(lines)
