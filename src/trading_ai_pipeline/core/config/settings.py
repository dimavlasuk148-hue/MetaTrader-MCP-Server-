"""
Configuration system.

Loads settings from YAML/JSON file or environment variables.
All pipeline parameters are centralised here.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class MT5ConnectionConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 18812
    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None
    timeout_ms: int = 10_000


class AIProviderConfig(BaseModel):
    provider: str = "ollama"          # ollama | openai | deepseek | qwen | anthropic
    model: str = "qwen2.5:14b"
    base_url: str = "http://localhost:11434"
    api_key: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 2048
    timeout_seconds: int = 60
    retry_attempts: int = 3


class SymbolConfig(BaseModel):
    symbol: str = "EURUSD"
    timeframe: str = "H1"             # M1 M5 M15 M30 H1 H4 D1
    secondary_timeframe: str = "H4"   # higher timeframe for trend context
    bars_required: int = 200


class RiskConfig(BaseModel):
    risk_percent: float = 1.0
    max_spread_points: int = 20
    min_rr_ratio: float = 1.5
    atr_sl_multiplier: float = 1.5
    atr_tp_multiplier: float = 2.5
    max_lots: float = 10.0
    min_lots: float = 0.01


class TradingRulesConfig(BaseModel):
    max_daily_trades: int = 5
    max_daily_loss_percent: float = 3.0
    max_drawdown_percent: float = 10.0
    news_blackout_minutes: int = 30
    allow_duplicate_positions: bool = False


class ConsensusConfig(BaseModel):
    min_confidence: float = 0.55
    min_agent_agreement: int = 2
    technical_weight: float = 0.35
    price_action_weight: float = 0.30
    smart_money_weight: float = 0.35


class LoggingConfig(BaseModel):
    level: str = "INFO"
    log_dir: str = "logs"
    max_file_size_mb: int = 50
    backup_count: int = 7
    log_agent_prompts: bool = True
    log_agent_responses: bool = True


class MemoryConfig(BaseModel):
    enabled: bool = True
    storage_path: str = "data/memory"
    max_history_entries: int = 1000
    persist_format: str = "jsonl"     # jsonl | sqlite


class PipelineConfig(BaseModel):
    mt5: MT5ConnectionConfig = Field(default_factory=MT5ConnectionConfig)
    ai: AIProviderConfig = Field(default_factory=AIProviderConfig)
    symbol: SymbolConfig = Field(default_factory=SymbolConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    rules: TradingRulesConfig = Field(default_factory=TradingRulesConfig)
    consensus: ConsensusConfig = Field(default_factory=ConsensusConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    dry_run: bool = True              # No real orders when True
    pipeline_interval_seconds: int = 60


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG_PATHS = [
    "config/pipeline.yaml",
    "config/pipeline.yml",
    "config/pipeline.json",
    "pipeline.yaml",
]


def load_config(path: Optional[str] = None) -> PipelineConfig:
    """
    Load PipelineConfig from a YAML/JSON file.
    Falls back to defaults if no file found.
    Environment variables override file values:
      PIPELINE_DRY_RUN, PIPELINE_SYMBOL, PIPELINE_AI_PROVIDER, etc.
    """
    raw: dict = {}

    if path:
        raw = _read_file(Path(path))
    else:
        for candidate in _DEFAULT_CONFIG_PATHS:
            candidate_path = Path(candidate)
            if candidate_path.exists():
                raw = _read_file(candidate_path)
                break

    config = PipelineConfig.model_validate(raw)
    config = _apply_env_overrides(config)
    return config


def _read_file(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        if path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(f) or {}
        elif path.suffix == ".json":
            import json
            return json.load(f)
    return {}


def _apply_env_overrides(config: PipelineConfig) -> PipelineConfig:
    """Apply environment variable overrides to the config."""
    env = os.environ

    if val := env.get("PIPELINE_DRY_RUN"):
        config.dry_run = val.lower() in ("true", "1", "yes")

    if val := env.get("PIPELINE_SYMBOL"):
        config.symbol.symbol = val

    if val := env.get("PIPELINE_TIMEFRAME"):
        config.symbol.timeframe = val

    if val := env.get("PIPELINE_AI_PROVIDER"):
        config.ai.provider = val

    if val := env.get("PIPELINE_AI_MODEL"):
        config.ai.model = val

    if val := env.get("PIPELINE_AI_BASE_URL"):
        config.ai.base_url = val

    if val := env.get("PIPELINE_AI_API_KEY"):
        config.ai.api_key = val

    if val := env.get("PIPELINE_RISK_PERCENT"):
        config.risk.risk_percent = float(val)

    if val := env.get("MT5_LOGIN"):
        config.mt5.login = int(val)

    if val := env.get("MT5_PASSWORD"):
        config.mt5.password = val

    if val := env.get("MT5_SERVER"):
        config.mt5.server = val

    return config
