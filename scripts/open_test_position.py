#!/usr/bin/env python3
"""Manually open a test position and verify tracking"""

import sys
import time
sys.path.insert(0, '/workspaces/TradingETH-')

from dotenv import load_dotenv
load_dotenv()

from src.config import load_settings
from src.exchange_hyperliquid import HyperliquidClient

def main():
    print("🚀 Opening manual test position...")
    print("=" * 70)
    
    settings = load_settings()
    client = HyperliquidClient(
        private_key_hex=settings.private_key,
        testnet=settings.hyperliquid_testnet,
        base_url_override=settings.hyperliquid_base_url,
    )
    
    # Check initial balance
    print("\n📊 BEFORE TRADE:")
    account = client.account()
    equity = account['equity']
    print(f"Equity: ${equity:.2f}")
    
    positions_before = client.positions()
    print(f"Positions: {len(positions_before)}")
    
    # Open a small SHORT position (0.004 ETH ≈ $12 at $3000)
    # This will use ~$0.60 margin at 20x leverage
    print("\n🔨 PLACING ORDER:")
    print("Side: SHORT")
    print("Size: 0.0040 ETH")
    print("Slippage: 0.5%")
    
    result = client.place_market(
        symbol="ETH",
        side="short",
        size=0.0040,
        max_slippage_pct=0.5
    )
    
    print(f"\n📊 Order Result:")
    print(result)
    
    # Wait 3 seconds for position to settle
    print("\n⏳ Waiting 3 seconds for settlement...")
    time.sleep(3)
    
    # Check position
    print("\n📊 AFTER TRADE:")
    account = client.account()
    equity_after = account['equity']
    print(f"Equity: ${equity_after:.2f}")
    
    positions_after = client.positions()
    print(f"Positions: {len(positions_after)}")
    
    if positions_after:
        pos = positions_after[0]
        print(f"\n✅ POSITION OPENED:")
        print(f"   Symbol: {pos.get('symbol', pos.get('coin'))}")
        print(f"   Size: {pos['size']:.4f} ETH")
        print(f"   Side: {'LONG' if pos['size'] > 0 else 'SHORT'}")
        print(f"   Entry Price: ${pos.get('entry_price', pos.get('entry', 0)):.2f}")
        print(f"   Unrealized P&L: ${pos.get('unrealized_pnl', pos.get('unrealized', 0)):+.2f}")
        print(f"   Leverage: {pos.get('leverage', 'N/A')}x")
    else:
        print("\n❌ No position found after trade!")
        print("This could mean:")
        print("  - Order was rejected")
        print("  - Position closed immediately")
        print("  - Not enough margin")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
