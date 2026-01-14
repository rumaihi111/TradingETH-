#!/usr/bin/env python3
"""Fast Venice vision test with chart"""
import os
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ccxt
from src.config import load_settings
from src.ai_client import AISignalClient
from src.history_store import HistoryStore

print("🧪 Fast Venice Vision Test\n")

settings = load_settings()

if not settings.venice_api_key:
    print("❌ VENICE_API_KEY not set")
    sys.exit(1)

print("✅ Venice API key present")

# Fetch just 130 candles
print("📊 Fetching 130 candles...")
exchange = ccxt.kucoin()
ohlcv = exchange.fetch_ohlcv("ETH/USDT", timeframe="5m", limit=130)
candles = [{"ts": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]} for c in ohlcv]
print(f"✅ Got {len(candles)} candles\n")

# Initialize AI client
history = HistoryStore()
ai = AISignalClient(
    api_key=settings.anthropic_api_key,
    history_store=history,
    venice_api_key=settings.venice_api_key,
    venice_endpoint=settings.venice_endpoint,
    venice_model=settings.venice_model,
)

print("🎨 Generating chart image...")
chart_start = time.time()
chart_image = ai._get_chart_image(candles)
chart_time = time.time() - chart_start
print(f"✅ Chart generated in {chart_time:.2f}s\n")

if not chart_image:
    print("❌ Chart generation failed")
    sys.exit(1)

print("🤖 Calling Venice with chart image...")
venice_start = time.time()
try:
    venice_result = ai._get_direction_with_venice(candles, chart_image, {"fractals_found": False, "reason": "test"})
    venice_time = time.time() - venice_start
    
    print(f"✅ Venice responded in {venice_time:.2f}s\n")
    
    if venice_result:
        print("📋 VENICE DECISION:")
        print(f"   Side: {venice_result.get('side', 'N/A').upper()}")
        print(f"   Pattern: {venice_result.get('pattern', 'N/A')}")
        print(f"   Reason: {venice_result.get('reason', 'N/A')}")
        print("\n✅ Venice vision is WORKING!")
    else:
        print("❌ Venice returned no decision")
        sys.exit(1)
        
except Exception as e:
    venice_time = time.time() - venice_start
    print(f"❌ Venice failed after {venice_time:.2f}s: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
