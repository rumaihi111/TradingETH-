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
        account_address: str = "",
    ):
        if private_key_hex.startswith("0x"):
            private_key_hex = private_key_hex
        self.wallet = Account.from_key(private_key_hex)
        self.account_address = account_address or self.wallet.address
        base_url = base_url_override or (constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL)
        self.info = Info(base_url, skip_ws=skip_ws)
        self.exchange = Exchange(self.wallet, base_url, account_address=self.account_address)
        
        # Note: Bot assumes 10x leverage - set this manually in Hyperliquid UI
        print("⚠️ IMPORTANT: Ensure your Hyperliquid account is set to 10x leverage (Cross Margin)")

    def account(self) -> Dict[str, Any]:
        """Get account state with equity"""
        print(f"🔍 Querying account: {self.account_address} (via API wallet: {self.wallet.address})")
        state = self.info.user_state(self.account_address)
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

    def place_trigger_order(self, symbol: str, side: str, size: float, trigger_price: float, is_stop: bool = True, reduce_only: bool = True) -> Dict[str, Any]:
        """Place stop loss or take profit trigger order
        
        Args:
            symbol: Trading pair (e.g., 'ETH')
            side: 'buy' or 'sell' - opposite of position direction
            size: Size in base currency (e.g., ETH amount)
            trigger_price: Price at which order triggers
            is_stop: True for stop loss, False for take profit
            reduce_only: True to only close positions, not open new ones
        """
        is_buy = side.lower() == "buy"
        # Hyperliquid SDK expects strings for numeric values
        sz_str = str(round(float(size), 4))
        px_str = str(round(float(trigger_price), 2))
        
        # Hyperliquid trigger order structure
        order_type = {"trigger": {"triggerPx": px_str, "isMarket": True, "tpsl": "tp" if not is_stop else "sl"}}
        
        print(f"🎯 Placing {'Stop Loss' if is_stop else 'Take Profit'}: {side.upper()} {sz_str} {symbol} @ ${px_str}")
        
        try:
            result = self.exchange.order(
                symbol,
                is_buy=is_buy,
                sz=float(sz_str),  # SDK needs float
                limit_px=float(px_str),  # SDK needs float
                order_type=order_type,
                reduce_only=reduce_only
            )
            print(f"✅ Trigger order placed: {result}")
            return result
        except Exception as e:
            print(f"❌ Failed to place trigger order: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}

    def close_position(self, symbol: str, size: Optional[float] = None, max_slippage_pct: float = 0.5, price: float = None) -> Dict[str, Any]:
        """Close position (price param for API compatibility, not used)"""
        slippage = max_slippage_pct / 100
        # Round size to 4 decimals if provided
        if size is not None:
            size = round(size, 4)
        
        # Get position info before closing for PNL calculation
        positions = self.positions()
        entry_price = 0
        position_size = 0
        if positions:
            entry_price = positions[0].get("entry_price", 0)
            position_size = abs(positions[0].get("size", 0))
        
        print(f"🚨 CLOSING: {symbol} position")
        result = self.exchange.market_close(symbol, sz=size, px=None, slippage=slippage)
        
        # Try to extract PNL from Hyperliquid response
        pnl = 0
        close_price = 0
        
        if isinstance(result, dict) and result.get("status") == "ok":
            response_data = result.get("response", {})
            if isinstance(response_data, dict):
                data = response_data.get("data", {})
                if isinstance(data, dict):
                    statuses = data.get("statuses", [])
                    if statuses and isinstance(statuses[0], dict):
                        filled = statuses[0].get("filled", {})
                        if isinstance(filled, dict):
                            # Try to get closedPnl from Hyperliquid
                            pnl = float(filled.get("closedPnl", 0))
                            # Get close price
                            close_price = float(filled.get("avgPx", 0))
        
        # If Hyperliquid didn't provide PNL, calculate it manually
        if pnl == 0 and entry_price > 0 and close_price > 0 and position_size > 0:
            # Calculate based on entry vs exit
            # For long: (exit - entry) * size
            # For short: (entry - exit) * size
            # Assume long for now (most common)
            pnl = (close_price - entry_price) * position_size
            print(f"📊 Calculated PnL manually: ({close_price:.2f} - {entry_price:.2f}) × {position_size:.4f} = ${pnl:.2f}")
        
        result["pnl"] = pnl
        result["close_price"] = close_price if close_price > 0 else None
        print(f"📊 Close result: Sold {position_size:.4f} {symbol} @ ${close_price:.2f} (PnL: ${pnl:+.2f})")
        return result
