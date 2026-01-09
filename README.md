<p align="center">
  <img src="https://img.shields.io/badge/ETH-Trading%20Bot-627EEA?style=for-the-badge&logo=ethereum&logoColor=white" alt="ETH Trading Bot"/>
</p>

<h1 align="center">🤖 TradingETH</h1>

<p align="center">
  <strong>AI-Powered Ethereum Trading Bot with Dual-Brain System</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Claude-AI-191919?style=flat-square&logo=anthropic&logoColor=white" alt="Claude AI"/>
  <img src="https://img.shields.io/badge/Hyperliquid-DEX-00D4AA?style=flat-square" alt="Hyperliquid"/>
  <img src="https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat-square&logo=telegram&logoColor=white" alt="Telegram"/>
  <img src="https://img.shields.io/badge/Railway-Deploy-0B0D0E?style=flat-square&logo=railway&logoColor=white" alt="Railway"/>
</p>

---

## 🧠 Dual-Brain Architecture

This bot uses a **two-brain system** for intelligent trade decisions:

### Brain 1: Claude Vision AI
- Analyzes 5-minute candlestick charts with RSI overlay
- Identifies patterns: triangles, flags, head & shoulders, double tops/bottoms
- Detects support/resistance levels
- Makes trading decisions based on visual analysis

### Brain 2: RSI Brain (Hive Mind)
- RSI(14) indicator on 5-minute timeframe
- Behavioral analysis: expectations, momentum, trapped traders
- Acts as a **filter** - blocks/approves Claude's decisions
- Calculates optimal stop-loss and take-profit levels

---

## 📊 RSI Trading Rules

| Zone | RSI Value | Action |
|:-----|:----------|:-------|
| 🟢 **Long Zone** | < 35.28 | ✅ Enter LONG positions |
| 🔴 **Short Zone** | > 66.80 | ✅ Enter SHORT positions |
| ⚠️ **No-Man's Land** | 35.28 - 66.80 | 🚫 NO entries allowed |
| 💰 **Profit Exit** | = 50.44 | Exit if position is profitable |

---

## 💰 Position Sizing & Leverage

```
┌─────────────────────────────────────────┐
│  Wallet: $100                           │
│  ├── Margin (80%): $80                  │
│  ├── Leverage: 10x                      │
│  └── Position Value: $800               │
└─────────────────────────────────────────┘
```

- **80% of wallet** used as margin
- **10x leverage** on Hyperliquid
- Max 1 position at a time
- Max 2 trades per hour with 30-min cooldown

---

## 🛡️ Risk Management

The RSI Brain calculates SL/TP based on:
- Recent support/resistance levels
- Market volatility (ATR-like measure)
- Realistic 30min-1hr timeframe targets

| Parameter | Range |
|:----------|:------|
| Stop Loss | 0.8% - 2.5% |
| Take Profit | 1.5% - 4.0% |
| Min Risk/Reward | 1:1.5 |

---

## 📱 Telegram Commands

| Command | Description |
|:--------|:------------|
| `/balance` | 💰 Wallet balance & positions |
| `/position` | 📊 Detailed position info |
| `/pnl` | 💵 P&L report |
| `/winrate` | 📈 Trading statistics |
| `/status` | 🟢 Bot status |
| `/rsi` | 📉 Current RSI & zone |
| `/help` | ❓ All commands |
| `/deposit` | 💳 Deposit address |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/TradingETH-.git
cd TradingETH-
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Required
export ANTHROPIC_API_KEY="sk-ant-..."
export PRIVATE_KEY="0x..."

# Optional - for main wallet trading
export ACCOUNT_ADDRESS="0x..."  # Main wallet address

# Hyperliquid Settings
export HYPERLIQUID_TESTNET=false  # true for testnet

# Paper Trading
export PAPER_MODE=false
export PAPER_INITIAL_EQUITY=10000

# Telegram Notifications
export TELEGRAM_TOKEN="123456:ABC..."
export TELEGRAM_CHAT_ID="123456789"

