import ccxt
import math
from typing import List, Dict

from ai_client import AISignalClient
from risk import clamp_decision


def fetch_ohlcv(limit: int = 200) -> List[Dict]:
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=limit)
    return [
        {"ts": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]}
        for c in ohlcv
    ]


def simple_backtest():
    candles = fetch_ohlcv()
    client = AISignalClient(api_key="", endpoint="")  # fill in via env or injection
    decision = client.fetch_signal(candles[-50:])
    trade = clamp_decision(decision, equity_fraction_cap=0.5)
    price = candles[-1]["close"]
    direction = 1 if trade.side == "long" else -1 if trade.side == "short" else 0
    size = trade.position_fraction
    sl = trade.stop_loss_pct
    tp = trade.take_profit_pct
    # Toy calc: risk per unit based on stop distance
    if direction == 0 or sl <= 0:
        print("No trade or invalid stop; skipping backtest")
        return
    risk_per_unit = price * (sl / 100)
    capital_risked = size * risk_per_unit
    reward_per_unit = price * (tp / 100)
    r_multiple = reward_per_unit / risk_per_unit if risk_per_unit else math.inf
    print({"direction": direction, "size_frac": size, "r_multiple": r_multiple, "capital_risked": capital_risked})


if __name__ == "__main__":
    simple_backtest()
