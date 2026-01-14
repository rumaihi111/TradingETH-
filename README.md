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
2) Set env vars (example):
```
export HYPERLIQUID_API_KEY=...
export HYPERLIQUID_SECRET=...
export HYPERLIQUID_BASE_URL=""        # optional override; SDK uses constants
export HYPERLIQUID_TESTNET=true
export ANTHROPIC_API_KEY=...
export VENICE_API_KEY=...
export RPC_URL=...
export WALLET_ADDRESS=...
export PRIVATE_KEY=...
export PAPER_MODE=false       # set true to simulate
export PAPER_INITIAL_EQUITY=10000
```
`HYPERLIQUID_API_KEY` and `HYPERLIQUID_SECRET` are optional when using the SDK with a private key.

## Paper mode
- Set `PAPER_MODE=true` to skip real orders and simulate fills with a local paper exchange.
- `PAPER_INITIAL_EQUITY` sets starting equity for simulation.
3) Backtest placeholder: `python -m src.runner_backtest`
4) Live loop placeholder: `python -m src.runner_live`

## History store
- Stored at `data/claude_history.jsonl` via `HistoryStore`
- Keeps 24h of decisions; on rollover, archives old file and carries last 3h into a fresh file
- AI client receives the recent decisions window and records each parsed decision

## Trade log
- Stored at `data/trades.jsonl` via `TradeLogger`
- Keeps 24h of trades; on rollover, archives old file and carries last 3h into a fresh file
- Each entry: timestamp, decision (side/size/stop/tp), result (fill info), and price

## Notes
- Hyperliquid client now uses the official SDK; sizing/price feed still TODO.
- AI prompt/response parsing is minimal; return JSON with side/size/stop/tp/slippage.
- Direction is determined by Venice (vision); Claude (vision) validates the pattern and computes SL/TP.
- Cooldown and sizing caps are enforced in `risk.py`.

## Trading Rules & Alerts
- Asset: ETH only, timeframe: 5m, analysis window: 350 candles.
- No indicators: decisions are based on price action and patterns.
- Volatility filter: skip trading when the most recent 5m close-to-close move exceeds `VOLATILITY_THRESHOLD_PCT` (default 2%).
- Max daily loss: 6% of starting equity (net closed PnL) triggers immediate position close, shutdown for 24h, Telegram alert.
- Loss streak pause: after 3 consecutive losing closes, pause trading for 24h and alert on Telegram.
- Telegram alerts include: signal timestamp (UTC + local), direction, entry, SL/TP%, leverage (assumed 10x Cross), and a brief "why" summary.

## Stats Definitions
- Basis: net PnL after fees when available from exchange responses; paper mode excludes fees.
- Win/Loss: a closed trade with `pnl > 0` is a win; partial closes count according to net for that close.
- Periods: daily (UTC day), weekly (ISO week), monthly (calendar month) computed on closed trades.
- Reported metrics: total closed trades, winners/losers, win rate, total PnL, average win/loss.

### Config (env vars)
- `TIMEFRAME` (default `5m`), `CANDLE_LIMIT` (default `350`)
- `DAILY_LOSS_LIMIT_PCT` (default `0.06`)
- `PAUSE_CONSECUTIVE_LOSSES` (default `3`), `PAUSE_DURATION_HOURS` (default `24`)
- `SHUTDOWN_DURATION_HOURS` (default `24`)
- `VOLATILITY_THRESHOLD_PCT` (default `0.02`)
 - `VENICE_ENDPOINT` (default `https://api.venice.ai/v1/chat/completions`)
 - `VENICE_MODEL` (default `mistral-31-24b`)