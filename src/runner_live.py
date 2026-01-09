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
from .rsi_engine import RSITradingEngine  # New RSI-only engine


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
    rsi_engine = RSITradingEngine()  # Initialize RSI trading engine
    spot = ccxt.kucoin()
    rate_limit_backoff = 60  # Start with 60 second backoff on rate limit

    while True:
        try:
            # Fetch latest 5m candles for analysis
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
        
        # Calculate unrealized P&L from open position
        unrealized_pnl = 0
        current_pos = open_positions[0] if open_positions else None
        current_side = None
        
        if current_pos:
            pos_size = current_pos.get("size", 0)
            entry_price = current_pos.get("entry", 0)
            if pos_size != 0 and entry_price != 0:
                unrealized_pnl = (price - entry_price) * pos_size
                current_side = "long" if pos_size > 0 else "short"
        
        # Log position status
        if current_pos and abs(current_pos.get("size", 0)) > 0.0001:
            side_display = "LONG" if current_pos.get("size", 0) > 0 else "SHORT"
            print(f"📍 Position: {side_display} {abs(current_pos.get('size', 0)):.4f} ETH @ ${current_pos.get('entry', 0):.2f}")
            print(f"💰 Unrealized P&L: ${unrealized_pnl:+.2f}")
        
        # Check for liquidation in paper mode
        if use_paper and hasattr(ex, 'check_liquidation'):
            if ex.check_liquidation(price):
                print("💥 Position liquidated due to excessive loss")
                await asyncio.sleep(300)
                continue
        
        # Pass position object to balance sheet
        pnl.print_balance_sheet(equity, unrealized_pnl, current_pos)
        
        # ========== RSI-ONLY TRADING LOGIC ==========
        # Get RSI decision - this is the ONLY indicator we use
        rsi_decision = rsi_engine.make_decision(candles, current_pos, unrealized_pnl)
        
        print("\n" + "="*80)
        print(f"📊 RSI DECISION ENGINE:")
        print(f"   RSI Value: {rsi_decision.rsi_value:.2f}")
        print(f"   Action: {rsi_decision.action.upper()}")
        print(f"   Reason: {rsi_decision.reason}")
        print(f"   Confidence: {rsi_decision.confidence:.1%}")
        print("="*80 + "\n")
        
        # Send RSI status to Telegram periodically
        if telegram_bot and current_pos:
            await telegram_bot.notify_rsi_status(
                rsi_decision.rsi_value,
                rsi_engine.get_zone(rsi_decision.rsi_value),
                current_side,
                unrealized_pnl
            )
        
        # ========== EXECUTE BASED ON RSI DECISION ==========
        
        # 1. WAIT - No action, just monitor
        if rsi_decision.action == "wait":
            print(f"⏸️  RSI in no-entry zone, waiting for extreme...")
            await asyncio.sleep(60)  # Check again in 1 minute
            continue
        
        # 2. HOLD - Keep current position, don't close
        if rsi_decision.action == "hold":
            print(f"✊ HOLDING position - RSI: {rsi_decision.rsi_value:.2f}")
            print(f"   Let stop loss and take profit orders work")
            await asyncio.sleep(60)  # Check again in 1 minute
            continue
        
        # 3. CLOSE_PROFIT - Close position because RSI hit exit zone AND we're in profit
        if rsi_decision.action == "close_profit":
            if current_pos:
                print(f"💰 CLOSING FOR PROFIT - RSI at exit zone + profit")
                ohlcv_close = spot.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=1)
                close_price = ohlcv_close[0][4]
                
                if use_paper:
                    close_result = ex.close_position(settings.trading_pair, price=close_price)
                else:
                    close_result = ex.close_position(settings.trading_pair)
                
                pnl_value = close_result.get("pnl", unrealized_pnl)
                pnl.record_trade("close", abs(current_pos.get("size", 0)), current_pos.get("entry", 0), close_price, pnl_value)
                
                if telegram_bot:
                    await telegram_bot.notify_trade_closed(
                        current_side,
                        abs(current_pos.get("size", 0)),
                        current_pos.get("entry", 0),
                        close_price,
                        pnl_value
                    )
                    await telegram_bot.notify_neutral()
                
                trade_log.log_trade({"decision": {"side": "close", "reason": rsi_decision.reason}, "result": close_result, "price": close_price})
                print(f"✅ Position closed @ ${close_price:.2f} | P&L: ${pnl_value:+.2f}")
                guard.record_close()
            
            await asyncio.sleep(300)  # Wait 5 min before next trade
            continue
        
        # 4. CLOSE_FLIP - Close current position and open opposite
        if rsi_decision.action == "close_flip":
            if current_pos:
                print(f"🔄 FLIPPING POSITION - RSI moved to opposite extreme")
                ohlcv_close = spot.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=1)
                close_price = ohlcv_close[0][4]
                
                if use_paper:
                    close_result = ex.close_position(settings.trading_pair, price=close_price)
                else:
                    close_result = ex.close_position(settings.trading_pair)
                
                pnl_value = close_result.get("pnl", unrealized_pnl)
                pnl.record_trade("close", abs(current_pos.get("size", 0)), current_pos.get("entry", 0), close_price, pnl_value)
                
                if telegram_bot:
                    await telegram_bot.notify_trade_closed(
                        current_side,
                        abs(current_pos.get("size", 0)),
                        current_pos.get("entry", 0),
                        close_price,
                        pnl_value
                    )
                
                trade_log.log_trade({"decision": {"side": "close_flip"}, "result": close_result, "price": close_price})
                print(f"✅ Closed {current_side.upper()} @ ${close_price:.2f} | P&L: ${pnl_value:+.2f}")
                guard.record_close()
                await asyncio.sleep(2)  # Brief pause before opening new position
        
        # Check cooldown for new entries
        if not guard.allow_new_trade():
            print(f"⏸️  Cooldown active, waiting...")
            await asyncio.sleep(60)
            continue
        
        # 5. OPEN_LONG or OPEN_SHORT - Open new position
        if rsi_decision.action in ["open_long", "open_short", "close_flip"]:
            new_side = "long" if rsi_decision.action == "open_long" or (rsi_decision.action == "close_flip" and current_side == "short") else "short"
            if rsi_decision.action == "close_flip":
                new_side = "short" if current_side == "long" else "long"
            
            # Position sizing - 80% of wallet at 10x leverage
            notional_value = equity * settings.max_position_fraction
            
            if notional_value < 11:
                print(f"⚠️ Position size ${notional_value:.2f} below minimum ($11), increasing")
                notional_value = 11
            
            size = notional_value / price
            
            print(f"📈 OPENING {new_side.upper()} - RSI: {rsi_decision.rsi_value:.2f}")
            print(f"💰 Size: {size:.4f} ETH (${notional_value:.2f})")
            
            if use_paper:
                result = ex.place_market(settings.trading_pair, new_side, size, 0.5, price=price)
            else:
                result = ex.place_market(settings.trading_pair, new_side, size, 0.5)
            
            # Verify position
            position_found = False
            for attempt in range(5):
                await asyncio.sleep(1)
                verification = ex.positions()
                if verification and abs(verification[0].get('size', 0)) >= size * 0.9:
                    verified_pos = verification[0]
                    print(f"✅ Position verified: {new_side.upper()} {abs(verified_pos.get('size', 0)):.4f} ETH @ ${verified_pos.get('entry', price):.2f}")
                    position_found = True
                    break
            
            if not position_found:
                print(f"⚠️ Position verification failed")
            
            # Record and notify
            pnl.record_trade("open", size, price)
            
            # Calculate SL/TP based on RSI decision
            stop_loss_pct = rsi_decision.stop_loss_pct
            take_profit_pct = rsi_decision.take_profit_pct
            
            if new_side == "long":
                stop_loss_price = price * (1 - stop_loss_pct)
                take_profit_price = price * (1 + take_profit_pct)
            else:
                stop_loss_price = price * (1 + stop_loss_pct)
                take_profit_price = price * (1 - take_profit_pct)
            
            if telegram_bot:
                await telegram_bot.notify_trade_opened_rsi(
                    new_side, size, price,
                    rsi_value=rsi_decision.rsi_value,
                    stop_loss=stop_loss_price,
                    take_profit=take_profit_price,
                    leverage=10
                )
            
            trade_log.log_trade({"decision": {"side": new_side, "rsi": rsi_decision.rsi_value}, "result": result, "price": price})
            guard.record_open()
            
            # Place SL/TP orders on exchange
            if not use_paper and position_found:
                print(f"\n🛡️ Setting risk management...")
                entry_price = verified_pos.get('entry', price)
                actual_size = abs(verified_pos.get('size', size))
                
                # Stop Loss
                if new_side == "long":
                    stop_price = entry_price * (1 - stop_loss_pct)
                    stop_side = "sell"
                else:
                    stop_price = entry_price * (1 + stop_loss_pct)
                    stop_side = "buy"
                
                ex.place_trigger_order(
                    symbol=settings.trading_pair, side=stop_side, size=actual_size,
                    trigger_price=stop_price, is_stop=True, reduce_only=True
                )
                print(f"🛡️ Stop Loss: ${stop_price:.2f}")
                
                # Take Profit
                if new_side == "long":
                    tp_price = entry_price * (1 + take_profit_pct)
                    tp_side = "sell"
                else:
                    tp_price = entry_price * (1 - take_profit_pct)
                    tp_side = "buy"
                
                ex.place_trigger_order(
                    symbol=settings.trading_pair, side=tp_side, size=actual_size,
                    trigger_price=tp_price, is_stop=False, reduce_only=True
                )
                print(f"🎯 Take Profit: ${tp_price:.2f}")
        
        # Wait before next cycle (minimum 60 seconds between checks)
        await asyncio.sleep(60)


def run_live():
    """Entry point that runs the async trading loop"""
    asyncio.run(run_live_async())


if __name__ == "__main__":
    run_live()
