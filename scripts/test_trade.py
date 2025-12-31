#!/usr/bin/env python3
"""Quick manual trade test - opens SHORT position immediately"""

import sys
import time
sys.path.insert(0, '/workspaces/TradingETH-')

from src.config import load_settings
from src.exchange_hyperliquid import HyperliquidClient

def main():
    print("🚀 MANUAL TRADE TEST")
    print("=" * 70)
    
    settings = load_settings()
    
    # Initialize with account_address (empty = uses API wallet)
    client = HyperliquidClient(
        private_key_hex=settings.private_key,
        testnet=settings.hyperliquid_testnet,
        base_url_override=settings.hyperliquid_base_url,
        account_address=settings.account_address,
    )
    
    # Check before
    print("\n📊 BEFORE:")
    account = client.account()
    equity = account['equity']
    print(f"Equity: ${equity:.2f}")
    
    pos_before = client.positions()
    print(f"Open positions: {len(pos_before)}")
    
    # Place SHORT order (0.0037 ETH ≈ $11 at $3000)
    print("\n🔨 PLACING SHORT ORDER:")
    print("Symbol: ETH")
    print("Side: SHORT")
    print("Size: 0.0037 ETH")
    print("Slippage: 0.5%")
    
    result = client.place_market(
        symbol="ETH",
        side="short",
        size=0.0037,
        max_slippage_pct=0.5
    )
    
    print(f"\n📊 Order Result:")
    print(result)
    
    # Wait and check 5 times
    print("\n⏳ Checking for position...")
    for i in range(5):
        time.sleep(1)
        pos_after = client.positions()
        
        if pos_after:
            pos = pos_after[0]
            print(f"\n✅ SUCCESS! Position found after {i+1} seconds:")
            print(f"   Symbol: {pos.get('symbol', pos.get('coin'))}")
            print(f"   Size: {pos['size']:.4f} ETH")
            print(f"   Side: {'LONG' if pos['size'] > 0 else 'SHORT'}")
            print(f"   Entry: ${pos.get('entry_price', pos.get('entry', 0)):.2f}")
            print(f"   Unrealized P&L: ${pos.get('unrealized_pnl', pos.get('unrealized', 0)):+.4f}")
            
            # Check new equity
            account_after = client.account()
            print(f"\n💰 Account after:")
            print(f"   Equity: ${account_after['equity']:.2f}")
            return
        else:
            print(f"   Attempt {i+1}/5: No position yet...")
    
    print("\n❌ FAILED: No position found after 5 seconds")
    print("This means:")
    print("  - Order was rejected")
    print("  - Position size too small")
    print("  - Immediate liquidation")
    print("  - Wrong wallet being queried")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
