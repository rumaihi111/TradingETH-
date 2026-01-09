# 🤖 TradingETH - Advanced AI Trading Bot

<div align="center">

**Intelligent ETH/USDC Trading Bot with Dual-Brain AI Analysis**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hyperliquid](https://img.shields.io/badge/Exchange-Hyperliquid-purple.svg)](https://hyperliquid.xyz)

</div>

## 🌟 Features

### 🧠 Dual-Brain AI System
- **Main Brain (Claude Sonnet 4)**: Visual chart analysis, pattern recognition, and decision making
- **Second Brain**: Advanced price action analysis focusing on:
  - Market expectations vs delivery
  - Second reactions and confirmations
  - Speed changes and momentum
  - Trapped traders identification
  - Market psychology and indifference detection

### 📊 Technical Analysis
- **RSI Strategy** (14-period on 5-minute charts):
  - RSI > 66.80 → Enter SHORT
  - RSI < 35.28 → Enter LONG
  - RSI ≈ 50.44 → EXIT ZONE (close if profitable)
  - No-Man Zone (35.28-66.80) → No new entries, only exits

- **Visual Chart Analysis**:
  - Chart patterns (triangles, flags, head & shoulders, wedges)
  - Support/resistance levels
  - Candlestick patterns (engulfing, doji, hammers)
  - Volume patterns and divergences

### 💰 Risk Management
- **Leverage**: 10x on all trades
- **Position Sizing**: 80% of available margin
  - Example: $70 margin = $800 position value
- **Intelligent Stop Loss**: Based on market structure, phase, and volatility
- **Take Profit Targets**: 30-60 minute targets with 1.5x-3x risk/reward
- **Trade Frequency**: Max 2 trades/hour with 30-minute cooldown

### 📱 Telegram Integration
- Real-time trade notifications with:
  - Entry price and position size
  - Stop loss and take profit levels
  - Expected profit/loss calculations
  - Risk/reward ratios
  - Position updates
- Interactive commands:
  - `/balance` - Wallet balance and positions
  - `/winrate` - Trading statistics
  - `/pnl` - Profit/Loss report
  - `/status` - Bot status
  - `/withdraw` - Withdraw funds
  - `/deposit` - Deposit address

### 📈 Trading Features
- Live 5-minute candlestick analysis
- Automatic position management
- Paper trading mode for testing
- Trade history and P&L tracking
- Liquidation protection
- Rate limit handling

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- Hyperliquid account (testnet or mainnet)
- Anthropic API key (Claude)
- Telegram bot (optional)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/TradingETH-.git
cd TradingETH-
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**

Create a `.env` file in the root directory:

```bash
# Hyperliquid Configuration
PRIVATE_KEY=your_private_key_here
ACCOUNT_ADDRESS=your_main_wallet_address
HYPERLIQUID_TESTNET=false
HYPERLIQUID_BASE_URL=  # Optional override

# AI Configuration
ANTHROPIC_API_KEY=your_claude_api_key

# Trading Configuration
PAPER_MODE=false  # Set to true for paper trading
PAPER_INITIAL_EQUITY=10000
MAX_POSITION_FRACTION=0.8  # 80% of wallet
MAX_TRADES_PER_HOUR=2
COOLDOWN_MINUTES=30

# Telegram (Optional)
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Blockchain RPC (Optional)
RPC_URL=your_rpc_url
WALLET_ADDRESS=your_wallet_address
```

### Running the Bot

**Live Trading:**
```bash
python -m src.runner_live
```

**Paper Trading (Simulation):**
```bash
PAPER_MODE=true python -m src.runner_live
```

**Backtest (Coming Soon):**
```bash
python -m src.runner_backtest
```

---

## 🧩 Architecture

### Module Overview

```
TradingETH-/
├── src/
│   ├── runner_live.py         # Main trading loop
│   ├── ai_client.py            # Main AI brain (Claude)
│   ├── second_brain.py         # Advanced price action analysis
│   ├── indicators.py           # Technical indicators (RSI, ATR, etc.)
│   ├── exchange_hyperliquid.py # Hyperliquid API client
│   ├── exchange_paper.py       # Paper trading simulator
│   ├── telegram_bot.py         # Telegram notifications
│   ├── risk.py                 # Risk management
│   ├── pnl_tracker.py          # P&L tracking
│   ├── history_store.py        # Decision history
│   ├── trade_logger.py         # Trade logging
│   └── config.py               # Configuration management
├── scripts/                    # Utility scripts
├── requirements.txt            # Python dependencies
└── .env                        # Environment configuration
```

### Trading Flow

```
┌─────────────────────┐
│ Fetch 5m Candles    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Calculate RSI       │
└──────────┬──────────┘
           │
           ▼
      ┌────────┐
      │RSI > 66.80?│───YES──> SHORT SIGNAL
      └────┬───┘
           │
           ▼
      ┌────────┐
      │RSI < 35.28?│───YES──> LONG SIGNAL
      └────┬───┘
           │
           ▼
┌─────────────────────┐
│ Second Brain        │
│ Analysis            │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Main AI Decision    │
│ (Claude)            │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Calculate SL/TP     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Execute Trade       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Send Telegram Alert │
└─────────────────────┘
```

---

## 📊 Second Brain Analysis

The Second Brain performs deep market analysis:

### 10 Key Analysis Points

1. **Expectations vs Delivery** - Did price do what was expected?
2. **Second Reactions** - Confirmation or exhaustion signals
3. **Speed Changes** - Acceleration/deceleration tracking
4. **Price Indifference** - When big moves get absorbed
5. **Hesitation Detection** - Where price pauses vs clean passes
6. **If-Then Logic Trees** - Conditional reasoning
7. **Time Pullbacks** - Sideways consolidation vs price retracements
8. **Behavior Changes** - Regime shift detection
9. **Emotional State** - FOMO, Fear, or Calm alignment
10. **Trapped Traders** - Identifying fuel for moves

### Market Phase Classification
- **Accumulation**: Tight, sideways, overlapping
- **Expansion**: Fast, directional, long candles
- **Distribution**: Stalling after expansion
- **Retracement**: Controlled pullback

---

## 🔧 Configuration

### Risk Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_POSITION_FRACTION` | 0.8 | 80% of wallet per trade |
| `LEVERAGE` | 10x | Fixed leverage multiplier |
| `MAX_TRADES_PER_HOUR` | 2 | Rate limiting |
| `COOLDOWN_MINUTES` | 30 | Time between trades |
| `RSI_OVERBOUGHT` | 66.80 | Short trigger level |
| `RSI_OVERSOLD` | 35.28 | Long trigger level |
| `RSI_NEUTRAL` | 50.44 | Exit zone |

### Stop Loss & Take Profit

Calculated intelligently based on:
- Market volatility (ATR)
- Market phase (accumulation, expansion, etc.)
- Support/resistance levels
- Typical range: SL 3-8%, TP 5-15%
- Target R:R ratio: 1.5:1 to 3:1

---

## 📱 Telegram Commands

| Command | Description |
|---------|-------------|
| `/balance` | Show current wallet balance and open positions |
| `/winrate` | Display win rate and trading statistics |
| `/pnl` | Show P&L report with percentage gains |
| `/status` | Bot status and current position |
| `/deposit` | Get deposit address for funding |
| `/withdraw <amount> <address>` | Withdraw USDC to external wallet |

### Notification Types

- **🔔 Trade Opened** - Entry price, size, SL/TP levels
- **✅ Trade Closed** - Exit price, P&L, percentage gain
- **📊 Position Updates** - Real-time position monitoring
- **🧠 Signal Received** - AI decision with RSI and confidence
- **⚪ Neutral** - Position closed, waiting for signal

---

## 🛡️ Safety Features

- **Liquidation Protection**: Monitors unrealized losses
- **Rate Limit Handling**: Exponential backoff on API limits
- **Position Verification**: Confirms orders executed correctly
- **Minimum Order Size**: $11 minimum to meet exchange requirements
- **Cooldown Enforcement**: Prevents overtrading
- **Paper Mode**: Test strategies without real money

---

## 📂 Data Storage

### History Store
- File: `data/claude_history.jsonl`
- Stores AI decisions for 24 hours
- Rolls over daily, keeps last 3 hours

### Trade Log
- File: `data/trades.jsonl`
- Complete trade history with entry/exit
- P&L tracking per trade

### CSV Export
- File: `trade_history.csv`
- Exportable trade data for analysis

---

## 🐛 Troubleshooting

### Common Issues

**Bot won't start:**
```bash
# Check environment variables
python -c "from src.config import load_settings; print(load_settings())"
```

**No trades executing:**
- Verify RSI is outside no-man zone (35.28-66.80)
- Check cooldown timer (30 minutes between trades)
- Ensure minimum equity ($11+)

**Rate limit errors:**
- Bot automatically handles with exponential backoff
- Wait 60-600 seconds before retry

**Position not found:**
- Order may be below minimum size
- Check account balance
- Verify exchange connectivity

---

## 🚧 Deployment

### Railway.app

1. Connect your GitHub repository
2. Add environment variables in Railway dashboard
3. Deploy automatically on push

### Local Systemd Service

```bash
# Copy service file
sudo cp scripts/tradingbot.service.example /etc/systemd/system/tradingbot.service

# Edit paths and user
sudo nano /etc/systemd/system/tradingbot.service

# Enable and start
sudo systemctl enable tradingbot
sudo systemctl start tradingbot

# Check status
sudo systemctl status tradingbot
```

---

## 📈 Performance Monitoring

- Track win rate with `/winrate`
- Monitor P&L with `/pnl`
- Review trade history in `trade_history.csv`
- Analyze decisions in `claude_history.jsonl`

---

## ⚠️ Disclaimer

**This bot is for educational purposes only.**

- Trading cryptocurrencies involves substantial risk
- Past performance does not guarantee future results
- Only trade with money you can afford to lose
- Always test with paper trading first
- Not financial advice - DYOR (Do Your Own Research)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- Built with [Hyperliquid Python SDK](https://github.com/hyperliquid-dex/hyperliquid-python-sdk)
- Powered by [Anthropic Claude](https://www.anthropic.com/)
- Chart generation with [mplfinance](https://github.com/matplotlib/mplfinance)

---

<div align="center">

**Made with ❤️ for Asher Shepherd Newton**

*Trade smart, trade safe* 🚀

</div>
