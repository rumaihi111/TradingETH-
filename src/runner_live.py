import time
from typing import Dict

import ccxt

from .ai_client import AISignalClient
from .config import load_settings
from .exchange_hyperliquid import HyperliquidClient
from .exchange_paper import PaperExchange
from .history_store import HistoryStore
from .trade_logger import TradeLogger
from .pnl_tracker import PnLTracker
from .risk import FrequencyGuard, clamp_decision


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
    
    # Initialize P&L tracker with current wallet equity as baseline
    current_equity = ex.account().get("equity", settings.paper_initial_equity)
    pnl = PnLTracker(current_equity=current_equity)
    
    guard = FrequencyGuard(settings.max_trades_per_hour, settings.cooldown_minutes)
    spot = ccxt.kucoin()

    while True:
        if not guard.allow_new_trade():
            time.sleep(10)
            continue

        # Fetch latest 5m candles for Claude analysis
        ohlcv = spot.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=50)
        candles = [{"ts": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]} for c in ohlcv]
        price = candles[-1]["close"]
        
        # Show current wallet balance and P&L
        account = ex.account()
        equity = account.get("equity", 0)
        open_positions = ex.positions()
        pnl.print_balance_sheet(equity)
        
        decision_raw: Dict = ai.fetch_signal(candles)
        trade = clamp_decision(decision_raw, settings.max_position_fraction)

        # Check if we have an open position to close
        if open_positions and trade.side == "flat":
            # Claude wants to close position
            ohlcv_close = spot.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=1)
            close_price = ohlcv_close[0][4]  # current close
            pos = open_positions[0]
            if use_paper:
                close_result = ex.close_position(settings.trading_pair, price=close_price)
            else:
                close_result = ex.close_position(settings.trading_pair)
            
            # Record P&L
            if "pnl" in close_result:
                pnl.record_trade("close", abs(pos.get("size", 0)), pos.get("entry", 0), close_price, close_result["pnl"])
            
            trade_log.log_trade({"decision": {"side": "close"}, "result": close_result, "price": close_price})
            print(f"Position closed @ {close_price}, result={close_result}")
            guard.record_close()
            time.sleep(10)
            continue

        if trade.side == "flat" or trade.position_fraction <= 0:
            time.sleep(10)
            continue

        # Close any existing position before opening new one (max 1 position rule)
        if open_positions:
            ohlcv_close = spot.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=1)
            close_price = ohlcv_close[0][4]
            pos = open_positions[0]
            if use_paper:
                close_result = ex.close_position(settings.trading_pair, price=close_price)
            else:
                close_result = ex.close_position(settings.trading_pair)
            
            # Record P&L
            if "pnl" in close_result:
                pnl.record_trade("close", abs(pos.get("size", 0)), pos.get("entry", 0), close_price, close_result["pnl"])
            
            trade_log.log_trade({"decision": {"side": "close"}, "result": close_result, "price": close_price})
            print(f"Position closed @ {close_price} before opening new, result={close_result}")
            guard.record_close()
            time.sleep(5)

        # Open new position
        size = trade.position_fraction
        if use_paper:
            result = ex.place_market(settings.trading_pair, trade.side, size, trade.max_slippage_pct, price=price)
        else:
            result = ex.place_market(settings.trading_pair, trade.side, size, trade.max_slippage_pct)
        
        # Record trade open
        pnl.record_trade("open", size, price)
        
        trade_log.log_trade({"decision": trade.model_dump(), "result": result, "price": price})
        guard.record_open()
        print(f"Trade placed: {trade.side} {size} @ {price}, result={result}")

        # Wait cooldown before next signal
        time.sleep(settings.cooldown_minutes * 60)


if __name__ == "__main__":
    run_live()
