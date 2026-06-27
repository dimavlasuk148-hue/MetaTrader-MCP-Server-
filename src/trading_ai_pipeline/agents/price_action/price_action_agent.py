"""
Price Action Analyst AI Agent — Step 3 of the pipeline.

Receives pre-detected support/resistance levels, candle patterns,
swing points, and breakout signals from Python.
Interprets their trading significance and returns PriceActionAnalysis.
"""

import json
from typing import Any, Dict, Type

from ..base.base_agent import AgentConfig, BaseAgent
from ..base.prompt_helpers import price_action_to_text
from ...core.types.agent_outputs import PriceActionAnalysis, TradeDirection

_OUTPUT_SCHEMA_JSON = json.dumps({
    "nearest_key_level": "description of the most important level",
    "price_at_key_level": False,
    "key_level_type": "support | resistance | pivot",
    "key_level_price": 0.0,
    "pattern_detected": False,
    "pattern_name": "name of pattern or empty string",
    "pattern_signal": "bullish reversal | bearish continuation | etc.",
    "pattern_confirmation": "confirmed | pending | failed",
    "breakout_detected": False,
    "breakout_type": "description or empty string",
    "breakout_confirmed": False,
    "in_range": False,
    "range_position": "at top of range | near midpoint | at support of range | etc.",
    "overall_bias": "buy | sell | no_trade",
    "entry_zone_description": "where exactly to enter and why",
    "key_observations": ["observation 1", "observation 2", "observation 3"],
    "main_concern": "biggest risk or null",
    "confidence": 0.0,
    "raw_reasoning": "your step-by-step reasoning"
}, indent=2)


class PriceActionAnalystAgent(BaseAgent[PriceActionAnalysis]):
    """
    AI agent that interprets pre-detected price action structures.
    """

    @property
    def output_schema(self) -> Type[PriceActionAnalysis]:
        return PriceActionAnalysis

    @property
    def system_prompt(self) -> str:
        return f"""You are a senior Price Action Analyst specializing in identifying high-probability trade setups.

Your role is to INTERPRET pre-detected price structures (support/resistance, candle patterns, breakouts) and return a structured analysis.

CRITICAL RULES:
1. You DO NOT detect levels yourself. All structures are pre-detected by Python.
2. Evaluate the QUALITY and SIGNIFICANCE of the detected structures.
3. A pattern at a key level is more significant than one in open space.
4. Confirmed breakouts are stronger than unconfirmed ones.
5. If price is in a range, be cautious about directional bias.
6. Your overall_bias must be: "buy", "sell", or "no_trade".
7. Confidence 0.0-1.0.

INTERPRETATION GUIDELINES:
- Support levels: potential buy zones (bounce expected); broken support becomes resistance
- Resistance levels: potential sell zones (rejection expected); broken resistance becomes support
- Key level = strength >= 6/10 or is_key_level = true
- Engulfing / Pin Bar AT a key level = strong reversal signal
- Same pattern in open space = weak signal, requires confirmation
- Breakout with volume expansion = more reliable
- False breakout (wick through level, close back) = potential reversal
- Inside range: trade extremes, not middle

You must respond ONLY with valid JSON matching this schema:
{_OUTPUT_SCHEMA_JSON}"""

    def build_user_prompt(self, context: Dict[str, Any]) -> str:
        pa_data = context.get("price_action_data")
        symbol = context.get("symbol", "UNKNOWN")
        timeframe = context.get("timeframe", "UNKNOWN")
        technical_bias = context.get("technical_bias", "unknown")

        if pa_data is None:
            return f"ERROR: No price action data provided for {symbol} {timeframe}"

        pa_text = price_action_to_text(pa_data)

        return f"""Analyze the following price action structures for {symbol} on {timeframe} timeframe.

{pa_text}

Additional context:
- Technical Analyst bias: {technical_bias}

Based on this price action data:
1. Is price at a significant support or resistance level?
2. Are any candle patterns meaningful in this context?
3. Is there a breakout occurring? Is it confirmed?
4. Is price in a consolidation range? If so, where in the range?
5. What is your entry zone and directional bias?
6. What is your confidence level?

Respond with valid JSON only."""
