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
- Cooldown and sizing caps are enforced in `risk.py`.