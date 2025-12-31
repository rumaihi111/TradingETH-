from typing import Any, Dict, List, Optional

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants


class HyperliquidClient:
    def __init__(
        self,
        private_key_hex: str,
        testnet: bool = True,
        base_url_override: str = "",
        skip_ws: bool = True,
    ):
        if private_key_hex.startswith("0x"):
            private_key_hex = private_key_hex
        self.wallet = Account.from_key(private_key_hex)
        base_url = base_url_override or (constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL)
        self.info = Info(base_url, skip_ws=skip_ws)
        self.exchange = Exchange(self.wallet, base_url, account_address=self.wallet.address)
        
        # Note: Bot assumes 10x leverage - set this manually in Hyperliquid UI
        print("⚠️ IMPORTANT: Ensure your Hyperliquid account is set to 10x leverage (Cross Margin)")

    def account(self) -> Dict[str, Any]:
        """Get account state with equity"""
        print(f"🔍 Querying wallet address: {self.wallet.address}")
        state = self.info.user_state(self.wallet.address)
        print(f"🔍 Raw marginSummary: {state.get('marginSummary', {})}")
        summary = state.get("marginSummary", {})
        equity = float(summary.get("accountValue", 0))
        print(f"✅ Hyperliquid connected: ${equity:.2f} USDC")
        return {"equity": equity, "raw_state": state}

    def positions(self) -> List[Dict[str, Any]]:
        state = self.account().get("raw_state", {})
        positions = []
        asset_positions = state.get("assetPositions", [])
        
        print(f"🔍 Raw assetPositions count: {len(asset_positions)}")
        
        for p in asset_positions:
            pos = p.get("position") or {}
            if not pos:
                continue
            
            size = float(pos.get("szi", 0))
            # Skip positions with zero size
            if abs(size) < 0.0001:
                continue
                
            position_data = {
                "symbol": pos.get("coin"),
                "coin": pos.get("coin"),
                "size": size,
                "entry": float(pos.get("entryPx") or 0),
                "entry_price": float(pos.get("entryPx") or 0),
                "unrealized": float(pos.get("unrealizedPnl") or 0),
                "unrealized_pnl": float(pos.get("unrealizedPnl") or 0),
                "leverage": float(pos.get("leverage", {}).get("value", 0)) if isinstance(pos.get("leverage"), dict) else 0,
            }
            
            print(f"✅ Found position: {position_data}")
            positions.append(position_data)
        
        if not positions:
            print("❌ No open positions found")
            
        return positions

    def place_market(self, symbol: str, side: str, size: float, max_slippage_pct: float, price: float = None) -> Dict[str, Any]:
        """Place market order (price param for API compatibility, not used)"""
        is_buy = side.lower() == "long"
        slippage = max_slippage_pct / 100
        # Round size to 4 decimals to avoid Hyperliquid wire encoding errors
        size = round(size, 4)
        
        # Check minimum position size (Hyperliquid typically requires > 0.001 ETH)
        if size < 0.001:
            print(f"⚠️ Position size {size:.4f} ETH too small (min 0.001), skipping trade")
            return {"status": "error", "error": "Position size below minimum"}
        
        print(f"🚨 LIVE TRADE: {side.upper()} {size:.4f} {symbol} with slippage {slippage*100:.1f}%")
        result = self.exchange.market_open(symbol, is_buy=is_buy, sz=size, px=None, slippage=slippage)
        print(f"📊 Order result: {result}")
        return result

    def close_position(self, symbol: str, size: Optional[float] = None, max_slippage_pct: float = 0.5, price: float = None) -> Dict[str, Any]:
        """Close position (price param for API compatibility, not used)"""
        slippage = max_slippage_pct / 100
        # Round size to 4 decimals if provided
        if size is not None:
            size = round(size, 4)
        print(f"🚨 CLOSING: {symbol} position")
        result = self.exchange.market_close(symbol, sz=size, px=None, slippage=slippage)
        
        # Calculate PnL from result
        if "status" in result and result.get("status") == "ok":
            # Extract PnL if available
            pnl = result.get("response", {}).get("data", {}).get("statuses", [{}])[0].get("filled", 0)
            result["pnl"] = float(pnl) if pnl else 0
        
        print(f"📊 Close result: {result}")
        return result
