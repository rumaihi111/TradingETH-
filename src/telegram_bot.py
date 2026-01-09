import asyncio
import logging
from datetime import datetime
from typing import Optional

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes

from .config import Settings
from .exchange_hyperliquid import HyperliquidClient
from .pnl_tracker import PnLTracker
from .indicators import calculate_rsi

logger = logging.getLogger(__name__)


class TradingTelegramBot:
    def __init__(
        self,
        telegram_token: str,
        chat_id: str,
        hyperliquid_client: HyperliquidClient,
        pnl_tracker: PnLTracker,
    ):
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.hyperliquid = hyperliquid_client
        self.pnl_tracker = pnl_tracker
        self.app = Application.builder().token(telegram_token).build()
        
        # Register command handlers
        self.app.add_handler(CommandHandler("balance", self.cmd_balance))
        self.app.add_handler(CommandHandler("winrate", self.cmd_winrate))
        self.app.add_handler(CommandHandler("pnl", self.cmd_pnl))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("withdraw", self.cmd_withdraw))
        self.app.add_handler(CommandHandler("deposit", self.cmd_deposit))
        self.app.add_handler(CommandHandler("rsi", self.cmd_rsi))
        self.app.add_handler(CommandHandler("analysis", self.cmd_analysis))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("start", self.cmd_help))
        self.app.add_handler(CommandHandler("price", self.cmd_price))
        self.app.add_handler(CommandHandler("closetrade", self.cmd_close_trade))

    async def start(self):
        """Start the Telegram bot"""
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        # Set bot commands menu
        commands = [
            ("help", "Show all available commands"),
            ("balance", "Show wallet balance and positions"),
            ("rsi", "Show current RSI value and zone"),
            ("price", "Show current ETH price"),
            ("analysis", "Full market analysis"),
            ("winrate", "Show trading statistics and win rate"),
            ("pnl", "Show P&L report"),
            ("status", "Show bot status"),
            ("deposit", "Show deposit address"),
            ("withdraw", "Withdraw USDC (usage: /withdraw <amount> <address>)"),
            ("closetrade", "Manually close current position"),
        ]
        await self.app.bot.set_my_commands(commands)
        logger.info("🤖 Telegram bot started with commands")

    async def stop(self):
        """Stop the Telegram bot"""
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    async def send_message(self, text: str):
        """Send a message to the configured chat"""
        try:
            await self.app.bot.send_message(chat_id=self.chat_id, text=text)
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    # Command Handlers
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show all available commands"""
        message = """🤖 **ETH Trading Bot Commands**

📊 **Market Info:**
/rsi - Current RSI value and zone
/price - Current ETH price
/analysis - Full market analysis

💰 **Account:**
/balance - Wallet balance and positions
/pnl - P&L report
/winrate - Trading statistics
/status - Bot operational status

💳 **Transactions:**
/deposit - Show deposit address
/withdraw <amount> <address> - Withdraw USDC
/closetrade - Manually close position

📈 **RSI Strategy Thresholds:**
• SHORT Entry: RSI > 66.80
• LONG Entry: RSI < 35.28
• Exit Zone: RSI ~50.44
• No-Man Zone: 35.28 - 66.80

