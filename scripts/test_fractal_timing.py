#!/usr/bin/env python3
"""Test just fractal brain timing"""
import os
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ccxt
from src.fractal_brain import NestedFractalBrain

print("🧪 Testing Fractal Brain Performance\n")

# Fetch candles
print("📊 Fetching 130 candles...")
exchange = ccxt.kucoin()
ohlcv = exchange.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=130)
candles = [{"ts": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]} for c in ohlcv]
print(f"✅ Got {len(candles)} candles\n")

# Test fractal brain
brain = NestedFractalBrain(min_similarity=0.75, scale_ratio_min=2.0)

print("🧠 Running fractal brain analysis...")
start = time.time()
result = brain.analyze(candles)
elapsed = time.time() - start

print(f"✅ Fractal brain completed in {elapsed:.2f}s\n")
print(f"Result: {result.get('fractals_found')} - {result.get('reason', 'N/A')}")

if elapsed > 5:
    print(f"\n⚠️  WARNING: Fractal brain is SLOW ({elapsed:.2f}s)")
    print("   This is blocking Venice and Claude!")
