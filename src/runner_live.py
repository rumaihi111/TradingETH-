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
    rate_limit_backoff = 60  # Start with 60 second backoff on rate limit

    while True:
        try:
            # Fetch latest 5m candles for Claude analysis
            ohlcv = spot.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=50)
            candles = [{"ts": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]} for c in ohlcv]
            price = candles[-1]["close"]
            
            # Get current positions ONCE at start of loop
            account = ex.account()
            equity = account.get("equity", 0)
            open_positions = ex.positions()
            
            # Reset backoff on successful query
            rate_limit_backoff = 60
        
        except Exception as e:
            # Handle rate limit errors (429) from Hyperliquid
            error_str = str(e)
            if "429" in error_str or "rate" in error_str.lower():
                print(f"⚠️ Rate limit hit, backing off for {rate_limit_backoff}s...")
                await asyncio.sleep(rate_limit_backoff)
                rate_limit_backoff = min(rate_limit_backoff * 2, 600)  # Max 10 min backoff
                continue
            else:
                # Other errors - log and retry after 5 minutes
                print(f"❌ Error querying exchange: {e}")
                await asyncio.sleep(300)
                continue
        
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

        # Note: We IGNORE trade.position_fraction - always use settings.max_position_fraction (80%)
        # Claude's position_fraction is informational only

        # Check if we need to flip or can hold existing position
        if current_pos and current_side == trade.side:
            print(f"Signal: {trade.side} → Already in {current_side} position, holding")
            # Wait longer when holding to avoid rate limits (5 minutes)
            await asyncio.sleep(300)
            continue

        # Close opposite position before opening new
        if current_pos and current_side != trade.side:
            ohlcv_close = spot.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=1)
            market_price = ohlcv_close[0][4]
            if use_paper:
                close_result = ex.close_position(settings.trading_pair, price=market_price)
            else:
                close_result = ex.close_position(settings.trading_pair)
            
            # Get actual close price from result or use market price
            close_price = close_result.get("close_price") or market_price
            
            # Record P&L (use result PNL if available, otherwise calculate)
            pnl_value = close_result.get("pnl", 0)
            if pnl_value == 0:
                # Calculate manually if not provided
                entry = current_pos.get("entry", 0)
                size = abs(current_pos.get("size", 0))
                if current_side.lower() == "long":
                    pnl_value = (close_price - entry) * size
                else:
                    pnl_value = (entry - close_price) * size
            
            pnl.record_trade("close", abs(current_pos.get("size", 0)), current_pos.get("entry", 0), close_price, pnl_value)
            
            # Send Telegram notification
            if telegram_bot:
                await telegram_bot.notify_trade_closed(
                    current_side,
                    abs(current_pos.get("size", 0)),
                    current_pos.get("entry", 0),
                    close_price,
                    pnl_value
                )
            
            trade_log.log_trade({"decision": {"side": "close"}, "result": close_result, "price": close_price, "pnl": pnl_value})
            print(f"Signal: {trade.side} → Closed {current_side} position @ ${close_price:.2f} (P&L: ${pnl_value:+.2f})")
            guard.record_close()
            await asyncio.sleep(5)

        # Open new position - ALWAYS use max position fraction (ignore Claude's position_fraction)
        notional_value = equity * settings.max_position_fraction  # Always use 80% of wallet
        
        print(f"🔧 DEBUG: settings.max_position_fraction = {settings.max_position_fraction}")
        print(f"🔧 DEBUG: equity = ${equity:.2f}")
        print(f"🔧 DEBUG: notional_value = ${notional_value:.2f}")
        print(f"🔧 DEBUG: Claude's position_fraction (IGNORED) = {trade.position_fraction}")
        
        # Hyperliquid requires minimum $10 order value, use $11 to be safe
        if notional_value < 11:
            print(f"⚠️ Position size ${notional_value:.2f} below minimum ($11), increasing to $11")
            notional_value = 11
        
        size = notional_value / price  # Convert to ETH amount
        
        print(f"💰 Position sizing: ${notional_value:.2f} ({settings.max_position_fraction*100:.0f}% of ${equity:.2f})")
        
        if use_paper:
            result = ex.place_market(settings.trading_pair, trade.side, size, trade.max_slippage_pct, price=price)
        else:
            result = ex.place_market(settings.trading_pair, trade.side, size, trade.max_slippage_pct)
        
        # Wait up to 5 seconds for position to settle
        print("⏳ Waiting for position to settle...")
        position_found = False
        for attempt in range(5):
            await asyncio.sleep(1)
            verification = ex.positions()
            if verification and abs(verification[0].get('size', 0)) >= size * 0.9:
                verified_pos = verification[0]
                print(f"✅ Position verified: {trade.side.upper()} {abs(verified_pos.get('size', 0)):.4f} ETH @ ${verified_pos.get('entry_price', verified_pos.get('entry', 0)):.2f}")
                position_found = True
                break
        
        if not position_found:
            print(f"⚠️ Warning: Position not found after {attempt + 1} attempts. Result: {result}")
            print("⚠️ This could mean: order rejected, position too small, or immediate liquidation")
        
        # Record trade open
        pnl.record_trade("open", size, price)
        
        # Send Telegram notification for opened trade
        if telegram_bot:
            await telegram_bot.notify_trade_opened(trade.side, size, price)
        
        trade_log.log_trade({"decision": trade.model_dump(), "result": result, "price": price})
        guard.record_open()
        print(f"Trade placed: {trade.side} {size:.4f} ETH (${notional_value:.2f}) @ ${price:.2f}, result={result}")
        
        # Place stop loss and take profit if Claude provided them
        if not use_paper and position_found and (trade.stop_loss_pct > 0 or trade.take_profit_pct > 0):
            print(f"\n🛡️ Setting up risk management (SL: {trade.stop_loss_pct*100:.1f}%, TP: {trade.take_profit_pct*100:.1f}%)")
            
            # Get actual entry price from verified position
            entry_price = verified_pos.get('entry_price', verified_pos.get('entry', price))
            actual_size = abs(verified_pos.get('size', size))
            
            # Place stop loss
            if trade.stop_loss_pct > 0:
                if trade.side.lower() == "long":
                    stop_price = entry_price * (1 - trade.stop_loss_pct)
                    stop_side = "sell"
                else:  # short
                    stop_price = entry_price * (1 + trade.stop_loss_pct)
                    stop_side = "buy"
                
                ex.place_trigger_order(
                    symbol=settings.trading_pair,
                    side=stop_side,
                    size=actual_size,
                    trigger_price=stop_price,
                    is_stop=True,
                    reduce_only=True
                )
                print(f"🛡️ Stop Loss: {stop_side.upper()} {actual_size:.4f} ETH @ ${stop_price:.2f} (-{trade.stop_loss_pct*100:.1f}% from ${entry_price:.2f})")
            
            # Place take profit
            if trade.take_profit_pct > 0:
                if trade.side.lower() == "long":
                    tp_price = entry_price * (1 + trade.take_profit_pct)
                    tp_side = "sell"
                else:  # short
                    tp_price = entry_price * (1 - trade.take_profit_pct)
                    tp_side = "buy"
                
                ex.place_trigger_order(
                    symbol=settings.trading_pair,
                    side=tp_side,
                    size=actual_size,
                    trigger_price=tp_price,
                    is_stop=False,
                    reduce_only=True
                )
                print(f"🎯 Take Profit: {tp_side.upper()} {actual_size:.4f} ETH @ ${tp_price:.2f} (+{trade.take_profit_pct*100:.1f}% from ${entry_price:.2f})")
            
            print(f"✅ Risk management orders placed successfully\n")

        # Wait cooldown before next signal
        await asyncio.sleep(settings.cooldown_minutes * 60)


def run_live():
    """Entry point that runs the async trading loop"""
    asyncio.run(run_live_async())


if __name__ == "__main__":
    run_live()
