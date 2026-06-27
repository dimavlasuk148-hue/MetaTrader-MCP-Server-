"""
Core type definitions for the trading AI pipeline.
"""

from .market_data import (
    Candle,
    OHLCV,
    SymbolInfo,
    MarketSnapshot,
    Timeframe,
)
from .indicators import (
    TrendDirection,
    SignalStrength,
    EMACrossSignal,
    MACDSignal,
    RSISignal,
    ATRData,
    ADXData,
    BollingerBands,
    VWAPData,
    IndicatorBundle,
)
from .price_action import (
    SupportResistanceLevel,
    CandlePattern,
    BreakoutSignal,
    PriceActionBundle,
)
from .smart_money import (
    StructureBreak,
    FairValueGap,
    OrderBlock,
    LiquiditySweep,
    SmartMoneyBundle,
)
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
    TradeDirection,
    NoTradeReason,
)
from .pipeline_context import PipelineContext, PipelineStatus

__all__ = [
    # Market data
    "Candle",
    "OHLCV",
    "SymbolInfo",
    "MarketSnapshot",
    "Timeframe",
    # Indicators
    "TrendDirection",
    "SignalStrength",
    "EMACrossSignal",
    "MACDSignal",
    "RSISignal",
    "ATRData",
    "ADXData",
    "BollingerBands",
    "VWAPData",
    "IndicatorBundle",
    # Price action
    "SupportResistanceLevel",
    "CandlePattern",
    "BreakoutSignal",
    "PriceActionBundle",
    # Smart money
    "StructureBreak",
    "FairValueGap",
    "OrderBlock",
    "LiquiditySweep",
    "SmartMoneyBundle",
    # Agent outputs
    "TechnicalAnalysis",
    "PriceActionAnalysis",
    "SmartMoneyAnalysis",
    "ConsensusResult",
    "ReviewerVerdict",
    "ProbabilityEstimate",
    "RiskParameters",
    "ValidationResult",
    "TradeDecision",
    "TradeDirection",
    "NoTradeReason",
    # Pipeline
    "PipelineContext",
    "PipelineStatus",
]
