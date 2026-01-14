# TradingETH-

Quick scaffold for an ETH trading bot with:
- Hyperliquid testnet execution (placeholder client)
- Hyperliquid testnet execution via official SDK
- 5m signals from an external AI (Claude)
- Guardrails: 1 position, <=2 trades/hour, 30m cooldown, max 50% equity size
- Local history store that rolls every 24h, carrying last 3h forward
- Paper mode simulator for orderless dry-runs

## Setup
1) Install deps: `pip install -r requirements.txt`
# TradingETH-

Clean, vision-first ETH trading bot that fuses two AIs:

- Venice Mistral-31-24b (vision): decides `long`/`short`/`flat`, names the pattern, and explains why.
- Claude (vision): validates the same pattern on the chart, sets stop loss / take profit / slippage, and monitors live trades.

Built for Hyperliquid (testnet or mainnet), with robust risk controls, Telegram alerts, and a paper simulator for safe local testing.

---

## Features
- Vision-first signals from chart images (auto-generated or screenshots).
- Side decision by Venice; SL/TP and monitoring by Claude.
- One position at a time, max trades/hour, cooldowns, volatility filter.
- Daily loss limit + loss-streak pause with auto-shutdown windows.
- Telegram alerts for opens/closes, pauses, and shutdowns.
- Paper mode simulator; persistent history and logs.

## Quick Start
1) Install dependencies
```bash
pip install -r requirements.txt
```

2) Provide environment variables (paper-mode example)
```bash
export PAPER_MODE=true
export PAPER_INITIAL_EQUITY=10000
export VENICE_API_KEY=your_venice_key
export ANTHROPIC_API_KEY=your_anthropic_key
export HYPERLIQUID_TESTNET=true
# optional overrides
export VENICE_ENDPOINT=https://api.venice.ai/v1/chat/completions
export VENICE_MODEL=mistral-31-24b
```

3) Verify configuration
```bash
python scripts/smoke_test.py
```

4) Run the live loop (paper mode)
```bash
python -m src.runner_live
```

For Railway deployment details, see [RAILWAY.md](RAILWAY.md).

## How It Works
- Venice (vision) receives the chart image and returns JSON: `{side, pattern, reason}`.
- Claude (vision) gets the same image and Venice’s `{side, pattern, reason}`:
	- Validates the described pattern in the chart.
	- Produces `stop_loss_pct`, `take_profit_pct`, and `max_slippage_pct`.
	- In monitoring mode, only chooses `flat` (close) or hold — no flips.
- The runner executes opens/closes, places risk orders, and enforces guardrails.

### Components
- AI Orchestration: [src/ai_client.py](src/ai_client.py)
- Live Runner: [src/runner_live.py](src/runner_live.py)
- Risk Controls: [src/risk.py](src/risk.py)
- PnL Tracker: [src/pnl_tracker.py](src/pnl_tracker.py)
- History Store: [src/history_store.py](src/history_store.py)
- Trade Logger: [src/trade_logger.py](src/trade_logger.py)
- Telegram Bot: [src/telegram_bot.py](src/telegram_bot.py)
- Fractal Brain (nested-pattern hints): [src/fractal_brain.py](src/fractal_brain.py)
- Exchanges: [src/exchange_hyperliquid.py](src/exchange_hyperliquid.py), [src/exchange_paper.py](src/exchange_paper.py)

## Configuration
Environment variables drive behavior. Common settings:

### AI
- `VENICE_API_KEY` — required for Venice vision.
- `VENICE_ENDPOINT` — default `https://api.venice.ai/v1/chat/completions`.
- `VENICE_MODEL` — default `mistral-31-24b`.
- `ANTHROPIC_API_KEY` — required for Claude vision.

### Trading
- `TIMEFRAME` — default `5m`.
- `CANDLE_LIMIT` — default `350`.
- `trading_pair` (internal) — ETH only on Hyperliquid.

### Risk
- `DAILY_LOSS_LIMIT_PCT` — default `0.06` (shutdown at daily limit).
- `PAUSE_CONSECUTIVE_LOSSES` — default `3`.
- `PAUSE_DURATION_HOURS` — default `24`.
- `SHUTDOWN_DURATION_HOURS` — default `24`.
- `VOLATILITY_THRESHOLD_PCT` — default `0.02` (skip spike cycles).

### Execution
- `PAPER_MODE` — `true` for simulator, `false` for real.
- `PAPER_INITIAL_EQUITY` — default `10000`.
- `HYPERLIQUID_TESTNET` — `true` for testnet.
- `PRIVATE_KEY`, `ACCOUNT_ADDRESS` — required for real orders.

### Telegram
- `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` — optional alerts.

## Paper Mode
- Simulates orders with local state and no fees.
- Size = 80–95% of wallet equity (configurable cap).
- Stop/TP are tracked logically; liquidation guard applies.

## Logs & Monitoring
- Venice decision: side, pattern, reason.
- Claude decision: JSON with SL/TP and constraints.
- Trade events: opens/closes, verified positions, trigger orders.
- Risk events: pauses and shutdowns with context.

## Common Issues
- Missing keys: ensure both `VENICE_API_KEY` and `ANTHROPIC_API_KEY` are set.
- Rate limits: the runner backs off automatically.
- Volatility filter: cycles are skipped when 5m spike exceeds threshold.

## Project Structure
```
Procfile
RAILWAY.md
README.md
requirements.txt
scripts/
src/
	ai_client.py
	config.py
	exchange_hyperliquid.py
	exchange_paper.py
	fractal_brain.py
	history_store.py
	pnl_tracker.py
	risk.py
	runner_backtest.py
	runner_live.py
	telegram_bot.py
	trade_logger.py
```

---

### Quick Commands
- Install: `pip install -r requirements.txt`
- Smoke test: `python scripts/smoke_test.py`
- Run live (paper): `python -m src.runner_live`
