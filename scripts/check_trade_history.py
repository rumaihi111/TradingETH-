"""Check complete trade history from Hyperliquid"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_settings
from src.exchange_hyperliquid import HyperliquidClient


def main():
    settings = load_settings()
    
    ex = HyperliquidClient(
        private_key_hex=settings.private_key,
        testnet=settings.hyperliquid_testnet,
        account_address=settings.account_address,
    )
    
    print("\n" + "="*80)
    print("📊 HYPERLIQUID TRADE HISTORY")
    print("="*80)
    
    # Get account state
    account = ex.account()
    print(f"\n💰 Current Account:")
    print(f"   Balance: ${account.get('equity', 0):.2f}")
    
    # Get current positions
    positions = ex.positions()
    print(f"\n📍 Current Positions: {len(positions)}")
    for pos in positions:
        side = "LONG" if pos.get("size", 0) > 0 else "SHORT"
        print(f"   {side} {abs(pos.get('size', 0)):.4f} ETH @ ${pos.get('entry_price', 0):.2f}")
        print(f"   Position Value: ${abs(pos.get('size', 0)) * pos.get('entry_price', 0):.2f}")
        print(f"   Leverage: {pos.get('leverage', 0):.1f}x")
        print(f"   Unrealized P&L: ${pos.get('unrealized_pnl', 0):+.2f}")
    
    # Try to get trade history from Hyperliquid API
    try:
        # Get user state which includes trade history
        user_state = ex.info.user_state(ex.account_address)
        
        if "assetPositions" in user_state:
            print(f"\n📈 Asset Positions:")
            for asset_pos in user_state.get("assetPositions", []):
                print(f"   {asset_pos}")
        
        # Check for fills (executed trades)
        print(f"\n🔍 Attempting to fetch trade fills...")
        
        # Hyperliquid's info API for user fills
        try:
            fills = ex.info.user_fills(ex.account_address)
            print(f"\n✅ Recent Fills (Last 100 trades):")
            print(f"   Total fills found: {len(fills)}")
            
            if fills:
                print(f"\n{'Time':<20} {'Side':<6} {'Size':<12} {'Price':<12} {'Value':<12} {'Fee':<10}")
                print("-" * 80)
                
                for fill in fills[:20]:  # Show last 20
                    timestamp = fill.get('time', 0)
                    import datetime
                    time_str = datetime.datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M:%S')
                    side = fill.get('side', 'N/A')
                    size = float(fill.get('sz', 0))
                    price = float(fill.get('px', 0))
                    value = size * price
                    fee = float(fill.get('fee', 0))
                    
                    print(f"{time_str:<20} {side:<6} {size:<12.4f} ${price:<11.2f} ${value:<11.2f} ${fee:<9.2f}")
            else:
                print("   No fills found")
                
        except Exception as e:
            print(f"   ⚠️ Could not fetch fills: {e}")
        
    except Exception as e:
        print(f"\n❌ Error fetching user state: {e}")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
