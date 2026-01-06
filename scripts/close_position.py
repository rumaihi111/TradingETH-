"""Manually close current position"""

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
    print("🔍 CHECKING CURRENT POSITION")
    print("="*80)
    
    # Get current positions
    positions = ex.positions()
    
    if not positions:
        print("\n❌ No open positions to close")
        return
    
    pos = positions[0]
    side = "LONG" if pos.get("size", 0) > 0 else "SHORT"
    size = abs(pos.get("size", 0))
    entry = pos.get("entry_price", 0)
    
    print(f"\n📍 Current Position:")
    print(f"   Side: {side}")
    print(f"   Size: {size:.4f} ETH")
    print(f"   Entry: ${entry:.2f}")
    print(f"   Unrealized P&L: ${pos.get('unrealized_pnl', 0):+.2f}")
    
    # Confirm close
    print(f"\n⚠️  About to CLOSE {side} position of {size:.4f} ETH")
    confirm = input("Type 'yes' to confirm: ")
    
    if confirm.lower() != 'yes':
        print("\n❌ Close cancelled")
        return
    
    print(f"\n🚨 Closing {side} position...")
    result = ex.close_position("ETH")
    
    print(f"\n✅ Position closed!")
    print(f"   Result: {result}")
    
    if "pnl" in result:
        print(f"   Realized P&L: ${result['pnl']:+.2f}")
    
    if "close_price" in result and result["close_price"]:
        print(f"   Close Price: ${result['close_price']:.2f}")
        pnl = (result['close_price'] - entry) * size if side == "LONG" else (entry - result['close_price']) * size
        print(f"   Calculated P&L: ${pnl:+.2f}")
    
    print("\n" + "="*80)
    print("✅ POSITION CLOSED - Next trade will use 80% position sizing")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
