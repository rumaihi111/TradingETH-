# 🤖 FIXED: Your Bot Now Runs 24/7 Without Closing Trades Immediately

## What Was Wrong ❌

Your bot was:
1. **Opening trades then immediately closing them** - costing you money on fees
2. **Not running continuously** - no 24/7 service configured
3. **Over-checking positions** every 5 minutes - causing panic closes
4. **Closing on tiny pullbacks** - not letting winners run

## What's Fixed ✅

### 1. **15-Minute Minimum Hold Time**
- Bot CANNOT close positions for first 15 minutes
- Prevents immediate panic closes
- Gives trades room to develop

### 2. **Reduced Monitoring**  
- Changed from 5-minute to 15-minute position checks
- Less over-management = better performance
- AI less tempted to close on noise

### 3. **Stricter AI Rules**
AI now only closes when:
- **Clear trend reversal** (multiple opposing candles)
- **Major support/resistance broken** with momentum
- **Clear invalidation** of the setup

AI will NOT close for:
- Small pullbacks (normal)
- Single red/green candle (noise)
- Just because target hit (lets winners run)

### 4. **24/7 Systemd Service**
- Runs in background continuously
- Auto-restarts on crashes
- Starts on system boot
- Full logging

## Quick Start (3 Commands)

```bash
# 1. Setup 24/7 service (one time)
sudo /workspaces/TradingETH-/scripts/setup_24_7.sh

# 2. Check it's running
./scripts/bot status

# 3. Watch live logs
./scripts/bot logs
```

## Daily Commands

```bash
# Check status
./scripts/bot status

# View live logs
./scripts/bot logs

# Check current position
./scripts/bot position

# Emergency stop
./scripts/bot stop

# Start again
./scripts/bot start

# Full health check
./scripts/bot health
```

## How It Works Now

### Opening Trades
1. ✅ All filters pass (time, volatility, multi-timeframe)
2. ✅ AI identifies setup
3. ✅ Position opened with SL/TP
4. ⏱️ **15-minute minimum hold timer starts**

### Monitoring Trades  
1. 🕐 Every **15 minutes** (not 5!) bot checks position
2. 🛡️ **Minimum hold time enforced** - won't close before 15 min
3. 🧠 AI evaluates: "Is there STRONG evidence of reversal?"
4. 💪 DEFAULT = HOLD unless clear reversal confirmed

### Closing Trades
Bot only closes when:
- ✅ Minimum 15 minutes passed
- ✅ Stop loss hit OR
- ✅ Take profit hit OR  
- ✅ AI sees **clear reversal pattern**

## What You'll See Different

### Before (BAD):
```
09:00: Long opened @ $3000
09:05: AI checking... small red candle
09:05: Position closed @ $2995 (-$5 + fees = -$10)
09:10: Price dumps to $2900 (like you predicted!)
```

### After (GOOD):
```
09:00: Long opened @ $3000
09:05: [minimum hold time - not checking]
09:10: [minimum hold time - not checking]
09:15: AI checking... small red candle = NOISE, holding
09:30: AI checking... trend intact, holding  
09:45: AI checking... still bullish, holding
10:00: Take profit hit @ $3080 (+$80 profit!)
```

## Configuration

### Current Settings
- **Minimum hold**: 15 minutes
- **Check interval**: 15 minutes  
- **Max trades/hour**: 2
- **Cooldown**: 10 minutes

### To Adjust Hold Time
Edit `src/runner_live.py` line ~89:
```python
minimum_hold_minutes = 15  # 5-30 recommended
```

### To Adjust Check Interval
Edit `src/runner_live.py` line ~518:
```python
await asyncio.sleep(900)  # 900=15min, 1200=20min
```

## Monitoring Your Bot

### Real-Time Monitoring
```bash
# Live logs with position updates
./scripts/bot logs

# Just errors
./scripts/bot errors

# Current position
./scripts/bot position
```

### What to Look For

**✅ Good Signs:**
- Positions held 15+ minutes
- "refusing to close" in logs (enforcing minimum time)
- AI citing "trend intact" when holding
- Clear reversal patterns when closing

**⚠️ Warning Signs:**
- Closing exactly at 15 minutes (AI wanted out earlier)
- Frequent "flip-flopping" between long/short
- Many consecutive losses
- Filters always blocking trades

## Emergency Procedures

### Stop Everything
```bash
./scripts/bot stop
```

### Close Position Manually  
```bash
./scripts/bot close
```

### Restart Fresh
```bash
./scripts/bot restart
rm data/claude_history.jsonl  # Clear AI memory
```

## Files Changed

1. **src/runner_live.py** - Added minimum hold time, reduced checking frequency
2. **src/ai_client.py** - Stricter AI closing rules  
3. **scripts/tradingbot.service.example** - Proper systemd config
4. **scripts/setup_24_7.sh** - Automated setup script (NEW)
5. **scripts/bot** - Quick control commands (NEW)

## Testing Before Going Live

```bash
# 1. Check your .env is configured
cat .env | grep -E "PAPER_MODE|HYPERLIQUID_TESTNET"

# 2. Make sure paper mode is ON for testing
PAPER_MODE=True

# 3. Start bot
./scripts/bot start

# 4. Watch it for 1 hour
./scripts/bot logs

# 5. Verify it's not panic closing
# Look for "refusing to close" messages in logs
```

## Support & Debugging

### Bot won't start
```bash
# Check logs for errors
sudo journalctl -u tradingbot -n 50 --no-pager

# Verify .env exists
ls -la .env

# Check Python environment
source .venv/bin/activate && python --version
```

### Bot keeps closing trades
```bash
# Check if minimum hold time is working
./scripts/bot logs | grep "refusing to close"

# If not seen, increase minimum hold time to 20-30 minutes
```

### Need more details
- Full guide: `BOT_OPERATION_GUIDE.md`
- Code changes: Check git diff
- Configuration: `.env` file

---

## Summary

Your bot now:
- ✅ Runs 24/7 automatically
- ✅ Won't close trades immediately (15 min minimum)
- ✅ Checks positions less frequently (15 min intervals)
- ✅ Only closes on strong reversal signals
- ✅ Auto-restarts if it crashes
- ✅ Has easy management commands

**Next Step**: Run `sudo ./scripts/setup_24_7.sh` to get it running 24/7!

The issue where it "opened then immediately closed" is now **IMPOSSIBLE** due to the 15-minute minimum hold enforcement. Even if the AI screams to close, the bot will refuse until 15 minutes passes.
