"""
Smart Money Concept (SMC) Analyst AI Agent — Step 4 of the pipeline.

Receives pre-detected BOS, CHoCH, FVG, Order Blocks, and Liquidity Sweeps.
Interprets their institutional significance and returns SmartMoneyAnalysis.
"""

import json
from typing import Any, Dict, Type

from ..base.base_agent import AgentConfig, BaseAgent
from ..base.prompt_helpers import smart_money_to_text
from ...core.types.agent_outputs import SmartMoneyAnalysis, TradeDirection

_OUTPUT_SCHEMA_JSON = json.dumps({
    "market_structure": "description: bullish BOS confirmed / CHoCH bearish / etc.",
    "structure_significance": "major | minor | internal",
    "fvg_relevant": False,
    "fvg_description": "description of the most relevant FVG or empty",
    "price_in_fvg": False,
    "ob_relevant": False,
    "ob_description": "description of the most relevant OB or empty",
    "price_at_ob": False,
    "liquidity_swept": False,
    "sweep_description": "description of liquidity sweep or empty",
    "continuation_likely": False,
    "htf_aligned": False,
    "htf_description": "higher timeframe structure alignment description",
    "zone_type": "premium | discount | equilibrium",
    "overall_bias": "buy | sell | no_trade",
    "entry_confirmation": "what specific confirmation is needed for entry",
    "key_observations": ["observation 1", "observation 2", "observation 3"],
    "main_concern": "biggest risk or null",
    "confidence": 0.0,
    "raw_reasoning": "your step-by-step reasoning"
}, indent=2)


class SmartMoneyAnalystAgent(BaseAgent[SmartMoneyAnalysis]):
    """
    AI agent that interprets pre-detected Smart Money Concept structures.
    """

    @property
    def output_schema(self) -> Type[SmartMoneyAnalysis]:
        return SmartMoneyAnalysis

    @property
    def system_prompt(self) -> str:
        return f"""You are a senior Smart Money Concept (SMC) analyst. You understand how institutional players (banks, hedge funds) move markets.

Your role is to INTERPRET pre-detected SMC structures (BOS, CHoCH, FVG, Order Blocks, Liquidity Sweeps) and return a structured analysis.

CRITICAL RULES:
1. You DO NOT detect structures yourself. All structures are pre-detected by Python.
2. Your job is to evaluate their SIGNIFICANCE and trading implications.
3. Your overall_bias must be: "buy", "sell", or "no_trade".
4. Confidence 0.0-1.0.

SMC INTERPRETATION FRAMEWORK:
- BOS (Break of Structure): continuation of trend — trade in direction of break
- CHoCH (Change of Character): potential trend reversal — first signal of reversal
- FVG (Fair Value Gap): imbalance zone — price tends to return to fill it
  - Bullish FVG below price = support zone
  - Bearish FVG above price = resistance zone
- Order Block: institutional order zone — expect price reaction
  - Bullish OB = demand zone below current price
  - Bearish OB = supply zone above current price
- Liquidity Sweep: institutions grab stops before moving in opposite direction
  - Sweep of sell-side liquidity (lows) + BOS bullish = strong buy
  - Sweep of buy-side liquidity (highs) + BOS bearish = strong sell
- Premium zone: price above equilibrium — institutions SELL, retail BUYS
- Discount zone: price below equilibrium — institutions BUY, retail SELLS

HIGHEST PROBABILITY SETUPS:
1. HTF BOS + LTF CHoCH + price at OB + FVG filled = very high confidence
2. Liquidity sweep + immediate BOS confirmation = high confidence
3. Price retesting broken structure level from the other side = moderate confidence

You must respond ONLY with valid JSON matching this schema:
{_OUTPUT_SCHEMA_JSON}"""

    def build_user_prompt(self, context: Dict[str, Any]) -> str:
        smc_data = context.get("smart_money_data")
        symbol = context.get("symbol", "UNKNOWN")
        timeframe = context.get("timeframe", "UNKNOWN")
        technical_bias = context.get("technical_bias", "unknown")
        price_action_bias = context.get("price_action_bias", "unknown")

        if smc_data is None:
            return f"ERROR: No SMC data provided for {symbol} {timeframe}"

        smc_text = smart_money_to_text(smc_data)

        return f"""Analyze the following Smart Money Concept structures for {symbol} on {timeframe} timeframe.

{smc_text}

Additional context from prior analysts:
- Technical Analyst bias: {technical_bias}
- Price Action Analyst bias: {price_action_bias}

Based on this SMC data:
1. What does the current market structure (BOS/CHoCH) tell us about institutional intent?
2. Are there relevant FVGs or Order Blocks providing entry/exit zones?
3. Has there been a recent liquidity sweep? What is the implication?
4. Is the higher timeframe structure aligned with the trade direction?
5. Is price in a premium or discount zone relative to the range?
6. What specific confirmation do you need before entry?

Respond with valid JSON only."""
