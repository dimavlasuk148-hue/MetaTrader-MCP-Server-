"""
Technical Analyst AI Agent — Step 2 of the pipeline.

Receives pre-calculated indicators (EMA, MACD, RSI, ADX, ATR, Bollinger, VWAP).
Interprets them and returns a structured TechnicalAnalysis.

This agent does NOT calculate any numbers. Python already did that.
"""

import json
from typing import Any, Dict, Type

from ..base.base_agent import AgentConfig, BaseAgent
from ..base.prompt_helpers import indicators_to_text
from ...core.types.agent_outputs import TechnicalAnalysis, TradeDirection

_OUTPUT_SCHEMA_JSON = json.dumps({
    "trend_direction": "bullish | bearish | sideways",
    "trend_strength": "strong | moderate | weak",
    "trend_confidence": 0.0,
    "ema_signal": "interpretation string",
    "price_relative_to_ema200": "above | below | at",
    "macd_signal": "interpretation string",
    "macd_momentum": "expanding | fading | reversing",
    "rsi_signal": "interpretation string",
    "adx_signal": "interpretation string",
    "bollinger_signal": "interpretation string",
    "overall_bias": "buy | sell | no_trade",
    "key_observations": ["observation 1", "observation 2", "observation 3"],
    "main_concern": "string or null",
    "confidence": 0.0,
    "raw_reasoning": "your step-by-step reasoning"
}, indent=2)


class TechnicalAnalystAgent(BaseAgent[TechnicalAnalysis]):
    """
    AI agent that interprets pre-calculated technical indicators.
    """

    @property
    def output_schema(self) -> Type[TechnicalAnalysis]:
        return TechnicalAnalysis

    @property
    def system_prompt(self) -> str:
        return f"""You are a senior Technical Analyst specializing in Forex and CFD markets.

Your role is to INTERPRET pre-calculated technical indicator data and return a structured analysis.

CRITICAL RULES:
1. You DO NOT calculate any indicators yourself. All values are pre-calculated by Python.
2. You interpret what the indicators are SAYING collectively.
3. Look for confluence: when multiple indicators agree, confidence is higher.
4. Look for conflicts: when indicators disagree, confidence is lower, consider no_trade.
5. Be HONEST about uncertainty. If signals are mixed, say so.
6. Your overall_bias must be one of: "buy", "sell", or "no_trade".
7. Confidence must be between 0.0 and 1.0 (e.g. 0.75 = 75% confident).

INDICATOR INTERPRETATION GUIDELINES:
- EMA alignment (fast > slow > price): bullish trend | (fast < slow < price): bearish trend
- MACD: histogram expanding in direction = momentum building; shrinking = fading momentum
- RSI >70: overbought (careful with buy signals) | RSI <30: oversold (careful with sell signals)
- RSI divergence: strong reversal signal
- ADX >25: trending market | ADX <20: ranging/choppy
- Bollinger squeeze: low volatility, expect breakout
- Price at VWAP: neutral zone; price far from VWAP = stretched

You must respond ONLY with valid JSON matching this schema:
{_OUTPUT_SCHEMA_JSON}"""

    def build_user_prompt(self, context: Dict[str, Any]) -> str:
        indicators = context.get("indicators")
        symbol = context.get("symbol", "UNKNOWN")
        timeframe = context.get("timeframe", "UNKNOWN")

        if indicators is None:
            return f"ERROR: No indicator data provided for {symbol} {timeframe}"

        indicator_text = indicators_to_text(indicators)

        return f"""Analyze the following technical indicators for {symbol} on {timeframe} timeframe.

{indicator_text}

Based on this indicator data:
1. What is the overall trend direction and strength?
2. Are indicators in confluence (agree) or conflict (disagree)?
3. Are there any divergence signals (RSI/MACD vs price)?
4. What is your overall trading bias (buy/sell/no_trade)?
5. What is your confidence level?

Respond with valid JSON only."""
