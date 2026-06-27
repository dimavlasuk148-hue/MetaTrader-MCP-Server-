"""
Trade Memory.

Persists pipeline run results to JSONL for pattern analysis,
backtesting, and agent context enrichment.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from trading_ai_pipeline.core.types.agent_outputs import TradeDirection


class TradeRecord(BaseModel):
    run_id: str
    timestamp: str
    symbol: str
    timeframe: str
    direction: str
    final_confidence: float
    executed: bool
    ticket: Optional[int] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    lots: Optional[float] = None
    rr_ratio: Optional[float] = None
    rejection_reason: Optional[str] = None
    # Outcome (filled after trade closes)
    outcome: Optional[str] = None       # WIN | LOSS | BREAKEVEN | OPEN
    pnl: Optional[float] = None
    pnl_pips: Optional[float] = None
    duration_minutes: Optional[int] = None
    # Snapshots of key metrics at decision time
    technical_direction: Optional[str] = None
    price_action_direction: Optional[str] = None
    smart_money_direction: Optional[str] = None
    consensus_confidence: Optional[float] = None
    reviewer_veto: Optional[bool] = None
    reviewer_concerns_count: Optional[int] = None


class TradeMemory:
    """
    Append-only JSONL store for trade records.
    Provides recent history context for agents.
    """

    def __init__(
        self,
        storage_path: str = "data/memory",
        max_entries: int = 1000,
    ) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.max_entries = max_entries
        self._records: list[TradeRecord] = []
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, trade: TradeRecord) -> None:
        """Append a new trade record and persist."""
        self._records.append(trade)
        if len(self._records) > self.max_entries:
            self._records = self._records[-self.max_entries:]
        self._append_to_file(trade)

    def update_outcome(
        self,
        run_id: str,
        outcome: str,
        pnl: float,
        pnl_pips: float,
        duration_minutes: int,
    ) -> bool:
        """Update outcome of an existing record (after trade closes)."""
        for rec in reversed(self._records):
            if rec.run_id == run_id:
                rec.outcome = outcome
                rec.pnl = pnl
                rec.pnl_pips = pnl_pips
                rec.duration_minutes = duration_minutes
                self._rewrite_file()
                return True
        return False

    def recent(self, n: int = 10, symbol: Optional[str] = None) -> list[TradeRecord]:
        """Return the n most recent records, optionally filtered by symbol."""
        filtered = self._records
        if symbol:
            filtered = [r for r in filtered if r.symbol == symbol]
        return list(reversed(filtered))[:n]

    def win_rate(self, symbol: Optional[str] = None, last_n: int = 50) -> Optional[float]:
        """Calculate win rate for closed trades."""
        closed = [
            r for r in self.recent(last_n, symbol)
            if r.outcome in ("WIN", "LOSS", "BREAKEVEN")
        ]
        if not closed:
            return None
        wins = sum(1 for r in closed if r.outcome == "WIN")
        return round(wins / len(closed), 4)

    def summary_for_agent(self, symbol: str, n: int = 5) -> dict[str, Any]:
        """Compact summary to inject into agent prompts."""
        recent = self.recent(n, symbol)
        return {
            "recent_trades": [
                {
                    "direction": r.direction,
                    "outcome": r.outcome or "OPEN",
                    "confidence": r.final_confidence,
                    "pnl_pips": r.pnl_pips,
                }
                for r in recent
            ],
            "win_rate_last_50": self.win_rate(symbol, 50),
            "total_recorded": len(self._records),
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @property
    def _file_path(self) -> Path:
        return self.storage_path / "trades.jsonl"

    def _load(self) -> None:
        if not self._file_path.exists():
            return
        with open(self._file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        self._records.append(
                            TradeRecord.model_validate_json(line)
                        )
                    except Exception:
                        pass  # Skip malformed lines
        # Keep only the last max_entries
        if len(self._records) > self.max_entries:
            self._records = self._records[-self.max_entries:]

    def _append_to_file(self, trade: TradeRecord) -> None:
        with open(self._file_path, "a", encoding="utf-8") as f:
            f.write(trade.model_dump_json() + "\n")

    def _rewrite_file(self) -> None:
        """Full rewrite — used only when updating outcomes."""
        with open(self._file_path, "w", encoding="utf-8") as f:
            for rec in self._records:
                f.write(rec.model_dump_json() + "\n")
