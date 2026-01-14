# Railway Deployment Guide

## Setup Steps

### 1. Create Service
- Connect your GitHub repo `rumaihi111/TradingETH-`
- Railway will auto-deploy on push to `main`

### 2. Environment Variables
Go to Settings → Variables and add:
```
ANTHROPIC_API_KEY=sk-ant-api03-...
VENICE_API_KEY=venice_live_key...
PAPER_MODE=true
PAPER_INITIAL_EQUITY=10000
HYPERLIQUID_TESTNET=true
```

Optional overrides (defaults are fine):
```
VENICE_ENDPOINT=https://api.venice.ai/v1/chat/completions
VENICE_MODEL=mistral-31-24b
```

### 3. **CRITICAL: Add Persistent Volume**
To preserve wallet state, history, and trade logs across deployments:

1. Go to your service → **Settings** → **Volumes**
2. Click **+ New Volume**
3. Mount Path: `/app/data`
4. Size: 1GB (minimum)
5. Save and redeploy

**Without a volume:**
- Paper wallet resets to $10k on every deploy
- Claude history lost on redeploy
- Trade frequency guard resets (could violate cooldown rules)

**With a volume:**
- Wallet equity persists across deploys
- 24h history rollover continues uninterrupted
- Trade frequency tracking survives restarts

### 4. Monitor Logs
```bash
# Railway CLI (optional)
railway logs
```

Look for:
- `💰 Current Wallet: $X.XX` - Wallet balance before each query
- `🤖 Venice direction:` - Direction, detected pattern, and rationale
- `CLAUDE QUERY:` - Full personality prompt sent
- `CLAUDE RESPONSE (raw):` - Claude's decision
- `Trade placed:` - Execution confirmation
- `Paper wallet updated:` - PnL after close

## Files Persisted in Volume
- `data/paper_wallet.json` - Wallet equity and position
- `data/claude_history.jsonl` - Last 24h of decisions
- `data/claude_history.jsonl.archive` - Historical decisions
- `data/trades.jsonl` - Trade execution log

## Troubleshooting

**Bot restarts constantly:**
- Check logs for errors (Binance geo-block = use KuCoin)
- Verify ANTHROPIC_API_KEY is valid

**Wallet resets on deploy:**
- Volume not mounted at `/app/data`
- Check Settings → Volumes

**No trades executing:**
- Frequency guard active (max 2/hour, 30m cooldown)
- Claude returning `side: "flat"`
- Check logs for Claude's reasoning
