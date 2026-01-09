import asyncio
import logging
from datetime import datetime
from typing import Optional

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes

from .config import Settings
from .exchange_hyperliquid import HyperliquidClient
from .pnl_tracker import PnLTracker

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
        self.app.add_handler(CommandHandler("position", self.cmd_position))
        self.app.add_handler(CommandHandler("rsi", self.cmd_rsi))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("withdraw", self.cmd_withdraw))
        self.app.add_handler(CommandHandler("deposit", self.cmd_deposit))

    async def start(self):
        """Start the Telegram bot"""
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        # Set bot commands menu
        commands = [
            ("balance", "Show wallet balance and positions"),
            ("position", "Show current position details"),
            ("winrate", "Show trading statistics and win rate"),
            ("pnl", "Show P&L report"),
            ("status", "Show bot status"),
            ("rsi", "Show current RSI value and zone"),
            ("help", "Show all commands"),
            ("deposit", "Show deposit address"),
            ("withdraw", "Withdraw USDC (usage: /withdraw <amount> <address>)"),
        ]
        await self.app.bot.set_my_commands(commands)
        logger.info("🤖 Telegram bot started with commands")
        
        # Send startup notification
        await self.notify_startup()

    async def stop(self):
        """Stop the Telegram bot"""
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    async def send_message(self, text: str, parse_mode: str = 'Markdown'):
        """Send a message to the configured chat"""
        try:
            await self.app.bot.send_message(chat_id=self.chat_id, text=text, parse_mode=parse_mode)
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    async def notify_startup(self):
        """Send notification when bot starts/restarts"""
        try:
            account = self.hyperliquid.account()
            equity = account.get("equity", 0)
            positions = self.hyperliquid.positions()
            
            message = f"🚀 **BOT STARTED**\n\n"
            message += f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            message += f"💰 **Wallet:** ${equity:.2f} USDC\n"
            
            if positions and abs(positions[0].get('size', 0)) > 0.0001:
                pos = positions[0]
                side = "LONG 📈" if pos['size'] > 0 else "SHORT 📉"
                size = abs(pos['size'])
                entry = pos.get('entry_price', pos.get('entry', 0))
                message += f"\n📊 **Existing Position:**\n"
                message += f"• {side} {size:.4f} ETH @ ${entry:.2f}\n"
            else:
                message += f"\n📊 **Position:** None (flat)\n"
            
            message += f"\n🧠 **RSI Brain:** Active\n"
            message += f"• Long: RSI < 35.28\n"
            message += f"• Short: RSI > 66.80\n"
            message += f"• Exit: RSI = 50.44 (if profit)\n"
            message += f"\n✅ Bot is now monitoring..."
            
            await self.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")

    async def notify_error(self, error: str, context: str = ""):
        """Send notification when an error occurs"""
        message = f"⚠️ **BOT ERROR**\n\n"
        if context:
            message += f"**Context:** {context}\n"
        message += f"**Error:** {error}\n"
        message += f"🕐 {datetime.utcnow().strftime('%H:%M:%S UTC')}"
        await self.send_message(message)

    # Command Handlers
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

    async def cmd_position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed current position info"""
        try:
            positions = self.hyperliquid.positions()
            account = self.hyperliquid.account()
            equity = account.get("equity", 0)
            
            if not positions or abs(positions[0].get('size', 0)) < 0.0001:
                message = "⚪ **No Open Position**\n\n"
                message += f"💰 Available Balance: ${equity:.2f}\n"
                message += "🔍 Waiting for RSI entry signal..."
                await update.message.reply_text(message, parse_mode='Markdown')
                return
            
            pos = positions[0]
            side = "LONG 📈" if pos['size'] > 0 else "SHORT 📉"
            size = abs(pos['size'])
            entry = pos.get('entry_price', pos.get('entry', 0))
            unrealized = pos.get('unrealized_pnl', pos.get('unrealized', 0))
            
            # Calculate current price from unrealized P&L
            if pos['size'] > 0:  # Long
                current_price = entry + (unrealized / size) if size > 0 else entry
            else:  # Short
                current_price = entry - (unrealized / size) if size > 0 else entry
            
            position_value = size * current_price
            margin_used = position_value / 10  # 10x leverage
            pnl_pct = (unrealized / margin_used * 100) if margin_used > 0 else 0
            
            message = f"📊 **Current Position**\n\n"
            message += f"**Direction:** {side}\n"
            message += f"**Size:** {size:.4f} ETH\n"
            message += f"**Entry:** ${entry:.2f}\n"
            message += f"**Current:** ${current_price:.2f}\n"
            message += f"**Position Value:** ${position_value:.2f}\n"
            message += f"**Margin Used:** ${margin_used:.2f}\n\n"
            
            pnl_emoji = "🟢" if unrealized > 0 else "🔴"
            message += f"{pnl_emoji} **Unrealized P&L:** ${unrealized:+.2f} ({pnl_pct:+.2f}%)\n\n"
            message += f"💰 **Account Equity:** ${equity:.2f}"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_rsi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current RSI value and trading zone"""
        try:
            import ccxt
            from .rsi_brain import RSIBrain
            
            # Fetch candles
            spot = ccxt.kucoin()
            ohlcv = spot.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=50)
            candles = [{"ts": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]} for c in ohlcv]
            
            # Calculate RSI
            rsi_brain = RSIBrain(rsi_period=14)
            rsi = rsi_brain.calculate_rsi(candles)
            zone = rsi_brain.get_rsi_zone(rsi)
            
            # Determine zone emoji and description
            if rsi < 35.28:
                zone_emoji = "🟢"
                zone_desc = "LONG ZONE - Entry allowed for LONGS"
                action = "✅ Can enter LONG positions"
            elif rsi > 66.80:
                zone_emoji = "🔴"
                zone_desc = "SHORT ZONE - Entry allowed for SHORTS"
                action = "✅ Can enter SHORT positions"
            else:
                zone_emoji = "⚠️"
                zone_desc = "NO-MAN'S LAND - No entries allowed"
                action = "🚫 NO entries - exits only"
            
            price = candles[-1]["close"]
            
            message = f"📊 **RSI Analysis**\n\n"
            message += f"**RSI(14):** {rsi:.2f}\n"
            message += f"**Zone:** {zone_emoji} {zone_desc}\n\n"
            message += f"**Action:** {action}\n\n"
            message += f"**RSI Levels:**\n"
            message += f"• Long Entry: < 35.28\n"
            message += f"• Short Entry: > 66.80\n"
            message += f"• Take Profit: 50.44 (if in profit)\n\n"
            message += f"**ETH Price:** ${price:.2f}"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show all available commands"""
        message = f"🤖 **Trading Bot Commands**\n\n"
        message += f"/balance - 💰 Wallet balance & positions\n"
        message += f"/position - 📊 Detailed position info\n"
        message += f"/pnl - 💵 P&L report\n"
        message += f"/winrate - 📈 Trading statistics\n"
        message += f"/status - 🟢 Bot status\n"
        message += f"/rsi - 📉 Current RSI & zone\n"
        message += f"/deposit - 💳 Deposit address\n"
        message += f"/withdraw - 💸 Withdraw USDC\n\n"
        message += f"**RSI Trading Rules:**\n"
        message += f"• Long: RSI < 35.28\n"
        message += f"• Short: RSI > 66.80\n"
        message += f"• Exit: RSI = 50.44 (if profit)\n"
        message += f"• No trades: 35.28 - 66.80"
        
        await update.message.reply_text(message, parse_mode='Markdown')

    # Notification Methods
    async def notify_trade_opened(
        self, 
        side: str, 
        size: float, 
        price: float,
        stop_loss_price: float = None,
        take_profit_price: float = None,
        leverage: int = 10,
        margin_used: float = None
    ):
        """Send notification when trade is opened with SL/TP details"""
        emoji = "📈" if side.lower() == "long" else "📉"
        position_value = size * price * leverage
        margin = margin_used or (size * price)
        
        message = f"{emoji} **TRADE OPENED**\n\n"
        message += f"**Direction:** {side.upper()}\n"
        message += f"**Size:** {size:.4f} ETH\n"
        message += f"**Entry Price:** ${price:.2f}\n"
        message += f"**Leverage:** {leverage}x\n"
        message += f"**Margin Used:** ${margin:.2f}\n"
        message += f"**Position Value:** ${position_value:.2f}\n\n"
        
        if stop_loss_price and take_profit_price:
            sl_pct = abs(stop_loss_price - price) / price * 100
            tp_pct = abs(take_profit_price - price) / price * 100
            
            # Calculate potential P&L
            if side.lower() == "long":
                sl_pnl = (stop_loss_price - price) * size * leverage
                tp_pnl = (take_profit_price - price) * size * leverage
            else:
                sl_pnl = (price - stop_loss_price) * size * leverage
                tp_pnl = (price - take_profit_price) * size * leverage
            
            message += f"🛡️ **Risk Management:**\n"
            message += f"• Stop Loss: ${stop_loss_price:.2f} (-{sl_pct:.2f}%) → ${sl_pnl:+.2f}\n"
            message += f"• Take Profit: ${take_profit_price:.2f} (+{tp_pct:.2f}%) → ${tp_pnl:+.2f}\n"
            message += f"• Risk/Reward: 1:{tp_pct/sl_pct:.1f}\n\n"
            
            message += f"⏱️ **Expected timeframe:** 30min - 1hr\n"
        
        message += f"\n🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        await self.send_message(message)

    async def notify_trade_closed(self, side: str, size: float, entry: float, exit_price: float, pnl: float, reason: str = None):
        """Send notification when trade is closed with P&L"""
        emoji = "✅" if pnl > 0 else "❌"
        pnl_emoji = "💰" if pnl > 0 else "📉"
        
        # Calculate percentage P&L
        entry_value = abs(size) * entry
        pnl_pct = (pnl / entry_value * 100) if entry_value > 0 else 0
        
        # Determine if hit SL, TP, or manual
        if reason:
            close_reason = reason
        elif pnl > 0:
            close_reason = "Take Profit Hit 🎯"
        else:
            close_reason = "Stop Loss Hit 🛑"
        
        message = f"{emoji} **TRADE CLOSED** {pnl_emoji}\n\n"
        message += f"**Reason:** {close_reason}\n"
        message += f"**Direction:** {side.upper()}\n"
        message += f"**Size:** {abs(size):.4f} ETH\n"
        message += f"**Entry:** ${entry:.2f}\n"
        message += f"**Exit:** ${exit_price:.2f}\n"
        message += f"**Price Change:** ${exit_price - entry:+.2f} ({(exit_price/entry - 1)*100:+.2f}%)\n\n"
        message += f"**P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%)**\n\n"
        message += f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        await self.send_message(message)

    async def notify_neutral(self):
        """Send notification when bot goes neutral (flat)"""
        message = f"⚪ **POSITION FLAT**\n\n"
        message += f"Bot is now neutral (no position)\n"
        message += f"Waiting for next signal...\n"
        message += f"Time: {datetime.utcnow().strftime('%H:%M:%S UTC')}"
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
