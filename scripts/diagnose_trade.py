#!/usr/bin/env python3
"""
Diagnostic script to verify Hyperliquid trading is working correctly.
Run this to check if your trades are actually being placed on Hyperliquid.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_settings
from src.exchange_hyperliquid import HyperliquidClient


def diagnose():
    print("=" * 60)
    print("🔍 HYPERLIQUID TRADING DIAGNOSTICS")
    print("=" * 60)
    
    # 1. Load settings
    print("\n📋 Step 1: Loading settings...")
    try:
        settings = load_settings()
        print(f"   ✅ Settings loaded")
        print(f"   📌 Paper Mode: {settings.paper_mode}")
        print(f"   📌 Testnet: {settings.hyperliquid_testnet}")
        print(f"   📌 Trading Pair: {settings.trading_pair}")
        print(f"   📌 Has Private Key: {bool(settings.private_key)}")
        print(f"   📌 Account Address: {settings.account_address or 'Not set (will use API wallet)'}")
        
        if settings.paper_mode:
            print("\n" + "⚠️" * 20)
            print("⚠️  PAPER_MODE=true - Trades are NOT going to Hyperliquid!")
            print("⚠️  Set PAPER_MODE=false in your environment to trade live.")
            print("⚠️" * 20)
            return
            
    except Exception as e:
        print(f"   ❌ Failed to load settings: {e}")
        return
    
    # 2. Connect to Hyperliquid
    print("\n📋 Step 2: Connecting to Hyperliquid...")
    try:
        ex = HyperliquidClient(
            private_key_hex=settings.private_key,
            testnet=settings.hyperliquid_testnet,
            base_url_override=settings.hyperliquid_base_url,
            account_address=settings.account_address,
        )
        print(f"   ✅ Connected to {'TESTNET' if settings.hyperliquid_testnet else 'MAINNET'}")
        print(f"   📌 API Wallet: {ex.wallet.address}")
        print(f"   📌 Trading Account: {ex.account_address}")
        
        if ex.wallet.address != ex.account_address:
            print(f"   ℹ️  Using API wallet to trade on behalf of: {ex.account_address}")
            
    except Exception as e:
        print(f"   ❌ Failed to connect: {e}")
        return
    
    # 3. Check account
    print("\n📋 Step 3: Checking account balance...")
    try:
        account = ex.account()
        equity = account.get("equity", 0)
        print(f"   ✅ Account equity: ${equity:.2f}")
        
        if equity < 10:
            print(f"   ⚠️  Warning: Low equity. Minimum for trading is ~$10-11")
            
    except Exception as e:
        print(f"   ❌ Failed to get account: {e}")
        return
    
    # 4. Check positions
    print("\n📋 Step 4: Checking open positions...")
    try:
        positions = ex.positions()
        if positions:
            for p in positions:
                side = "LONG" if p.get('size', 0) > 0 else "SHORT"
                print(f"   📊 {side}: {abs(p.get('size', 0)):.4f} {p.get('symbol')} @ ${p.get('entry', 0):.4f}")
                print(f"      Unrealized P&L: ${p.get('unrealized', 0):+.2f}")
        else:
            print(f"   ℹ️  No open positions")
    except Exception as e:
        print(f"   ❌ Failed to get positions: {e}")
    
    # 5. Check open orders
    print("\n📋 Step 5: Checking open orders...")
    try:
        orders = ex.get_open_orders()
        if orders:
            print(f"   📝 Found {len(orders)} open orders:")
            for o in orders[:5]:  # Show first 5
                print(f"      {o.get('coin')}: {o.get('side')} {o.get('sz')} @ ${o.get('limitPx')}")
        else:
            print(f"   ℹ️  No open orders")
    except Exception as e:
        print(f"   ❌ Failed to get orders: {e}")
    
    # 6. Check recent fills/trades
    print("\n📋 Step 6: Checking recent trade history...")
    try:
        fills = ex.info.user_fills(ex.account_address)
        if fills:
            print(f"   📜 Last 5 fills:")
            for f in fills[:5]:
                side = f.get('dir', f.get('side', ''))
                print(f"      {f.get('coin')}: {side} {f.get('sz')} @ ${f.get('px')}")
                print(f"         Time: {f.get('time')}, Fee: ${f.get('fee', 0):.4f}")
        else:
            print(f"   ℹ️  No recent fills found")
    except Exception as e:
        print(f"   ⚠️  Could not fetch fills: {e}")
    
    print("\n" + "=" * 60)
    print("📋 DIAGNOSIS COMPLETE")
    print("=" * 60)
    
    # Summary
    print("\n🔑 COMMON ISSUES:")
    print("1. PAPER_MODE=true → Trades only simulate, not sent to exchange")
    print("2. Wrong API wallet → Check PRIVATE_KEY matches your API wallet")
    print("3. No permissions → API wallet may not have trading permissions")
    print("4. ACCOUNT_ADDRESS mismatch → Should be your main trading account")
    print("5. TESTNET=true but looking at mainnet → Check HYPERLIQUID_TESTNET")
    print("6. Insufficient margin → Need at least ~$11 to open a position")


if __name__ == "__main__":
    diagnose()