⚙️ **Settings:**
• Leverage: 10x
• Position Size: 80% margin
• Asset: ETH/USDC"""
        
        await update.message.reply_text(message, parse_mode='Markdown')

    async def cmd_rsi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current RSI value and trading zone"""
        try:
            # Get candles for RSI calculation
            candles = self.hyperliquid.candles(symbol="ETH", interval="5m", limit=50)
            
            if not candles or len(candles) < 20:
                await update.message.reply_text("❌ Not enough data for RSI calculation")
                return
            
            # Calculate RSI
            closes = [c['close'] for c in candles]
            rsi = calculate_rsi(closes, period=14)
            current_rsi = rsi[-1] if rsi else 50
            current_price = closes[-1]
            
            # Determine zone
            if current_rsi > 66.80:
                zone = "🔴 OVERBOUGHT"
                zone_desc = "SHORT Signal Zone"
                action = "📉 Consider opening SHORT"
            elif current_rsi < 35.28:
                zone = "🟢 OVERSOLD"
                zone_desc = "LONG Signal Zone"
                action = "📈 Consider opening LONG"
            elif 48 < current_rsi < 53:
                zone = "🟡 EXIT ZONE"
                zone_desc = "Take Profit Zone"
                action = "💰 Close position if in profit"
            else:
                zone = "⚪ NO-MAN ZONE"
                zone_desc = "Hold/Wait Zone"
                action = "⏳ Wait for signal"
            
            # Get current position
            positions = self.hyperliquid.positions()
            pos_info = ""
            if positions and abs(positions[0].get('size', 0)) > 0.0001:
                pos = positions[0]
                side = "LONG 📈" if pos['size'] > 0 else "SHORT 📉"
                unrealized = pos.get('unrealized_pnl', pos.get('unrealized', 0))
                pos_info = f"\n\n📊 **Current Position:** {side}\n💵 **Unrealized P&L:** ${unrealized:+.2f}"
            else:
                pos_info = "\n\n📊 **Position:** None"
            
            message = f"""📈 **RSI Analysis**

**RSI(14):** {current_rsi:.2f}
**Zone:** {zone}
**Status:** {zone_desc}
**Suggested:** {action}

**ETH Price:** ${current_price:.2f}

📊 **Thresholds:**
• Overbought (SHORT): > 66.80
• Oversold (LONG): < 35.28  
• Exit Zone: ~50.44
• No-Man: 35.28 - 66.80{pos_info}

🕐 {datetime.utcnow().strftime('%H:%M:%S UTC')}"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current ETH price"""
        try:
            candles = self.hyperliquid.candles(symbol="ETH", interval="5m", limit=10)
            
            if candles:
                current = candles[-1]
                price = current['close']
                open_price = current['open']
                high = current['high']
                low = current['low']
                
                change = price - open_price
                change_pct = (change / open_price) * 100 if open_price > 0 else 0
                emoji = "📈" if change >= 0 else "📉"
                
                message = f"""{emoji} **ETH Price**

**Current:** ${price:.2f}
**Change:** ${change:+.2f} ({change_pct:+.2f}%)
**High:** ${high:.2f}
**Low:** ${low:.2f}

🕐 {datetime.utcnow().strftime('%H:%M:%S UTC')}"""
                
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Could not fetch price data")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Full market analysis"""
        try:
            candles = self.hyperliquid.candles(symbol="ETH", interval="5m", limit=50)
            
            if not candles or len(candles) < 20:
                await update.message.reply_text("❌ Not enough data for analysis")
                return
            
            closes = [c['close'] for c in candles]
            highs = [c['high'] for c in candles]
            lows = [c['low'] for c in candles]
            
            # Calculate indicators
            rsi = calculate_rsi(closes, period=14)
            current_rsi = rsi[-1] if rsi else 50
            current_price = closes[-1]
            
            # Simple trend detection
            ema_20 = sum(closes[-20:]) / 20
            trend = "BULLISH 🟢" if current_price > ema_20 else "BEARISH 🔴"
            
            # Volatility (ATR-like)
            ranges = [h - l for h, l in zip(highs[-14:], lows[-14:])]
            avg_range = sum(ranges) / len(ranges)
            volatility_pct = (avg_range / current_price) * 100
            
            if volatility_pct > 2:
                vol_status = "HIGH 🔥"
            elif volatility_pct > 1:
                vol_status = "MEDIUM 📊"
            else:
                vol_status = "LOW 😴"
            
            # RSI zone
            if current_rsi > 66.80:
                rsi_zone = "OVERBOUGHT 🔴"
                rsi_signal = "SHORT opportunity"
            elif current_rsi < 35.28:
                rsi_zone = "OVERSOLD 🟢"
                rsi_signal = "LONG opportunity"
            elif 48 < current_rsi < 53:
                rsi_zone = "EXIT ZONE 🟡"
                rsi_signal = "Take profits"
            else:
                rsi_zone = "NO-MAN ZONE ⚪"
                rsi_signal = "Wait for signal"
            
            # 24h high/low
            high_24h = max(highs)
            low_24h = min(lows)
            
            # Get position info
            positions = self.hyperliquid.positions()
            pos_info = ""
            if positions and abs(positions[0].get('size', 0)) > 0.0001:
                pos = positions[0]
                side = "LONG 📈" if pos['size'] > 0 else "SHORT 📉"
                entry = pos.get('entry_price', pos.get('entry', 0))
                unrealized = pos.get('unrealized_pnl', pos.get('unrealized', 0))
                pos_info = f"""
📊 **CURRENT POSITION**
• Direction: {side}
• Entry: ${entry:.2f}
• Unrealized P&L: ${unrealized:+.2f}
"""
            
            message = f"""📊 **FULL MARKET ANALYSIS**

💰 **PRICE**
• Current: ${current_price:.2f}
• 24h High: ${high_24h:.2f}
• 24h Low: ${low_24h:.2f}
• EMA(20): ${ema_20:.2f}

📈 **TREND**
• Direction: {trend}
• Volatility: {vol_status} ({volatility_pct:.2f}%)

📉 **RSI ANALYSIS**
• RSI(14): {current_rsi:.2f}
• Zone: {rsi_zone}
• Signal: {rsi_signal}
{pos_info}
🕐 {datetime.utcnow().strftime('%H:%M:%S UTC')}"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_close_trade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually close current position"""
        try:
            positions = self.hyperliquid.positions()
            
            if not positions or abs(positions[0].get('size', 0)) < 0.0001:
                await update.message.reply_text("⚪ No open position to close")
                return
            
            pos = positions[0]
            size = pos['size']
            entry = pos.get('entry_price', pos.get('entry', 0))
            side = "LONG" if size > 0 else "SHORT"
            
            # Close the position
            close_side = "sell" if size > 0 else "buy"
            result = self.hyperliquid.market_order(
                symbol="ETH",
                side=close_side,
                size=abs(size),
                reduce_only=True
            )
            
            if result:
                fill_price = result.get('filled_price', result.get('price', entry))
                unrealized = pos.get('unrealized_pnl', pos.get('unrealized', 0))
                
                message = f"""✅ **POSITION CLOSED**

• Direction: {side}
• Size: {abs(size):.4f} ETH
• Entry: ${entry:.2f}
• Exit: ${fill_price:.2f}
• P&L: ${unrealized:+.2f}

⚠️ Position closed manually via Telegram

🕐 {datetime.utcnow().strftime('%H:%M:%S UTC')}"""
                
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Failed to close position")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current wallet balance and positions"""
        try:
            account = self.hyperliquid.account()
            equity = account.get("equity", 0)
            
            positions = self.hyperliquid.positions()
            
            message = f"💰 **Account Balance**\n\n"
            message += f"Equity: ${equity:.2f} USDC\n"
            
            if positions and abs(positions[0].get('size', 0)) > 0.0001:
                pos = positions[0]
                side = "LONG 📈" if pos['size'] > 0 else "SHORT 📉"
                size = abs(pos['size'])
                entry = pos.get('entry_price', pos.get('entry', 0))
                unrealized = pos.get('unrealized_pnl', pos.get('unrealized', 0))
                total_value = equity + unrealized
                
                message += f"\n**Open Position:**\n"
                message += f"• {side} {size:.4f} ETH\n"
                message += f"• Entry: ${entry:.2f}\n"
                message += f"• Unrealized P&L: ${unrealized:+.2f}\n"
                message += f"\n**Total Account Value:** ${total_value:.2f}"
            else:
                message += "\nNo open positions"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_winrate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show overall win rate and stats"""
        try:
            account = self.hyperliquid.account()
            current_equity = account.get("equity", 0)
            stats = self.pnl_tracker.get_stats(current_equity)
            
            total_trades = stats["total_closed_trades"]
            winners = stats["winning_trades"]
            losers = stats["losing_trades"]
            winrate = stats["win_rate"]
            
            message = f"📊 **Trading Statistics**\n\n"
            message += f"Total Trades: {total_trades}\n"
            message += f"Winners: {winners} ({winrate:.1f}%)\n"
            message += f"Losers: {losers}\n\n"
            message += f"Avg Win: ${stats['avg_win']:+.2f}\n"
            message += f"Avg Loss: ${stats['avg_loss']:+.2f}\n"
            message += f"Best Trade: ${stats['largest_win']:+.2f}\n"
            message += f"Worst Trade: ${stats['largest_loss']:+.2f}\n\n"
            message += f"Total P&L: ${stats['total_pnl']:+.2f} ({stats['total_pnl_pct']:+.2f}%)"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_pnl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current P&L report with percentage from initial investment"""
        try:
            account = self.hyperliquid.account()
            equity = account.get("equity", 0)
            
            # Get positions for unrealized P&L
            positions = self.hyperliquid.positions()
            unrealized_pnl = sum(p.get('unrealized_pnl', p.get('unrealized', 0)) for p in positions)
            
            # Get stats with current equity
            stats = self.pnl_tracker.get_stats(equity)
            
            # Calculate total account value including unrealized
            total_value = equity + unrealized_pnl
            total_pnl = stats['total_pnl'] + unrealized_pnl
            
            # Calculate percentage from initial investment
            initial = stats['starting_equity']
            pnl_pct = (total_pnl / initial * 100) if initial > 0 else 0
            
            message = f"💵 **P&L Report**\n\n"
            message += f"Initial Investment: ${initial:.2f}\n"
            message += f"Current Equity: ${equity:.2f}\n"
            
            if unrealized_pnl != 0:
                message += f"Unrealized P&L: ${unrealized_pnl:+.2f}\n"
                message += f"**Total Value: ${total_value:.2f}**\n\n"
            else:
                message += f"\n"
            
            message += f"**Total P&L: ${total_pnl:+.2f} ({pnl_pct:+.2f}%)**\n\n"
            message += f"Closed Trades: {stats['total_closed_trades']}\n"
            message += f"Win Rate: {stats['winning_trades']}/{stats['total_closed_trades']} ({stats['win_rate']:.1f}%)"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot status and current position"""
        try:
            account = self.hyperliquid.account()
            equity = account.get("equity", 0)
            positions = self.hyperliquid.positions()
            
            status = "🟢 **Bot Status: ACTIVE**\n\n"
            status += f"Balance: ${equity:.2f} USDC\n"
            
            if positions:
                pos = positions[0]
                side = "LONG 📈" if pos['size'] > 0 else "SHORT 📉"
                status += f"\n{side}\n"
                status += f"Size: {abs(pos['size']):.4f} ETH\n"
                status += f"Entry: ${pos['entry']:.2f}\n"
                status += f"Unrealized P&L: ${pos['unrealized']:.2f}"
            else:
                status += "\n⚪ Position: FLAT (No position)"
            
            await update.message.reply_text(status)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_withdraw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Withdraw USDC from Hyperliquid to external wallet
        Usage: /withdraw <amount> <address>
        """
        try:
            if not context.args or len(context.args) < 2:
                await update.message.reply_text(
                    "Usage: /withdraw <amount> <address>\n"
                    "Example: /withdraw 10 0x1234..."
                )
                return
            
            amount = float(context.args[0])
            address = context.args[1]
            
            # TODO: Implement Hyperliquid withdrawal
            # This requires using the exchange.usd_transfer() method
            await update.message.reply_text(
                f"⚠️ Withdrawal feature coming soon!\n"
                f"Amount: ${amount:.2f} USDC\n"
                f"To: {address[:10]}...{address[-8:]}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_deposit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show deposit address"""
        try:
            wallet_address = self.hyperliquid.wallet.address
            
            message = f"💳 **Deposit to API Wallet**\n\n"
            message += f"Address: `{wallet_address}`\n\n"
            message += f"⚠️ Send USDC on Arbitrum to this address\n"
            message += f"Then bridge to Hyperliquid at:\n"
            message += f"https://app.hyperliquid.xyz/bridge"
            
            await update.message.reply_text(message)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    # Notification Methods
    async def notify_trade_opened(self, side: str, size: float, price: float, stop_loss: float = None, take_profit: float = None, leverage: int = 10):
        """Send notification when trade is opened with stop loss and take profit details"""
        emoji = "📈" if side.lower() == "long" else "📉"
        notional_value = size * price
        margin_used = notional_value / leverage
        
        message = f"{emoji} **TRADE OPENED** {emoji}\n\n"
        message += f"**Direction:** {side.upper()}\n"
        message += f"**Entry Price:** ${price:.2f}\n"
        message += f"**Size:** {size:.4f} ETH\n"
        message += f"**Leverage:** {leverage}x\n"
        message += f"**Position Value:** ${notional_value:.2f}\n"
        message += f"**Margin Used:** ${margin_used:.2f}\n\n"
        
        # Add Stop Loss and Take Profit if provided
        if stop_loss:
            sl_distance = abs(price - stop_loss)
            sl_pct = (sl_distance / price) * 100
            message += f"🛑 **Stop Loss:** ${stop_loss:.2f}\n"
            message += f"   Distance: ${sl_distance:.2f} ({sl_pct:.2f}%)\n"
            message += f"   Max Loss: ${margin_used * (sl_pct/100) * leverage:.2f}\n\n"
        
        if take_profit:
            tp_distance = abs(take_profit - price)
            tp_pct = (tp_distance / price) * 100
            message += f"🎯 **Take Profit:** ${take_profit:.2f}\n"
            message += f"   Distance: ${tp_distance:.2f} ({tp_pct:.2f}%)\n"
            message += f"   Expected Profit: ${margin_used * (tp_pct/100) * leverage:.2f}\n\n"
        
        if stop_loss and take_profit:
            risk_reward = tp_distance / sl_distance if sl_distance > 0 else 0
            message += f"⚖️ **Risk/Reward:** 1:{risk_reward:.2f}\n\n"
        
        message += f"🕐 Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        message += f"_Target timeframe: 30-60 minutes_"
        
        await self.send_message(message)
    
    async def notify_position_update(self, side: str, size: float, entry: float, current_price: float, unrealized_pnl: float):
        """Send periodic position update with current P&L"""
        emoji = "📈" if side.lower() == "long" else "📉"
        pnl_emoji = "💚" if unrealized_pnl > 0 else "❤️" if unrealized_pnl < 0 else "💛"
        
        price_change = current_price - entry
        price_change_pct = (price_change / entry) * 100
        
        message = f"{emoji} **POSITION UPDATE** {pnl_emoji}\n\n"
        message += f"**Direction:** {side.upper()}\n"
        message += f"**Entry:** ${entry:.2f}\n"
        message += f"**Current:** ${current_price:.2f}\n"
        message += f"**Price Δ:** ${price_change:+.2f} ({price_change_pct:+.2f}%)\n\n"
        message += f"**Unrealized P&L:** ${unrealized_pnl:+.2f}\n"
        message += f"Time: {datetime.utcnow().strftime('%H:%M:%S UTC')}"
        
        await self.send_message(message)
    
    async def notify_signal_received(self, signal: str, rsi: float, confidence: float):
        """Notify when trading signal is received from AI"""
        emoji_map = {
            "long": "🟢",
            "short": "🔴",
            "flat": "⚪",
            "neutral": "⚪"
        }
        emoji = emoji_map.get(signal.lower(), "⚪")
        
        message = f"{emoji} **SIGNAL RECEIVED** {emoji}\n\n"
        message += f"**Direction:** {signal.upper()}\n"
        message += f"**RSI:** {rsi:.2f}\n"
        message += f"**Confidence:** {confidence:.1%}\n"
        message += f"Time: {datetime.utcnow().strftime('%H:%M:%S UTC')}"
        
        await self.send_message(message)

    async def notify_trade_closed(self, side: str, size: float, entry: float, exit_price: float, pnl: float):
        """Send notification when trade is closed with P&L"""
        emoji = "✅" if pnl > 0 else "❌"
        pnl_emoji = "💰" if pnl > 0 else "📉"
        
        # Calculate percentage P&L
        entry_value = abs(size) * entry
        pnl_pct = (pnl / entry_value * 100) if entry_value > 0 else 0
        
        message = f"{emoji} **TRADE CLOSED** {pnl_emoji}\n\n"
        message += f"Direction: {side.upper()}\n"
        message += f"Size: {abs(size):.4f} ETH\n"
        message += f"Entry: ${entry:.2f}\n"
        message += f"Exit: ${exit_price:.2f}\n"
        message += f"Price Change: ${exit_price - entry:+.2f} ({(exit_price/entry - 1)*100:+.2f}%)\n\n"
        message += f"**P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%)**\n\n"
        message += f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        await self.send_message(message)

    async def notify_neutral(self):
        """Send notification when bot goes neutral (flat)"""
        message = f"⚪ **POSITION FLAT**\n\n"
        message += f"Bot is now neutral (no position)\n"
        message += f"Waiting for next signal...\n"
        message += f"Time: {datetime.utcnow().strftime('%H:%M:%S UTC')}"
        await self.send_message(message)

    async def notify_rsi_status(self, rsi_value: float, zone: str, position_side: str = None, unrealized_pnl: float = None):
        """Send RSI status update with zone information
        
        Args:
            rsi_value: Current RSI value
            zone: One of 'overbought', 'oversold', 'exit_zone', 'no_man_zone'
            position_side: Current position ('long', 'short', or None)
            unrealized_pnl: Current unrealized P&L if in position
        """
        # Zone emojis and descriptions
        zone_info = {
            'overbought': ('🔴', 'OVERBOUGHT', 'Short Signal Zone'),
            'oversold': ('🟢', 'OVERSOLD', 'Long Signal Zone'),
            'exit_zone': ('🟡', 'EXIT ZONE', 'Take Profit Zone'),
            'no_man_zone': ('⚪', 'NO-MAN ZONE', 'Hold/Wait Zone')
        }
        
        emoji, zone_name, description = zone_info.get(zone, ('⚪', 'UNKNOWN', 'Unknown Zone'))
        
        message = f"{emoji} **RSI UPDATE** {emoji}\n\n"
        message += f"**RSI Value:** {rsi_value:.2f}\n"
        message += f"**Zone:** {zone_name}\n"
        message += f"**Status:** {description}\n\n"
        
        # Zone thresholds reminder
        message += f"📊 **Thresholds:**\n"
        message += f"   • Overbought (SHORT): > 66.80\n"
        message += f"   • Oversold (LONG): < 35.28\n"
        message += f"   • Exit Zone: ~50.44\n"
        message += f"   • No-Man Zone: 35.28 - 66.80\n\n"
        
        # Position info if available
        if position_side:
            pos_emoji = "📈" if position_side.lower() == "long" else "📉"
            message += f"{pos_emoji} **Current Position:** {position_side.upper()}\n"
            if unrealized_pnl is not None:
                pnl_emoji = "💚" if unrealized_pnl > 0 else "❤️"
                message += f"{pnl_emoji} **Unrealized P&L:** ${unrealized_pnl:+.2f}\n"
        else:
            message += f"🔲 **Position:** None (Waiting for signal)\n"
        
        message += f"\n🕐 Time: {datetime.utcnow().strftime('%H:%M:%S UTC')}"
        
        await self.send_message(message)

    async def notify_rsi_decision(self, decision: str, rsi_value: float, reason: str):
        """Notify about RSI-based trading decision
        
        Args:
            decision: The decision made (open_long, open_short, close_profit, close_flip, hold, wait)
            rsi_value: Current RSI value
            reason: Explanation for the decision
        """
        decision_info = {
            'open_long': ('🟢', 'OPENING LONG', 'RSI entered oversold zone'),
            'open_short': ('🔴', 'OPENING SHORT', 'RSI entered overbought zone'),
            'close_profit': ('💰', 'CLOSING IN PROFIT', 'RSI reached exit zone'),
            'close_flip': ('🔄', 'FLIPPING POSITION', 'RSI moved to opposite extreme'),
            'hold': ('✋', 'HOLDING POSITION', 'RSI in no-man zone'),
            'wait': ('⏳', 'WAITING', 'No position, RSI in no-man zone')
        }
        
        emoji, action_name, default_reason = decision_info.get(decision, ('❓', 'UNKNOWN', 'Unknown decision'))
        
        message = f"{emoji} **RSI DECISION** {emoji}\n\n"
        message += f"**Action:** {action_name}\n"
        message += f"**RSI:** {rsi_value:.2f}\n"
        message += f"**Reason:** {reason or default_reason}\n"
        message += f"🕐 Time: {datetime.utcnow().strftime('%H:%M:%S UTC')}"
        
        await self.send_message(message)

    async def notify_trade_opened_rsi(self, side: str, size: float, price: float, rsi_value: float, 
                                       stop_loss: float = None, take_profit: float = None, leverage: int = 10):
        """Send notification when trade is opened with RSI value included"""
        emoji = "📈" if side.lower() == "long" else "📉"
        rsi_emoji = "🟢" if side.lower() == "long" else "🔴"
        notional_value = size * price
        margin_used = notional_value / leverage
        
        message = f"{emoji} **TRADE OPENED** {emoji}\n\n"
        message += f"**Direction:** {side.upper()}\n"
        message += f"**Entry Price:** ${price:.2f}\n"
        message += f"**Size:** {size:.4f} ETH\n"
        message += f"**Leverage:** {leverage}x\n"
        message += f"**Position Value:** ${notional_value:.2f}\n"
        message += f"**Margin Used:** ${margin_used:.2f}\n\n"
        
        message += f"{rsi_emoji} **RSI Trigger:** {rsi_value:.2f}\n"
        if side.lower() == "long":
            message += f"   (Entered OVERSOLD zone < 35.28)\n\n"
        else:
            message += f"   (Entered OVERBOUGHT zone > 66.80)\n\n"
        
        # Add Stop Loss and Take Profit if provided
        if stop_loss:
            sl_distance = abs(price - stop_loss)
            sl_pct = (sl_distance / price) * 100
            message += f"🛑 **Stop Loss:** ${stop_loss:.2f}\n"
            message += f"   Distance: ${sl_distance:.2f} ({sl_pct:.2f}%)\n"
            message += f"   Max Loss: ${margin_used * (sl_pct/100) * leverage:.2f}\n\n"
        
        if take_profit:
            tp_distance = abs(take_profit - price)
            tp_pct = (tp_distance / price) * 100
            message += f"🎯 **Take Profit:** ${take_profit:.2f}\n"
            message += f"   Distance: ${tp_distance:.2f} ({tp_pct:.2f}%)\n"
            message += f"   Expected Profit: ${margin_used * (tp_pct/100) * leverage:.2f}\n\n"
        
        if stop_loss and take_profit:
            risk_reward = tp_distance / sl_distance if sl_distance > 0 else 0
            message += f"⚖️ **Risk/Reward:** 1:{risk_reward:.2f}\n\n"
        
        message += f"🕐 Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        message += f"_RSI-based strategy: Exit at RSI ~50.44 in profit_"
        
        await self.send_message(message)

    async def notify_error(self, error_msg: str, context: str = None):
        """Send error notification"""
        message = f"🚨 **ERROR** 🚨\n\n"
        message += f"**Error:** {error_msg}\n"
        if context:
            message += f"**Context:** {context}\n"
        message += f"🕐 Time: {datetime.utcnow().strftime('%H:%M:%S UTC')}"
        
        await self.send_message(message)

    async def notify_market_analysis(self, price: float, rsi: float, trend: str, volatility: str):
        """Send market analysis summary"""
        trend_emoji = {
            'bullish': '🟢📈',
            'bearish': '🔴📉',
            'sideways': '⚪↔️',
            'neutral': '⚪'
        }
        vol_emoji = {
            'high': '🔥',
            'medium': '📊',
            'low': '😴'
        }
        
        message = f"📊 **MARKET ANALYSIS** 📊\n\n"
        message += f"**ETH Price:** ${price:.2f}\n"
        message += f"**RSI(14):** {rsi:.2f}\n"
        message += f"**Trend:** {trend_emoji.get(trend.lower(), '⚪')} {trend.upper()}\n"
        message += f"**Volatility:** {vol_emoji.get(volatility.lower(), '📊')} {volatility.upper()}\n\n"
        
        # RSI interpretation
        if rsi > 66.80:
            message += f"⚠️ RSI OVERBOUGHT - Short opportunity\n"
        elif rsi < 35.28:
            message += f"⚠️ RSI OVERSOLD - Long opportunity\n"
        elif 48 < rsi < 53:
            message += f"🟡 RSI at exit zone - Take profits if in position\n"
        else:
            message += f"⏳ RSI in no-man zone - Wait for signal\n"
        
        message += f"\n🕐 Time: {datetime.utcnow().strftime('%H:%M:%S UTC')}"
        
        await self.send_message(message)

    async def send_daily_report(self):
        """Send daily P&L report"""
        try:
            account = self.hyperliquid.account()
            equity = account.get("equity", 0)
            stats = self.pnl_tracker.get_stats()
            
            message = f"📅 **Daily Report - {datetime.utcnow().strftime('%Y-%m-%d')}**\n\n"
            message += f"💰 Current Balance: ${equity:.2f} USDC\n"
            message += f"📊 Total P&L: ${stats['total_pnl']:.2f} ({stats['total_pnl_pct']:.2f}%)\n"
            message += f"📈 Trades Today: {stats['total_closed_trades']}\n"
            message += f"✅ Winners: {stats['winning_trades']}\n"
            message += f"❌ Losers: {stats['losing_trades']}\n"
            message += f"🎯 Win Rate: {stats['win_rate']:.1f}%\n"
            message += f"💵 Avg Win: ${stats['avg_win']:.2f}\n"
            message += f"💸 Avg Loss: ${stats['avg_loss']:.2f}"
            
            await self.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")


async def schedule_daily_reports(bot: TradingTelegramBot):
    """Schedule daily P&L reports every 24 hours"""
    while True:
        # Wait 24 hours
        await asyncio.sleep(24 * 60 * 60)
        await bot.send_daily_report()
