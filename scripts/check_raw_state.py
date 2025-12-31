#!/usr/bin/env python3
"""Direct query to Hyperliquid to see raw account state"""

import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, '/workspaces/TradingETH-')

from dotenv import load_dotenv
load_dotenv()

from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.utils import constants

def main():
    private_key = os.getenv('PRIVATE_KEY')
    if not private_key:
        print("❌ PRIVATE_KEY not set")
        return
    
    wallet = Account.from_key(private_key)
    base_url = constants.MAINNET_API_URL
    info = Info(base_url, skip_ws=True)
    
    print(f"🔍 Querying: {wallet.address}")
    print("=" * 70)
    
    # Get raw state
    state = info.user_state(wallet.address)
    
    print("\n📊 MARGIN SUMMARY:")
    print(json.dumps(state.get('marginSummary', {}), indent=2))
    
    print("\n📦 ASSET POSITIONS:")
    asset_positions = state.get('assetPositions', [])
    print(f"Count: {len(asset_positions)}")
    
    if asset_positions:
        for i, ap in enumerate(asset_positions):
            print(f"\n--- Position {i+1} ---")
            print(json.dumps(ap, indent=2))
    else:
        print("⚠️ No asset positions found")
    
    print("\n🔍 FULL RAW STATE:")
    print(json.dumps(state, indent=2))

if __name__ == "__main__":
    main()
