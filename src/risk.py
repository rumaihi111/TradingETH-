import time
from typing import Dict, Optional

from pydantic import BaseModel, Field
import json
import os
import time


class TradeDecision(BaseModel):
    side: str  # long, short, flat
    position_fraction: float = Field(0, ge=0, le=1)  # Ignored - bot uses max_position_fraction from config
    stop_loss_pct: float = Field(0)  # can be negative (below entry)
    take_profit_pct: float = Field(0)  # can be negative for shorts
    max_slippage_pct: float = Field(0.5, ge=0)


class FrequencyGuard:
    def __init__(self, max_trades_per_hour: int, cooldown_minutes: int):
        self.max_trades_per_hour = max_trades_per_hour
        self.cooldown_seconds = cooldown_minutes * 60
        self.last_trades = []
        self.last_close_time: Optional[float] = None

    def allow_new_trade(self) -> bool:
        now = time.time()
        self.last_trades = [t for t in self.last_trades if now - t < 3600]
        if len(self.last_trades) >= self.max_trades_per_hour:
            return False
        if self.last_close_time and now - self.last_close_time < self.cooldown_seconds:
            return False
        return True

    def record_open(self):
        self.last_trades.append(time.time())

    def record_close(self):
        self.last_close_time = time.time()


def clamp_decision(decision: Dict, equity_fraction_cap: float) -> TradeDecision:
    raw = TradeDecision(**decision)
    raw.position_fraction = min(raw.position_fraction, equity_fraction_cap)
    if raw.side == "flat":
        raw.position_fraction = 0
    return raw


class RiskManager:
    """Persistent risk manager handling daily loss limit and loss streak pause."""

    def __init__(self, state_path: str = "data/risk_state.json"):
        self.state_path = state_path
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        self.state = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "day_start_ts": 0,
            "day_pnl": 0.0,
            "consecutive_losses": 0,
            "paused_until": 0,
            "shutdown_until": 0,
        }

    def _save(self):
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def _midnight_utc_ts(self) -> float:
        # Compute current UTC midnight epoch
        t = time.gmtime()
        midnight = time.struct_time((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, t.tm_wday, t.tm_yday, 0))
        return time.mktime(midnight)

    def ensure_day_initialized(self):
        now_midnight = self._midnight_utc_ts()
        if self.state["day_start_ts"] != now_midnight:
            # New day: reset daily counters
            self.state["day_start_ts"] = now_midnight
            self.state["day_pnl"] = 0.0
            self._save()

    def is_paused(self) -> bool:
        return time.time() < float(self.state.get("paused_until", 0))

    def is_shutdown(self) -> bool:
        return time.time() < float(self.state.get("shutdown_until", 0))

    def pause_for(self, seconds: int):
        self.state["paused_until"] = time.time() + seconds
        self._save()

    def shutdown_for(self, seconds: int):
        self.state["shutdown_until"] = time.time() + seconds
        self._save()

    def on_trade_closed(self, pnl: float, pause_after_losses: int, pause_duration_sec: int):
        """Update streaks and daily PnL, return flags for actions."""
        self.ensure_day_initialized()
        self.state["day_pnl"] = float(self.state.get("day_pnl", 0.0)) + float(pnl or 0)
        # Update loss streak
        if pnl < 0:
            self.state["consecutive_losses"] = int(self.state.get("consecutive_losses", 0)) + 1
        else:
            self.state["consecutive_losses"] = 0
        self._save()

        triggered_pause = False
        if self.state["consecutive_losses"] >= pause_after_losses:
            self.pause_for(pause_duration_sec)
            triggered_pause = True
        return {
            "triggered_pause": triggered_pause,
            "consecutive_losses": self.state["consecutive_losses"],
            "day_pnl": self.state["day_pnl"],
        }

    def get_day_pnl(self) -> float:
        self.ensure_day_initialized()
        return float(self.state.get("day_pnl", 0.0))
