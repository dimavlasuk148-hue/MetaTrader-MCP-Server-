"""
Probability Estimator — Step 7 of the pipeline.

Takes consensus + reviewer output and computes final
Buy / Sell / No Trade probabilities. Pure Python, no AI calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from trading_ai_pipeline.core.types.agent_outputs import (
    ConsensusOutput,
    ReviewerOutput,
    ProbabilityOutput,
    TradeDirection,
    SignalStrength,
)


# How strongly a reviewer veto reduces the probability
VETO_PENALTY = 0.30
# How much each reviewer concern reduces probability
CONCERN_PENALTY = 0.05
# Maximum total concern penalty
MAX_CONCERN_PENALTY = 0.20


@dataclass
class ProbabilityResult:
    buy_probability: float
    sell_probability: float
    no_trade_probability: float
    recommended_direction: TradeDirection
    final_confidence: float
    adjusted: bool
    adjustments: list[str]


class ProbabilityEstimator:
    """
    Combines consensus confidence with reviewer risk flags to produce
    final trade probabilities for all three outcomes.
    """

    def __init__(
        self,
        veto_penalty: float = VETO_PENALTY,
        concern_penalty: float = CONCERN_PENALTY,
        max_concern_penalty: float = MAX_CONCERN_PENALTY,
        min_final_confidence: float = 0.50,
    ) -> None:
        self.veto_penalty = veto_penalty
        self.concern_penalty = concern_penalty
        self.max_concern_penalty = max_concern_penalty
        self.min_final_confidence = min_final_confidence

    def estimate(
        self,
        consensus: ConsensusOutput,
        reviewer: ReviewerOutput,
    ) -> ProbabilityOutput:
        adjustments: list[str] = []
        base_confidence = consensus.confidence

        # --- Apply reviewer adjustments ---
        adjusted_confidence = base_confidence
        adjusted = False

        if reviewer.veto:
            adjusted_confidence -= self.veto_penalty
            adjustments.append(
                f"Reviewer veto applied: -{self.veto_penalty:.0%} "
                f"(reason: {reviewer.veto_reason})"
            )
            adjusted = True

        concern_penalty = min(
            len(reviewer.concerns) * self.concern_penalty,
            self.max_concern_penalty,
        )
        if concern_penalty > 0:
            adjusted_confidence -= concern_penalty
            adjustments.append(
                f"{len(reviewer.concerns)} reviewer concerns: "
                f"-{concern_penalty:.0%}"
            )
            adjusted = True

        # Clamp to [0, 1]
        adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))

        # --- Calculate direction probabilities ---
        direction = consensus.direction
        buy_prob, sell_prob, no_trade_prob = self._compute_probabilities(
            direction, adjusted_confidence, consensus
        )

        # --- Determine recommendation ---
        recommended = self._recommend(
            buy_prob, sell_prob, no_trade_prob, adjusted_confidence
        )

        return ProbabilityOutput(
            buy_probability=round(buy_prob, 4),
            sell_probability=round(sell_prob, 4),
            no_trade_probability=round(no_trade_prob, 4),
            recommended_direction=recommended,
            base_confidence=round(base_confidence, 4),
            final_confidence=round(adjusted_confidence, 4),
            adjusted=adjusted,
            adjustments=adjustments,
            proceed=recommended != TradeDirection.NO_TRADE
            and adjusted_confidence >= self.min_final_confidence,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _compute_probabilities(
        self,
        direction: TradeDirection,
        confidence: float,
        consensus: ConsensusOutput,
    ) -> tuple[float, float, float]:
        """
        Distributes probability mass across Buy / Sell / No Trade.
        The winning direction gets the adjusted confidence as its probability.
        Remaining probability is split between the other two outcomes.
        """
        # Conflict ratio lowers certainty
        conflict_ratio = (
            len(consensus.conflicts) / consensus.total_agents
            if consensus.total_agents > 0
            else 0.0
        )
        uncertainty_bonus = conflict_ratio * 0.15  # up to 15% no-trade bonus

        if direction == TradeDirection.BUY:
            buy = confidence * (1 - uncertainty_bonus)
            no_trade = uncertainty_bonus + (1 - confidence) * 0.6
            sell = max(0.0, 1.0 - buy - no_trade)
        elif direction == TradeDirection.SELL:
            sell = confidence * (1 - uncertainty_bonus)
            no_trade = uncertainty_bonus + (1 - confidence) * 0.6
            buy = max(0.0, 1.0 - sell - no_trade)
        else:
            no_trade = 0.60 + confidence * 0.20
            buy = (1 - no_trade) / 2
            sell = (1 - no_trade) / 2

        # Normalise to exactly 1.0
        total = buy + sell + no_trade
        if total > 0:
            buy /= total
            sell /= total
            no_trade /= total

        return round(buy, 4), round(sell, 4), round(no_trade, 4)

    def _recommend(
        self,
        buy: float,
        sell: float,
        no_trade: float,
        confidence: float,
    ) -> TradeDirection:
        if confidence < self.min_final_confidence:
            return TradeDirection.NO_TRADE

        probs = {
            TradeDirection.BUY: buy,
            TradeDirection.SELL: sell,
            TradeDirection.NO_TRADE: no_trade,
        }
        return max(probs, key=lambda d: probs[d])
