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
from .rsi_brain import RSIBrain


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
    
    # Initialize RSI Brain (second brain / hive mind)
    rsi_brain = RSIBrain(rsi_period=14)
    print("🧠 RSI Brain initialized (RSI-14 on 5m chart)")

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
        
        # Determine current position state FIRST (needed for RSI brain)
        current_pos = open_positions[0] if open_positions else None
        current_side = None
        if current_pos:
            size = current_pos.get("size", 0)
            if size > 0:
                current_side = "long"
            elif size < 0:
                current_side = "short"
        
        # ═══════════════════════════════════════════════════════════════
        # 🧠 RSI BRAIN CHECK - Run BEFORE Claude to check for exit signals
        # ═══════════════════════════════════════════════════════════════
        rsi_analysis = rsi_brain.full_analysis(candles, current_side, None, unrealized_pnl)
        rsi_brain.print_analysis(rsi_analysis)
        
        # Check if RSI brain wants to exit current position (ONLY IF IN PROFIT at 50.44)
        if current_pos and rsi_analysis.should_exit:
            print(f"🧠 RSI Brain EXIT SIGNAL: {rsi_analysis.exit_reason}")
            ohlcv_close = spot.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=1)
            close_price = ohlcv_close[0][4]
            if use_paper:
                close_result = ex.close_position(settings.trading_pair, price=close_price)
            else:
                close_result = ex.close_position(settings.trading_pair)
            
            # Record P&L
            pnl_value = close_result.get("pnl", 0)
            if pnl_value == 0:
                entry = current_pos.get("entry", 0)
                size = abs(current_pos.get("size", 0))
                if current_side == "long":
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
                    pnl_value,
                    reason=f"RSI Exit ({rsi_analysis.rsi_value:.2f})"
                )
                await telegram_bot.notify_neutral()
            
            trade_log.log_trade({"decision": {"side": "close", "reason": "RSI brain exit"}, "result": close_result, "price": close_price})
            print(f"🧠 RSI Brain closed {current_side} position @ ${close_price:.2f} (P&L: ${pnl_value:+.2f})")
            guard.record_close()
            await asyncio.sleep(300)  # Wait 5 minutes after RSI-triggered exit
            continue
        
        # Check if we should query Claude (respect cooldown)
        if not guard.allow_new_trade():
            print(f"⏸️  Cooldown active, waiting...")
            await asyncio.sleep(60)  # Check again in 1 minute
            continue
        
        decision_raw: Dict = ai.fetch_signal(candles)
        trade = clamp_decision(decision_raw, settings.max_position_fraction)

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

        # ═══════════════════════════════════════════════════════════════
        # 🧠 RSI BRAIN ENTRY CHECK - Validate Claude's decision before opening
        # ═══════════════════════════════════════════════════════════════
        rsi_entry_check = rsi_brain.full_analysis(candles, None, trade.side)
        
        if not rsi_entry_check.should_enter:
            print(f"🧠 RSI Brain BLOCKED entry: {trade.side}")
            for note in rsi_entry_check.analysis_notes:
                if "🚫" in note or "blocked" in note.lower():
                    print(f"   {note}")
            print(f"⏸️  Waiting for better RSI conditions...")
            await asyncio.sleep(300)  # Wait 5 minutes and re-evaluate
            continue
        else:
            print(f"🧠 RSI Brain APPROVED {trade.side} entry (RSI: {rsi_entry_check.rsi_value:.1f}, Confidence: {rsi_entry_check.confidence*100:.0f}%)")

        # Open new position - 80% of wallet as MARGIN, with 10x leverage
        # Example: $100 wallet → $80 margin → $800 position value
        margin_amount = equity * settings.max_position_fraction  # 80% of wallet = margin
        position_value = margin_amount * 10  # 10x leverage = position value
        
        print(f"💰 MARGIN CALCULATION:")
        print(f"   Wallet Equity: ${equity:.2f}")
        print(f"   Margin Used (80%): ${margin_amount:.2f}")
        print(f"   Leverage: 10x")
        print(f"   Position Value: ${position_value:.2f}")
        
        # Hyperliquid requires minimum $10 order value, use $11 to be safe
        if margin_amount < 11:
            print(f"⚠️ Margin ${margin_amount:.2f} below minimum ($11), increasing to $11")
            margin_amount = 11
            position_value = margin_amount * 10
        
        # Size in ETH based on position value (not margin)
        size = position_value / price  # This is the leveraged size
        notional_value = margin_amount  # Keep for compatibility
        
        print(f"   ETH Size: {size:.4f} (${position_value:.2f} / ${price:.2f})")
        
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
        
        # ═══════════════════════════════════════════════════════════════
        # 🧠 RSI BRAIN - Calculate SL/TP using market analysis
        # ═══════════════════════════════════════════════════════════════
        sl_pct, tp_pct, sl_reason = rsi_brain.calculate_stop_loss(candles, trade.side, price)
        
        # Calculate actual SL/TP prices
        if trade.side.lower() == "long":
            stop_price = price * (1 - sl_pct)
            tp_price = price * (1 + tp_pct)
        else:  # short
            stop_price = price * (1 + sl_pct)
            tp_price = price * (1 - tp_pct)
        
        print(f"🧠 RSI Brain SL/TP: {sl_reason}")
        print(f"   Stop Loss: ${stop_price:.2f} ({sl_pct*100:.2f}%)")
        print(f"   Take Profit: ${tp_price:.2f} ({tp_pct*100:.2f}%)")
        
        # Send Telegram notification with SL/TP
        if telegram_bot:
            await telegram_bot.notify_trade_opened(
                side=trade.side, 
                size=size, 
                price=price,
                stop_loss_price=stop_price,
                take_profit_price=tp_price,
                leverage=10,
                margin_used=notional_value
            )
        
        trade_log.log_trade({"decision": trade.model_dump(), "result": result, "price": price, "sl": stop_price, "tp": tp_price})
        guard.record_open()
        print(f"Trade placed: {trade.side} {size:.4f} ETH (${notional_value:.2f} margin, ${notional_value*10:.2f} position) @ ${price:.2f}")
        
        # Place stop loss and take profit orders using RSI brain calculated values
        if not use_paper and position_found:
            print(f"\n🛡️ Setting up risk management (SL: {sl_pct*100:.2f}%, TP: {tp_pct*100:.2f}%)")
            
            # Get actual entry price from verified position
            entry_price = verified_pos.get('entry_price', verified_pos.get('entry', price))
            actual_size = abs(verified_pos.get('size', size))
            
            # Recalculate with actual entry price
            if trade.side.lower() == "long":
                stop_price = entry_price * (1 - sl_pct)
                tp_price = entry_price * (1 + tp_pct)
                stop_side = "sell"
                tp_side = "sell"
            else:  # short
                stop_price = entry_price * (1 + sl_pct)
                tp_price = entry_price * (1 - tp_pct)
                stop_side = "buy"
                tp_side = "buy"
            
            # Place stop loss
            try:
                ex.place_trigger_order(
                    symbol=settings.trading_pair,
                    side=stop_side,
                    size=actual_size,
                    trigger_price=stop_price,
                    is_stop=True,
                    reduce_only=True
                )
                print(f"🛡️ Stop Loss: {stop_side.upper()} {actual_size:.4f} ETH @ ${stop_price:.2f} (-{sl_pct*100:.2f}% from ${entry_price:.2f})")
            except Exception as e:
                print(f"⚠️ Failed to place stop loss: {e}")
            
            # Place take profit
            try:
                ex.place_trigger_order(
                    symbol=settings.trading_pair,
                    side=tp_side,
                    size=actual_size,
                    trigger_price=tp_price,
                    is_stop=False,
                    reduce_only=True
                )
                print(f"🎯 Take Profit: {tp_side.upper()} {actual_size:.4f} ETH @ ${tp_price:.2f} (+{tp_pct*100:.2f}% from ${entry_price:.2f})")
            except Exception as e:
                print(f"⚠️ Failed to place take profit: {e}")
            
            print(f"✅ Risk management orders placed successfully\n")

        # Wait cooldown before next signal
        await asyncio.sleep(settings.cooldown_minutes * 60)


def run_live():
    """Entry point that runs the async trading loop"""
    asyncio.run(run_live_async())


if __name__ == "__main__":
    run_live()
