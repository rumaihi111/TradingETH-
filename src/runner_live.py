import time
import asyncio
from typing import Dict, Optional

import ccxt

from .ai_client import AISignalClient
from .config import load_settings
from .exchange_hyperliquid import HyperliquidClient
from .exchange_paper import PaperExchange
from .history_store import HistoryStore
from .trade_logger import TradeLogger
from .pnl_tracker import PnLTracker
from .risk import FrequencyGuard, clamp_decision
from .telegram_bot import TradingTelegramBot, schedule_daily_reports


telegram_bot: Optional[TradingTelegramBot] = None


async def run_live_async():
    global telegram_bot
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
            account_address=settings.account_address,
        )
    
    # Initialize P&L tracker with current wallet equity as baseline
    current_equity = ex.account().get("equity", settings.paper_initial_equity)
    pnl = PnLTracker(current_equity=current_equity)
    
    # Initialize Telegram bot if configured
    if settings.telegram_token and settings.telegram_chat_id:
        telegram_bot = TradingTelegramBot(
            telegram_token=settings.telegram_token,
            chat_id=settings.telegram_chat_id,
            hyperliquid_client=ex,
            pnl_tracker=pnl,
        )
        await telegram_bot.start()
        # Start daily report scheduler in background
        asyncio.create_task(schedule_daily_reports(telegram_bot))
        print("🤖 Telegram bot enabled")
    
    guard = FrequencyGuard(settings.max_trades_per_hour, settings.cooldown_minutes)
    spot = ccxt.kucoin()

    while True:
        # Fetch latest 5m candles for Claude analysis
        ohlcv = spot.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=50)
        candles = [{"ts": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]} for c in ohlcv]
        price = candles[-1]["close"]
        
        # Get current positions ONCE at start of loop
        account = ex.account()
        equity = account.get("equity", 0)
        open_positions = ex.positions()
        
        # Log position status
        if open_positions:
            pos = open_positions[0]
            side = "LONG" if pos.get("size", 0) > 0 else "SHORT"
            print(f"📍 Position: {side} {abs(pos.get('size', 0)):.4f} ETH @ ${pos.get('entry', 0):.2f}")
        
        # Check for liquidation in paper mode
        if use_paper and hasattr(ex, 'check_liquidation'):
            if ex.check_liquidation(price):
                print("💥 Position liquidated due to excessive loss")
                await asyncio.sleep(300)  # Wait 5 minutes before next trade
                continue
        
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
                print(f"💰 Unrealized P&L: ${unrealized_pnl:+.2f}")
        
        # Pass position object to balance sheet instead of position_value
        current_position = open_positions[0] if open_positions else None
        pnl.print_balance_sheet(equity, unrealized_pnl, current_position)
        
        # Check if we should query Claude (respect cooldown)
        if not guard.allow_new_trade():
            print(f"⏸️  Cooldown active, waiting...")
            await asyncio.sleep(60)  # Check again in 1 minute
            continue
        
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
                    # Send Telegram notification
                    if telegram_bot:
                        await telegram_bot.notify_trade_closed(
                            current_side,
                            abs(current_pos.get("size", 0)),
                            current_pos.get("entry", 0),
                            close_price,
                            close_result["pnl"]
                        )
                
                trade_log.log_trade({"decision": {"side": "close"}, "result": close_result, "price": close_price})
                print(f"Signal: flat → Position closed @ {close_price}, result={close_result}")
                guard.record_close()
                
                # Notify going neutral
                if telegram_bot:
                    await telegram_bot.notify_neutral()
            else:
                print(f"Signal: flat → No position, staying flat")
            # Wait 5 minutes before next query
            await asyncio.sleep(300)
            continue

        if trade.position_fraction <= 0:
            print(f"Signal: {trade.side} with 0 size → Ignoring")
            await asyncio.sleep(300)
            continue

        # Check if we need to flip or can hold existing position
        if current_pos and current_side == trade.side:
            print(f"Signal: {trade.side} → Already in {current_side} position, holding")
            # Wait longer when holding to avoid rate limits (5 minutes)
            await asyncio.sleep(300)
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
                # Send Telegram notification
                if telegram_bot:
                    await telegram_bot.notify_trade_closed(
                        current_side,
                        abs(current_pos.get("size", 0)),
                        current_pos.get("entry", 0),
                        close_price,
                        close_result["pnl"]
                    )
            
            trade_log.log_trade({"decision": {"side": "close"}, "result": close_result, "price": close_price})
            print(f"Signal: {trade.side} → Closed {current_side} position @ {close_price} (flipping)")
            guard.record_close()
            await asyncio.sleep(5)

        # Open new position - calculate actual size from position_fraction
        notional_value = equity * trade.position_fraction  # USD to allocate
        
        # Hyperliquid requires minimum $10 order value, use $11 to be safe
        if notional_value < 11:
            print(f"⚠️ Position size ${notional_value:.2f} below minimum ($11), increasing to $11")
            notional_value = 11
        
        size = notional_value / price  # Convert to ETH amount
        
        if use_paper:
            result = ex.place_market(settings.trading_pair, trade.side, size, trade.max_slippage_pct, price=price)
        else:
            result = ex.place_market(settings.trading_pair, trade.side, size, trade.max_slippage_pct)
        
        # Wait a moment for position to register on exchange
        await asyncio.sleep(2)
        
        # Verify position was opened
        verification = ex.positions()
        if verification:
            verified_pos = verification[0]
            print(f"✅ Position verified: {trade.side.upper()} {abs(verified_pos.get('size', 0)):.4f} ETH @ ${verified_pos.get('entry', 0):.2f}")
        else:
            print(f"⚠️ Warning: No position found after placing order. Result: {result}")
        
        # Record trade open
        pnl.record_trade("open", size, price)
        
        # Send Telegram notification for opened trade
        if telegram_bot:
            await telegram_bot.notify_trade_opened(trade.side, size, price)
        
        trade_log.log_trade({"decision": trade.model_dump(), "result": result, "price": price})
        guard.record_open()
        print(f"Trade placed: {trade.side} {size:.4f} ETH (${notional_value:.2f}) @ ${price:.2f}, result={result}")

        # Wait cooldown before next signal
        await asyncio.sleep(settings.cooldown_minutes * 60)


def run_live():
    """Entry point that runs the async trading loop"""
    asyncio.run(run_live_async())


if __name__ == "__main__":
    run_live()
