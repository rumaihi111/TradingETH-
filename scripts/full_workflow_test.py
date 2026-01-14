#!/usr/bin/env python3
"""Test full workflow with timing breakdown"""
import os
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ccxt
from src.config import load_settings
from src.ai_client import AISignalClient
from src.history_store import HistoryStore

print("🧪 Full Workflow Test with Timing\n")

settings = load_settings()
print("✅ Settings loaded\n")

# Fetch candles
print("📊 Fetching 130 candles...")
fetch_start = time.time()
exchange = ccxt.kucoin()
ohlcv = exchange.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=130)
candles = [{"ts": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]} for c in ohlcv]
fetch_time = time.time() - fetch_start
print(f"✅ Got {len(candles)} candles in {fetch_time:.2f}s\n")

# Initialize AI
print("🤖 Initializing AI client...")
init_start = time.time()
history = HistoryStore()
ai = AISignalClient(
    api_key=settings.anthropic_api_key,
    history_store=history,
    venice_api_key=settings.venice_api_key,
    venice_endpoint=settings.venice_endpoint,
    venice_model=settings.venice_model,
)
init_time = time.time() - init_start
print(f"✅ AI initialized in {init_time:.2f}s\n")

# Full workflow
print("="*80)
print("RUNNING FULL WORKFLOW (Venice → Claude)")
print("="*80 + "\n")

workflow_start = time.time()
try:
    decision = ai.fetch_signal(candles, current_position=None)
    workflow_time = time.time() - workflow_start
    
    print(f"\n{'='*80}")
    print(f"✅ WORKFLOW COMPLETED in {workflow_time:.2f}s")
    print(f"{'='*80}\n")
    
    print("📋 FINAL DECISION:")
    print(f"   Side: {decision.get('side', 'N/A').upper()}")
    if decision.get('venice_pattern'):
        print(f"   Venice Pattern: {decision.get('venice_pattern')}")
    if decision.get('venice_reason'):
        print(f"   Venice Reason: {decision.get('venice_reason')}")
    print(f"   Stop Loss: {decision.get('stop_loss_pct', 0)*100:.2f}%")
    print(f"   Take Profit: {decision.get('take_profit_pct', 0)*100:.2f}%")
    print(f"   Max Slippage: {decision.get('max_slippage_pct', 0)*100:.2f}%")
    
    print("\n✅ VENICE → CLAUDE PIPELINE WORKING!\n")
    
    print("Timing Breakdown:")
    print(f"  - Fetch candles: {fetch_time:.2f}s")
    print(f"  - Initialize AI: {init_time:.2f}s")
    print(f"  - Full workflow: {workflow_time:.2f}s")
    print(f"  - TOTAL: {fetch_time + init_time + workflow_time:.2f}s")
    
except Exception as e:
    workflow_time = time.time() - workflow_start
    print(f"\n❌ WORKFLOW FAILED after {workflow_time:.2f}s")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