# Position Sizing
export MAX_POSITION_FRACTION=0.8  # 80% of wallet
```

### 3. Run

```bash
# Live trading
python -m src.runner_live

# Paper trading (simulation)
PAPER_MODE=true python -m src.runner_live
```

---

## 🚂 Railway Deployment

### One-Click Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template)

### Manual Setup

1. **Create Railway Project**
   ```bash
   railway login
   railway init
   ```

2. **Add Environment Variables**
   - Go to Railway Dashboard → Variables
   - Add all required env vars (see above)

3. **Add Persistent Volume** ⚠️ CRITICAL
   ```
   Mount Path: /app/data
   ```
   This preserves wallet state and trade history across deploys.

4. **Deploy**
   ```bash
   railway up
   ```

---

## 📁 Project Structure

```
TradingETH-/
├── src/
│   ├── ai_client.py       # Claude Vision AI integration
│   ├── rsi_brain.py       # RSI Brain (second brain)
│   ├── runner_live.py     # Main trading loop
│   ├── exchange_hyperliquid.py  # Hyperliquid SDK wrapper
│   ├── exchange_paper.py  # Paper trading simulator
│   ├── telegram_bot.py    # Telegram notifications
│   ├── risk.py            # Risk management & guards
│   ├── pnl_tracker.py     # P&L tracking
│   ├── config.py          # Configuration
│   └── trade_logger.py    # Trade logging
├── scripts/
│   ├── check_positions.py # Check open positions
│   ├── close_position.py  # Manual position close
│   └── smoke_test.py      # Test connectivity
├── data/                  # Trade history & state
├── Procfile              # Railway entry point
├── requirements.txt      # Python dependencies
└── README.md
```

---

## ⚙️ Configuration Reference

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `ANTHROPIC_API_KEY` | ✅ | - | Claude API key |
| `PRIVATE_KEY` | ✅ | - | Wallet private key |
| `ACCOUNT_ADDRESS` | ❌ | - | Main wallet for trading |
| `HYPERLIQUID_TESTNET` | ❌ | `true` | Use testnet |
| `PAPER_MODE` | ❌ | `false` | Paper trading |
| `PAPER_INITIAL_EQUITY` | ❌ | `10000` | Starting balance |
| `MAX_POSITION_FRACTION` | ❌ | `0.8` | Margin % |
| `TELEGRAM_TOKEN` | ❌ | - | Telegram bot token |
| `TELEGRAM_CHAT_ID` | ❌ | - | Telegram chat ID |

---

## 📊 How It Works

```
┌──────────────────────────────────────────────────────────────┐
│                     TRADING LOOP                              │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Fetch 5-min candles from KuCoin                          │
│                     ↓                                         │
│  2. RSI Brain checks for EXIT signals                        │
│     • RSI = 50.44 + in profit → EXIT                         │
│     • RSI at opposite extreme → TAKE PROFIT                  │
│                     ↓                                         │
│  3. Generate chart with RSI overlay                          │
│                     ↓                                         │
│  4. Claude AI analyzes chart visually                        │
│     → Returns: LONG / SHORT / FLAT                           │
│                     ↓                                         │
│  5. RSI Brain validates entry                                │
│     • RSI < 35.28 → Allow LONG                               │
│     • RSI > 66.80 → Allow SHORT                              │
│     • Otherwise → BLOCK entry                                │
│                     ↓                                         │
│  6. Execute trade on Hyperliquid                             │
│     • 80% margin, 10x leverage                               │
│     • Set SL/TP orders                                       │
│                     ↓                                         │
│  7. Send Telegram notification                               │
│                     ↓                                         │
│  8. Wait cooldown (30 min) → Repeat                          │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔒 Security Notes

- ⚠️ **Never commit private keys** - use environment variables
- 🔐 Use a dedicated **API wallet** with limited funds
- 📊 Start with **paper mode** to test strategies
- 💰 Only trade what you can afford to lose

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Built with 🧠 by the Dual-Brain System</strong>
</p>

<p align="center">
  <sub>Claude AI + RSI Brain = Smarter Trading</sub>
</p>
