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
        
        # Check for liquidation in paper mode
        if use_paper and hasattr(ex, 'check_liquidation'):
            if ex.check_liquidation(price):
                print("💥 Position liquidated due to excessive loss")
                time.sleep(300)  # Wait 5 minutes before next trade
                continue
        
        # Show current wallet balance and P&L
        account = ex.account()
        equity = account.get("equity", 0)
        open_positions = ex.positions()
        
        # Calculate unrealized P&L from open position
        unrealized_pnl = 0
        position_value = 0
        if open_positions:
            pos = open_positions[0]
            pos_size = pos.get("size", 0)
            entry_price = pos.get("entry", 0)
            if pos_size != 0 and entry_price != 0:
                position_value = abs(pos_size) * price
                unrealized_pnl = (price - entry_price) * pos_size
        
        pnl.print_balance_sheet(equity, unrealized_pnl, position_value)
        
        decision_raw: Dict = ai.fetch_signal(candles)
        trade = clamp_decision(decision_raw, settings.max_position_fraction)

        # Determine current position state
        current_pos = open_positions[0] if open_positions else None
        current_side = None
        if current_pos:
            size = current_pos.get("size", 0)
            if size > 0:
                current_side = "long"
            elif size < 0:
                current_side = "short"

        # Decision logic: close/flip/hold/open based on signal
        if trade.side == "flat":
            if current_pos:
                # Claude wants to close position
                ohlcv_close = spot.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=1)
                close_price = ohlcv_close[0][4]
                if use_paper:
                    close_result = ex.close_position(settings.trading_pair, price=close_price)
                else:
                    close_result = ex.close_position(settings.trading_pair)
                
                # Record P&L
                if "pnl" in close_result:
                    pnl.record_trade("close", abs(current_pos.get("size", 0)), current_pos.get("entry", 0), close_price, close_result["pnl"])
                
                trade_log.log_trade({"decision": {"side": "close"}, "result": close_result, "price": close_price})
                print(f"Signal: flat → Position closed @ {close_price}, result={close_result}")
                guard.record_close()
            else:
                print(f"Signal: flat → No position, staying flat")
            # Wait 5 minutes before next query
            time.sleep(300)
            continue

        if trade.position_fraction <= 0:
            print(f"Signal: {trade.side} with 0 size → Ignoring")
            time.sleep(300)
            continue

        # Check if we need to flip or can hold existing position
        if current_pos and current_side == trade.side:
            print(f"Signal: {trade.side} → Already in {current_side} position, holding")
            # Wait longer when holding to avoid rate limits (5 minutes)
            time.sleep(300)
            continue

        # Close opposite position before opening new
        if current_pos and current_side != trade.side:
            ohlcv_close = spot.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=1)
            close_price = ohlcv_close[0][4]
            if use_paper:
                close_result = ex.close_position(settings.trading_pair, price=close_price)
            else:
                close_result = ex.close_position(settings.trading_pair)
            
            # Record P&L
            if "pnl" in close_result:
                pnl.record_trade("close", abs(current_pos.get("size", 0)), current_pos.get("entry", 0), close_price, close_result["pnl"])
            
            trade_log.log_trade({"decision": {"side": "close"}, "result": close_result, "price": close_price})
            print(f"Signal: {trade.side} → Closed {current_side} position @ {close_price} (flipping)")
            guard.record_close()
            time.sleep(5)

        # Open new position - calculate actual size from position_fraction
        notional_value = equity * trade.position_fraction  # USD to allocate
        size = notional_value / price  # Convert to ETH amount
        
        if use_paper:
            result = ex.place_market(settings.trading_pair, trade.side, size, trade.max_slippage_pct, price=price)
        else:
            result = ex.place_market(settings.trading_pair, trade.side, size, trade.max_slippage_pct)
        
        # Record trade open
        pnl.record_trade("open", size, price)
        
        trade_log.log_trade({"decision": trade.model_dump(), "result": result, "price": price})
        guard.record_open()
        print(f"Trade placed: {trade.side} {size:.4f} ETH (${notional_value:.2f}) @ ${price:.2f}, result={result}")

        # Wait cooldown before next signal
        time.sleep(settings.cooldown_minutes * 60)


if __name__ == "__main__":
    run_live()
