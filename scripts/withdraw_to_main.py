#!/usr/bin/env python3
"""Withdraw funds from API wallet to main wallet"""

import os
import sys
sys.path.insert(0, '/workspaces/TradingETH-')

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants

def main():
    print("💸 WITHDRAWING FROM API WALLET TO MAIN WALLET")
    print("=" * 70)
    
    # Get private key directly from env (bypass config)
    private_key = os.getenv('PRIVATE_KEY')
    if not private_key:
        print("❌ ERROR: PRIVATE_KEY environment variable not set")
        return
    
    # Setup API wallet
    wallet = Account.from_key(private_key)
    base_url = constants.MAINNET_API_URL
    info = Info(base_url, skip_ws=True)
    exchange = Exchange(wallet, base_url, account_address=wallet.address)
    
    print(f"\n📤 From (API wallet): {wallet.address}")
    print(f"📥 To (Main wallet): 0x24ff8C760c6433A7507a4C5352e81fCa28806762")
    
    # Check current balance
    state = info.user_state(wallet.address)
    equity = float(state.get('marginSummary', {}).get('accountValue', 0))
    withdrawable = float(state.get('withdrawable', 0))
    
    print(f"\n💰 API Wallet Balance:")
    print(f"   Total Equity: ${equity:.2f}")
    print(f"   Withdrawable: ${withdrawable:.2f}")
    
    if withdrawable < 1:
        print(f"\n❌ ERROR: Not enough withdrawable balance (${withdrawable:.2f})")
        print("   This could mean funds are locked in positions or pending settlements")
        return
    
    # Withdraw all available funds
    amount = withdrawable
    destination = "0x24ff8C760c6433A7507a4C5352e81fCa28806762"
    
    print(f"\n🔄 Initiating withdrawal...")
    print(f"   Amount: ${amount:.2f} USDC")
    print(f"   Destination: {destination}")
    
    # Use withdraw_from_bridge to send to external address
    result = exchange.withdraw_from_bridge(amount, destination)
    
    print(f"\n📊 Withdrawal Result:")
    print(result)
    
    if result.get('status') == 'ok':
        print(f"\n✅ SUCCESS! Withdrawal initiated")
        print(f"   ${amount:.2f} USDC sent to {destination}")
        print(f"\n   Note: May take a few minutes to appear in destination wallet")
    else:
        print(f"\n❌ FAILED: {result}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
