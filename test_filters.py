#!/usr/bin/env python
"""
Test script to demonstrate all the new filters in action
"""
import os
import asyncio
from datetime import datetime

# Set up test environment
os.environ['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', 'test_key')
os.environ['PAPER_MODE'] = 'true'
os.environ['PAPER_INITIAL_EQUITY'] = '10000'
os.environ['TELEGRAM_TOKEN'] = ''
os.environ['TELEGRAM_CHAT_ID'] = ''

from src.config import load_settings
from src.ai_client import AISignalClient
from src.history_store import HistoryStore
import ccxt

async def test_filters():
    print("="*80)
    print("🧪 TESTING ALL FILTERS WITH LIVE DATA")
    print("="*80)
    
    # Load settings
    settings = load_settings()
    print(f"\n📋 Configuration:")
    print(f"   Timeframe: {settings.timeframe}")
    print(f"   Bias Timeframe: {settings.bias_timeframe}")
    print(f"   MTF Alignment: {settings.require_timeframe_alignment}")
    print(f"   Volatility Gate: {settings.enable_volatility_gate}")
    print(f"   Time Filter: {settings.enable_time_filter}")
    print(f"   Session Context: {settings.enable_session_context}")
    
    # Initialize AI client with all filters
    history = HistoryStore()
    ai = AISignalClient(
        api_key=settings.anthropic_api_key,
        history_store=history,
        require_timeframe_alignment=settings.require_timeframe_alignment,
        bias_lookback=settings.bias_lookback,
        enable_volatility_gate=settings.enable_volatility_gate,
        atr_period=settings.atr_period,
        atr_compression_threshold=settings.atr_compression_threshold,
        require_volatility_expansion=settings.require_volatility_expansion,
        enable_time_filter=settings.enable_time_filter,
        timezone=settings.timezone,
        enable_session_context=settings.enable_session_context,
        session_start_hour=settings.session_start_hour,
        session_start_minute=settings.session_start_minute,
        entry_mode=settings.entry_mode,
        stop_atr_multiplier=settings.stop_atr_multiplier,
        min_rr_ratio=settings.min_rr_ratio,
        time_stop_candles=settings.time_stop_candles,
    )
    
    print(f"\n✅ AI Client initialized with all filters")
    
    # Fetch live candles
    print(f"\n📊 Fetching live candle data...")
    spot = ccxt.kucoin()
    
    # Fetch 5m candles
    ohlcv = spot.fetch_ohlcv("ETH/USDT", timeframe=settings.timeframe, limit=settings.candle_limit)
    candles = [{"ts": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]} for c in ohlcv]
    print(f"   5m candles: {len(candles)} fetched")
    
    # Fetch 15m candles
    ohlcv_15m = spot.fetch_ohlcv("ETH/USDT", timeframe=settings.bias_timeframe, limit=settings.bias_candle_limit)
    candles_15m = [{"ts": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]} for c in ohlcv_15m]
    print(f"   15m candles: {len(candles_15m)} fetched")
    
    current_price = candles[-1]['close']
    print(f"   Current ETH price: ${current_price:.2f}")
    
    # Run AI analysis (this will show all filter output)
    print(f"\n{'='*80}")
    print("🤖 RUNNING AI ANALYSIS WITH ALL FILTERS")
    print(f"{'='*80}\n")
    
    try:
        decision = ai.fetch_signal(candles, candles_15m=candles_15m, current_position=None)
        
        print(f"\n{'='*80}")
        print("📊 FINAL DECISION")
        print(f"{'='*80}")
        print(f"   Side: {decision.get('side', 'unknown').upper()}")
        print(f"   Stop Loss: {decision.get('stop_loss_pct', 0)*100:.2f}%")
        print(f"   Take Profit: {decision.get('take_profit_pct', 0)*100:.2f}%")
        print(f"   Max Slippage: {decision.get('max_slippage_pct', 0)*100:.2f}%")
        
        if 'reason' in decision:
            print(f"   Reason: {decision['reason']}")
        if 'override_reason' in decision:
            print(f"   ⚠️  Override: {decision['override_reason']}")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("✅ FILTER TEST COMPLETE")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(test_filters())
