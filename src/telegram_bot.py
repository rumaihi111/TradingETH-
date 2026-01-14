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
            ("winrate", "Show trading statistics and win rate"),
            ("pnl", "Show P&L report"),
            ("status", "Show bot status"),
            ("deposit", "Show deposit address"),
            ("withdraw", "Withdraw USDC (usage: /withdraw <amount> <address>)"),
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
            daily = self.pnl_tracker.get_period_stats("daily")
            weekly = self.pnl_tracker.get_period_stats("weekly")
            monthly = self.pnl_tracker.get_period_stats("monthly")
            
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
            message += f"Total P&L: ${stats['total_pnl']:+.2f} ({stats['total_pnl_pct']:+.2f}%)\n\n"
            message += f"— Period Stats —\n"
            message += f"Daily: {daily['winning_trades']}/{daily['total_closed_trades']} ({daily['win_rate']:.1f}%), P&L: ${daily['total_pnl']:+.2f}\n"
            message += f"Weekly: {weekly['winning_trades']}/{weekly['total_closed_trades']} ({weekly['win_rate']:.1f}%), P&L: ${weekly['total_pnl']:+.2f}\n"
            message += f"Monthly: {monthly['winning_trades']}/{monthly['total_closed_trades']} ({monthly['win_rate']:.1f}%), P&L: ${monthly['total_pnl']:+.2f}"
            
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
    async def notify_trade_opened(self, side: str, size: float, price: float, sl_pct: float = 0.0, tp_pct: float = 0.0, leverage: Optional[float] = 10.0, why: Optional[str] = None):
        """Send notification when trade is opened"""
        emoji = "📈" if side.lower() == "long" else "📉"
        notional_value = size * price
        utc_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        local_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S local')

        message = f"{emoji} **TRADE OPENED**\n\n"
        message += f"Direction: {side.upper()}\n"
        message += f"Entry: ${price:.2f}\n"
        message += f"Size: {size:.4f} ETH\n"
        message += f"Position Value: ${notional_value:.2f}\n"
        if sl_pct:
            message += f"SL: {sl_pct*100:.1f}%\n"
        if tp_pct:
            message += f"TP: {tp_pct*100:.1f}%\n"
        if leverage is not None:
            message += f"Leverage: {leverage:.0f}x (Cross)\n"
        if why:
            message += f"Why: {why}\n"
        message += f"Signal Time: {utc_str} | {local_str}"

        await self.send_message(message)

    async def notify_trade_closed(self, side: str, size: float, entry: float, exit_price: float, pnl: float):
        """Send notification when trade is closed with P&L"""
        emoji = "✅" if pnl > 0 else "❌"
        pnl_emoji = "💰" if pnl > 0 else "📉"
        
        # Calculate percentage P&L
        entry_value = abs(size) * entry
        pnl_pct = (pnl / entry_value * 100) if entry_value > 0 else 0
        
        utc_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        local_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S local')
        message = f"{emoji} **TRADE CLOSED** {pnl_emoji}\n\n"
        message += f"Direction: {side.upper()}\n"
        message += f"Size: {abs(size):.4f} ETH\n"
        message += f"Entry: ${entry:.2f}\n"
        message += f"Exit: ${exit_price:.2f}\n"
        message += f"Price Change: ${exit_price - entry:+.2f} ({(exit_price/entry - 1)*100:+.2f}%)\n\n"
        message += f"**P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%)**\n\n"
        message += f"Signal Time: {utc_str} | {local_str}"
        
        await self.send_message(message)

    async def notify_neutral(self):
        """Send notification when bot goes neutral (flat)"""
        utc_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        local_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S local')
        message = f"⚪ **POSITION FLAT**\n\n"
        message += f"Bot is now neutral (no position)\n"
        message += f"Waiting for next signal...\n"
        message += f"Signal Time: {utc_str} | {local_str}"
        await self.send_message(message)

    async def notify_paused(self, reason: str, hours: int):
        utc_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        local_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S local')
        message = (
            f"⏸️ **BOT PAUSED**\n\nReason: {reason}\nDuration: {hours}h\n"
            f"Signal Time: {utc_str} | {local_str}"
        )
        await self.send_message(message)

    async def notify_shutdown(self, reason: str, hours: int):
        utc_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        local_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S local')
        message = (
            f"🛑 **BOT SHUTDOWN**\n\nReason: {reason}\nDuration: {hours}h\n"
            f"Signal Time: {utc_str} | {local_str}"
        )
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
