import time
from typing import Dict, Optional

from pydantic import BaseModel, Field


class TradeDecision(BaseModel):
    side: str  # long, short, flat
    position_fraction: float = Field(0, ge=0, le=0.5)
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
