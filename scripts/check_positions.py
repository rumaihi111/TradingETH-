#!/usr/bin/env python3
"""Quick script to check current Hyperliquid positions and account state."""

import sys
import os
sys.path.insert(0, '/workspaces/TradingETH-')

# Load env from Railway or local
from dotenv import load_dotenv
load_dotenv()

from src.config import load_settings
from src.exchange_hyperliquid import HyperliquidClient

def main():
    # Check for required env vars
    if not os.getenv('PRIVATE_KEY'):
        print("❌ PRIVATE_KEY not set. This script needs Railway env vars.")
        print("Run on Railway or set env vars locally.")
        return
    
    settings = load_settings()
    client = HyperliquidClient(settings)
    
    print("=" * 60)
    print("HYPERLIQUID ACCOUNT STATUS")
    print("=" * 60)
    
    # Get account info
    account = client.account()
    print(f"\n💰 Account Equity: ${account['equity']:.2f}")
    
    # Get raw state for detailed info
    raw_state = account['raw_state']
    margin_summary = raw_state.get('marginSummary', {})
    
    print(f"   Account Value: ${float(margin_summary.get('accountValue', 0)):.2f}")
    print(f"   Total Margin Used: ${float(margin_summary.get('totalMarginUsed', 0)):.2f}")
    print(f"   Total Notional Pos: ${float(margin_summary.get('totalNtlPos', 0)):.2f}")
    print(f"   Total Raw USD: ${float(margin_summary.get('totalRawUsd', 0)):.2f}")
    
    # Get positions
    positions = client.positions()
    print(f"\n📊 Open Positions: {len(positions)}")
    print("-" * 60)
    
    if positions:
        for pos in positions:
            side = "LONG" if float(pos['size']) > 0 else "SHORT"
            size = abs(float(pos['size']))
            entry_price = float(pos['entry_price'])
            unrealized = float(pos['unrealized_pnl'])
            notional = size * entry_price
            
            print(f"\n   {pos['symbol']}:")
            print(f"   Side: {side}")
            print(f"   Size: {size:.4f} ETH")
            print(f"   Entry Price: ${entry_price:.2f}")
            print(f"   Notional Value: ${notional:.2f}")
            print(f"   Unrealized P&L: ${unrealized:.2f}")
            
            # Calculate leverage
            if float(margin_summary.get('totalMarginUsed', 0)) > 0:
                effective_leverage = notional / float(margin_summary.get('totalMarginUsed', 0))
                print(f"   Effective Leverage: {effective_leverage:.1f}x")
    else:
        print("   No open positions")
    
    # Show asset positions from raw state
    print("\n" + "=" * 60)
    print("RAW ASSET POSITIONS")
    print("=" * 60)
    asset_positions = raw_state.get('assetPositions', [])
    for ap in asset_positions:
        position_data = ap.get('position', {})
        coin = position_data.get('coin', 'UNKNOWN')
        szi = position_data.get('szi', '0')
        entry_px = position_data.get('entryPx', '0')
        
        print(f"\n   Asset: {coin}")
        print(f"   Size: {szi}")
        print(f"   Entry Price: {entry_px}")
        print(f"   Raw data: {position_data}")

if __name__ == "__main__":
    main()
