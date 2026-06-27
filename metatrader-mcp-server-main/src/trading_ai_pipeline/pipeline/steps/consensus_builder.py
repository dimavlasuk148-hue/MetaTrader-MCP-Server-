"""
Consensus Builder — Step 5 of the pipeline.

Merges outputs from Technical, Price Action, and Smart Money agents.
Assigns weighted confidence score. Pure Python, no AI calls.
"""
from __future__ import annotations

from typing import Optional
from dataclasses import dataclass

from trading_ai_pipeline.core.types.agent_outputs import (
    TechnicalAnalysisOutput,
    PriceActionOutput,
    SmartMoneyOutput,
    ConsensusOutput,
    TradeDirection,
    SignalStrength,
)


# Weights for each agent's contribution to consensus
AGENT_WEIGHTS = {
    "technical": 0.35,
    "price_action": 0.30,
    "smart_money": 0.35,
}

# Minimum combined confidence to proceed with a trade
MIN_CONSENSUS_CONFIDENCE = 0.55

# Minimum number of agents that must agree on direction
MIN_AGENT_AGREEMENT = 2


@dataclass
class AgentVote:
    agent_name: str
    direction: TradeDirection
    confidence: float
    weight: float


class ConsensusBuilder:
    """
    Merges the three analyst outputs into a single consensus result.
    Calculates weighted confidence and determines if a trade signal is valid.
    """

    def __init__(
        self,
        min_confidence: float = MIN_CONSENSUS_CONFIDENCE,
        min_agreement: int = MIN_AGENT_AGREEMENT,
        weights: Optional[dict[str, float]] = None,
    ) -> None:
        self.min_confidence = min_confidence
        self.min_agreement = min_agreement
        self.weights = weights or AGENT_WEIGHTS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        technical: TechnicalAnalysisOutput,
        price_action: PriceActionOutput,
        smart_money: SmartMoneyOutput,
    ) -> ConsensusOutput:
        votes = self._collect_votes(technical, price_action, smart_money)
        direction, agreement_count = self._determine_direction(votes)
        weighted_confidence = self._weighted_confidence(votes, direction)
        signal_strength = self._classify_signal(weighted_confidence)
        conflicts = self._detect_conflicts(votes, direction)
        proceed = self._should_proceed(
            direction, agreement_count, weighted_confidence
        )

        return ConsensusOutput(
            direction=direction,
            confidence=round(weighted_confidence, 4),
            signal_strength=signal_strength,
            agreement_count=agreement_count,
            total_agents=len(votes),
            conflicts=conflicts,
            proceed=proceed,
            technical_weight=self.weights["technical"],
            price_action_weight=self.weights["price_action"],
            smart_money_weight=self.weights["smart_money"],
            technical_direction=technical.trend_direction,
            price_action_direction=price_action.bias,
            smart_money_direction=smart_money.market_bias,
            technical_confidence=technical.confidence,
            price_action_confidence=price_action.confidence,
            smart_money_confidence=smart_money.confidence,
            rejection_reason=self._rejection_reason(
                direction, agreement_count, weighted_confidence, proceed
            ),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_votes(
        self,
        technical: TechnicalAnalysisOutput,
        price_action: PriceActionOutput,
        smart_money: SmartMoneyOutput,
    ) -> list[AgentVote]:
        return [
            AgentVote(
                agent_name="technical",
                direction=technical.trend_direction,
                confidence=technical.confidence,
                weight=self.weights["technical"],
            ),
            AgentVote(
                agent_name="price_action",
                direction=price_action.bias,
                confidence=price_action.confidence,
                weight=self.weights["price_action"],
            ),
            AgentVote(
                agent_name="smart_money",
                direction=smart_money.market_bias,
                confidence=smart_money.confidence,
                weight=self.weights["smart_money"],
            ),
        ]

    def _determine_direction(
        self, votes: list[AgentVote]
    ) -> tuple[TradeDirection, int]:
        """
        Majority vote weighted by confidence.
        Returns (winning direction, number of agents that voted for it).
        """
        scores: dict[TradeDirection, float] = {}
        counts: dict[TradeDirection, int] = {}

        for v in votes:
            if v.direction not in scores:
                scores[v.direction] = 0.0
                counts[v.direction] = 0
            scores[v.direction] += v.confidence * v.weight
            counts[v.direction] += 1

        if not scores:
            return TradeDirection.NO_TRADE, 0

        # Exclude NO_TRADE from winning unless it dominates
        actionable = {
            d: s
            for d, s in scores.items()
            if d != TradeDirection.NO_TRADE
        }

        if not actionable:
            return TradeDirection.NO_TRADE, counts.get(TradeDirection.NO_TRADE, 0)

        winning_direction = max(actionable, key=lambda d: actionable[d])
        return winning_direction, counts.get(winning_direction, 0)

    def _weighted_confidence(
        self, votes: list[AgentVote], direction: TradeDirection
    ) -> float:
        """
        Weighted average confidence of agents that agree with the winning direction.
        Agents that disagree contribute a penalty.
        """
        if direction == TradeDirection.NO_TRADE:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for v in votes:
            if v.direction == direction:
                weighted_sum += v.confidence * v.weight
                total_weight += v.weight
            elif v.direction != TradeDirection.NO_TRADE:
                # Opposing vote: subtract penalty
                penalty = v.confidence * v.weight * 0.5
                weighted_sum -= penalty
                total_weight += v.weight * 0.5

        if total_weight == 0:
            return 0.0

        return max(0.0, min(1.0, weighted_sum / total_weight))

    def _classify_signal(self, confidence: float) -> SignalStrength:
        if confidence >= 0.80:
            return SignalStrength.STRONG
        elif confidence >= 0.65:
            return SignalStrength.MODERATE
        elif confidence >= 0.50:
            return SignalStrength.WEAK
        else:
            return SignalStrength.NO_SIGNAL

    def _detect_conflicts(
        self, votes: list[AgentVote], direction: TradeDirection
    ) -> list[str]:
        conflicts = []
        for v in votes:
            if v.direction != direction and v.direction != TradeDirection.NO_TRADE:
                conflicts.append(
                    f"{v.agent_name} disagrees: voted {v.direction.value} "
                    f"with confidence {v.confidence:.2f}"
                )
        return conflicts

    def _should_proceed(
        self,
        direction: TradeDirection,
        agreement_count: int,
        confidence: float,
    ) -> bool:
        if direction == TradeDirection.NO_TRADE:
            return False
        if agreement_count < self.min_agreement:
            return False
        if confidence < self.min_confidence:
            return False
        return True

    def _rejection_reason(
        self,
        direction: TradeDirection,
        agreement_count: int,
        confidence: float,
        proceed: bool,
    ) -> Optional[str]:
        if proceed:
            return None
        if direction == TradeDirection.NO_TRADE:
            return "All agents returned NO_TRADE"
        if agreement_count < self.min_agreement:
            return (
                f"Only {agreement_count}/{self.min_agreement} agents agree "
                f"on {direction.value}"
            )
        if confidence < self.min_confidence:
            return (
                f"Consensus confidence {confidence:.2%} below "
                f"threshold {self.min_confidence:.2%}"
            )
        return "Unknown rejection"
