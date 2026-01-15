# TradingETH Bot - 24/7 Operation Guide

## What Was Fixed

Your bot was closing positions immediately after opening them because:

1. **AI was checking positions too frequently** (every 5 minutes) and being too eager to close
2. **No minimum hold time** - positions could be closed seconds after opening
3. **AI memory was cleared** after every trade, causing context loss
4. **No systemd service** configured for reliable 24/7 operation

## Changes Made

### 1. Minimum Hold Time (15 Minutes)
- Bot will NOT close positions for at least 15 minutes after opening
- This prevents panic closes and gives your trades room to develop
- Even if AI wants to close, the bot will refuse until minimum time passes

### 2. Reduced Monitoring Frequency
- **Before**: Checked positions every 5 minutes
- **After**: Checks positions every 15 minutes
- This reduces over-management and prevents premature exits

### 3. Stricter AI Closing Rules
The AI now only closes positions when:
- Clear trend reversal confirmed (multiple opposing candles)
- Major support/resistance broken with strong momentum  
- Clear invalidation pattern

The AI will NOT close for:
- Small pullbacks (normal price action)
- Single opposing candle (noise)
- Just because target is reached (lets winners run)

### 4. 24/7 Systemd Service
- Bot runs as a background service
- Auto-restarts on crashes
- Starts automatically on system boot
- Logs everything for debugging

## Setup Instructions

### Option 1: Automated Setup (Recommended)
```bash
sudo /workspaces/TradingETH-/scripts/setup_24_7.sh
```

### Option 2: Manual Setup
```bash
# 1. Copy service file
sudo cp /workspaces/TradingETH-/scripts/tradingbot.service.example /etc/systemd/system/tradingbot.service

# 2. Edit the service file and replace %USER% with your username
sudo nano /etc/systemd/system/tradingbot.service

# 3. Create log directory
sudo mkdir -p /var/log/tradingbot
sudo chown $USER:$USER /var/log/tradingbot

# 4. Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable tradingbot
sudo systemctl start tradingbot
```

## Managing Your Bot

### Check Status
```bash
sudo systemctl status tradingbot
```

### View Live Logs
```bash
# System logs
sudo journalctl -u tradingbot -f

# Application logs
sudo tail -f /var/log/tradingbot.log
```

### Stop Bot
```bash
sudo systemctl stop tradingbot
```

### Start Bot
```bash
sudo systemctl start tradingbot
```

### Restart Bot
```bash
sudo systemctl restart tradingbot
```

### View Recent Logs
```bash
sudo journalctl -u tradingbot -n 100 --no-pager
```

## Important Settings

### Current Configuration
- **Minimum hold time**: 15 minutes (prevents immediate closes)
- **Monitoring interval**: 15 minutes (reduces over-checking)
- **Max trades per hour**: 2 (from your config)
- **Cooldown between trades**: 10 minutes (from your config)

### Adjusting Minimum Hold Time
Edit [runner_live.py](src/runner_live.py) line ~89:
```python
minimum_hold_minutes = 15  # Change this value (5-30 recommended)
```

### Adjusting Monitoring Interval  
Edit [runner_live.py](src/runner_live.py) line ~518:
```python
await asyncio.sleep(900)  # 900 = 15 minutes, 600 = 10 minutes
```

## Troubleshooting

### Bot keeps closing positions
- Check minimum hold time is enforced (look for "refusing to close" in logs)
- Increase monitoring interval to 20-30 minutes
- Review AI closing reasons in logs

### Bot not opening trades
- Check filters in logs (time filter, volatility gate, MTF alignment)
- Verify cooldown period has passed
- Check risk manager isn't paused/shutdown

### Bot crashed/stopped
```bash
# Check status
sudo systemctl status tradingbot

# View error logs
sudo journalctl -u tradingbot -n 50 --no-pager

# Restart
sudo systemctl restart tradingbot
```

### Logs not showing up
```bash
# Make sure log directory exists and has correct permissions
ls -la /var/log/tradingbot.log
sudo chown $USER:$USER /var/log/tradingbot.log
```

## Monitoring Your Bot's Health

### Daily Checklist
1. Check bot is running: `sudo systemctl status tradingbot`
2. Review recent trades: Check Telegram notifications or trade logs
3. Check for errors: `sudo journalctl -u tradingbot --since today | grep -i error`

### Weekly Checklist
1. Review performance in trade_history.csv
2. Check if any positions were liquidated
3. Verify stop losses are being respected
4. Review AI decision patterns for any issues

## Key Metrics to Watch

### Good Signs ✅
- Positions held for 15+ minutes before closing
- Stop losses being respected
- AI citing clear reversal patterns when closing
- Win rate around 50%+ with positive R:R

### Warning Signs ⚠️
- Positions closing at exactly 15 minutes (AI wants out immediately)
- Frequent flip-flopping between long/short
- Low win rate (<40%) with poor R:R
- Multiple consecutive losses triggering pause

## Emergency Actions

### Stop All Trading Immediately
```bash
sudo systemctl stop tradingbot
```

### Close Open Position Manually
```bash
cd /workspaces/TradingETH-
source .venv/bin/activate
python scripts/close_position.py
```

### Reset Bot (Clear History)
```bash
rm data/claude_history.jsonl
sudo systemctl restart tradingbot
```

## Configuration Files

- **Main config**: `.env` (API keys, settings)
- **Service config**: `/etc/systemd/system/tradingbot.service`  
- **Trade history**: `data/trades.jsonl`
- **AI decisions**: `data/claude_history.jsonl`
- **P&L tracking**: `data/pnl_tracker.json`

## Support

If issues persist:
1. Check logs for error patterns
2. Review recent AI decisions in `data/claude_history.jsonl`
3. Check your account on Hyperliquid for actual position state
4. Verify .env configuration is correct

---

**Remember**: The bot is now configured to be more patient. It will hold positions for at least 15 minutes and only close on strong reversal signals. Trust your setups!
