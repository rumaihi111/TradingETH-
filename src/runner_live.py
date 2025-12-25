import time
from typing import Dict

import ccxt

from ai_client import AISignalClient
from config import load_settings
from exchange_hyperliquid import HyperliquidClient
from exchange_paper import PaperExchange
from history_store import HistoryStore
from trade_logger import TradeLogger
from risk import FrequencyGuard, clamp_decision


def run_live():
    settings = load_settings()
    history = HistoryStore()
    trade_log = TradeLogger()
    ai = AISignalClient(api_key=settings.anthropic_api_key, history_store=history)
    use_paper = settings.paper_mode
    if use_paper:
        ex = PaperExchange(starting_equity=settings.paper_initial_equity)
    else:
        ex = HyperliquidClient(
            private_key_hex=settings.private_key,
            testnet=settings.hyperliquid_testnet,
            base_url_override=settings.hyperliquid_base_url,
        )
    guard = FrequencyGuard(settings.max_trades_per_hour, settings.cooldown_minutes)
    spot = ccxt.binance()

    while True:
        if not guard.allow_new_trade():
            time.sleep(10)
            continue

        # Fetch latest 5m candles for Claude analysis
        ohlcv = spot.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=50)
        candles = [{"ts": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]} for c in ohlcv]
        price = candles[-1]["close"]
        decision_raw: Dict = ai.fetch_signal(candles)
        trade = clamp_decision(decision_raw, settings.max_position_fraction)

        if trade.side == "flat" or trade.position_fraction <= 0:
            time.sleep(10)
            continue

        # TODO: fetch live price; placeholder uses position fraction as size
        size = trade.position_fraction
        if use_paper:
            result = ex.place_market(settings.trading_pair, trade.side, size, trade.max_slippage_pct, price=price)
        else:
            result = ex.place_market(settings.trading_pair, trade.side, size, trade.max_slippage_pct)
        trade_log.log_trade({"decision": trade.model_dump(), "result": result, "price": price})
        guard.record_open()
        print(f"Trade placed: {trade.side} {size} @ {price}, result={result}")

        # TODO: monitor position and exit by stop/TP or signal
        time.sleep(settings.cooldown_minutes * 60)
        guard.record_close()


if __name__ == "__main__":
    run_live()
