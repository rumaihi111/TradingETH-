# TradingETH

<div align="center">

![ETH Trading Bot](https://img.shields.io/badge/ETH-Trading%20Bot-627EEA?style=for-the-badge&logo=ethereum&logoColor=white)

**Automated ETH/USDC perpetual trading on Hyperliquid**

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Hyperliquid](https://img.shields.io/badge/Hyperliquid-DEX-8B5CF6?style=flat-square)](https://hyperliquid.xyz)
[![Claude AI](https://img.shields.io/badge/Claude-AI-FF6B6B?style=flat-square)](https://anthropic.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## Overview

TradingETH is an automated trading bot that combines RSI-based technical analysis with AI-powered market insights. It trades ETH perpetuals on Hyperliquid with 10x leverage, operating 24/7 with built-in risk management.

## Strategy

### RSI Engine (Period: 7)

| Zone | RSI Range | Action |
|:-----|:----------|:-------|
| 🔴 Short | 68.83 – 87 | Enter SHORT |
| 🟢 Long | 29 – 31 | Enter LONG |
| 🟡 Exit | 49 – 51 | Close position |
| ⚪ Neutral | Outside zones | Hold / Wait |

The bot monitors 5-minute candles and executes trades when RSI enters the defined zones. Positions are closed at the middle zone (49-51) when in profit.

### Risk Management

- **Leverage:** 10x
- **Position Size:** 95% of available margin
- **Stop Loss:** Dynamic, based on market structure
- **Take Profit:** 1.5x – 3x risk/reward ratio

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/rumaihi111/TradingETH-.git
cd TradingETH-
pip install -r requirements.txt
```

### 2. Configure

Create `.env` in the project root:

```env
# Required
PRIVATE_KEY=your_hyperliquid_private_key
ANTHROPIC_API_KEY=your_claude_api_key

# Optional
ACCOUNT_ADDRESS=your_wallet_address
HYPERLIQUID_TESTNET=false
PAPER_MODE=false
PAPER_INITIAL_EQUITY=10000

# Telegram Notifications
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 3. Run

```bash
python start.py
```

**Paper Trading:**
```bash
PAPER_MODE=true python start.py
```

## Telegram Commands

| Command | Description |
|:--------|:------------|
| `/balance` | Wallet balance & positions |
| `/pnl` | Profit/Loss report |
| `/winrate` | Trading statistics |
| `/rsi` | Current RSI value |
| `/analysis` | AI market analysis |
| `/price` | Current ETH price |
| `/closetrade` | Close current position |
| `/status` | Bot status |
| `/help` | All commands |

## Architecture

```
src/
├── runner_live.py      # Main trading loop
├── rsi_engine.py       # RSI strategy logic
├── ai_client.py        # Claude AI integration
├── exchange_*.py       # Exchange connectors
├── telegram_bot.py     # Notifications
├── risk.py             # Risk management
└── config.py           # Configuration
```

## Deployment

### Railway

1. Connect GitHub repo to Railway
2. Add environment variables
3. Deploy

### Local Service

```bash
sudo cp scripts/tradingbot.service.example /etc/systemd/system/tradingbot.service
sudo systemctl enable --now tradingbot
```

## Disclaimer

⚠️ **For educational purposes only.** Trading cryptocurrencies involves substantial risk. Only trade with money you can afford to lose. This is not financial advice.

---

<div align="center">

**Built for Asher Shepherd Newton** ❤️

</div>
