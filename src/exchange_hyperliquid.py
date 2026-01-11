import time
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
        
        # Note: Bot assumes 15x leverage - set this manually in Hyperliquid UI
        print("⚠️ IMPORTANT: Ensure your Hyperliquid account is set to 15x leverage (Cross Margin)")

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

    def place_limit_order(self, symbol: str, is_buy: bool, size: float, limit_price: float) -> Dict[str, Any]:
        """Place a limit order (maker fee ~0.01% vs 0.035% taker)"""
        size = round(size, 4)
        limit_price = round(limit_price, 2)
        
        print(f"📝 Placing LIMIT {'BUY' if is_buy else 'SELL'}: {size:.4f} {symbol} @ ${limit_price:.2f}")
        
        try:
            result = self.exchange.order(
                symbol,
                is_buy=is_buy,
                sz=size,
                limit_px=limit_price,
                order_type={"limit": {"tif": "Gtc"}},  # Good-til-cancelled
                reduce_only=False
            )
            print(f"📊 Limit order result: {result}")
            return result
        except Exception as e:
            print(f"❌ Limit order failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get all open orders, optionally filtered by symbol"""
        try:
            orders = self.info.open_orders(self.account_address)
            if symbol:
                orders = [o for o in orders if o.get("coin") == symbol]
            return orders
        except Exception as e:
            print(f"❌ Failed to get open orders: {e}")
            return []
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order"""
        try:
            result = self.exchange.cancel(symbol, order_id)
            print(f"🚫 Cancelled order {order_id}: {result}")
            return result
        except Exception as e:
            print(f"❌ Failed to cancel order: {e}")
            return {"status": "error", "error": str(e)}
    
    def place_market(self, symbol: str, side: str, size: float, max_slippage_pct: float, price: float = None, max_retries: int = 10, retry_delay: float = 2.0, use_limit: bool = True, limit_timeout: int = 30) -> Dict[str, Any]:
        """
        Place order with limit-first strategy to save fees.
        
        Strategy:
        1. Place limit order at 0.03% better price (saves ~70% on fees)
        2. Wait up to limit_timeout seconds for fill
        3. If not filled, cancel and use market order (safety net)
        
        Args:
            use_limit: If True, try limit order first (default). Set False to force market.
            limit_timeout: Seconds to wait for limit fill before falling back to market.
        """
        is_buy = side.lower() == "long"
        size = round(size, 4)
        
        # Check minimum position size
        if size < 0.001:
            print(f"⚠️ Position size {size:.4f} ETH too small (min 0.001), skipping trade")
            return {"status": "error", "error": "Position size below minimum"}
        
        # === LIMIT ORDER STRATEGY ===
        if use_limit and price and price > 0:
            # Calculate limit price: 0.03% better than current
            # For BUY: slightly below current (we want to buy cheaper)
            # For SELL: slightly above current (we want to sell higher)
            offset_pct = 0.0003  # 0.03%
            if is_buy:
                limit_price = price * (1 - offset_pct)
            else:
                limit_price = price * (1 + offset_pct)
            
            print(f"💰 FEE SAVER: Trying limit order first (0.01% fee vs 0.035% market)")
            print(f"   Current price: ${price:.2f} → Limit: ${limit_price:.2f}")
            
            limit_result = self.place_limit_order(symbol, is_buy, size, limit_price)
            
            if limit_result.get("status") == "ok":
                # Extract order ID from response
                order_id = None
                try:
                    statuses = limit_result.get("response", {}).get("data", {}).get("statuses", [])
                    if statuses and "resting" in statuses[0]:
                        order_id = statuses[0]["resting"]["oid"]
                except:
                    pass
                
                if order_id:
                    print(f"⏳ Limit order placed (ID: {order_id}). Waiting up to {limit_timeout}s for fill...")
                    
                    # Poll for fill
                    for i in range(limit_timeout):
                        time.sleep(1)
                        
                        # Check if position exists (order filled)
                        positions = self.positions()
                        if positions and abs(positions[0].get("size", 0)) >= size * 0.9:
                            print(f"✅ LIMIT ORDER FILLED! Saved ~70% on fees!")
                            return {"status": "ok", "type": "limit", "price": limit_price}
                        
                        # Check if order still open
                        open_orders = self.get_open_orders(symbol)
                        order_still_open = any(o.get("oid") == order_id for o in open_orders)
                        
                        if not order_still_open:
                            # Order gone but no position - might have been filled
                            positions = self.positions()
                            if positions and abs(positions[0].get("size", 0)) >= size * 0.9:
                                print(f"✅ LIMIT ORDER FILLED! Saved ~70% on fees!")
                                return {"status": "ok", "type": "limit", "price": limit_price}
                            break
                        
                        if i % 10 == 9:
                            print(f"   Still waiting... {limit_timeout - i - 1}s remaining")
                    
                    # Timeout - cancel limit order
                    print(f"⏰ Limit order timeout. Cancelling and using market order...")
                    self.cancel_order(symbol, order_id)
                    time.sleep(0.5)  # Brief pause after cancel
        
        # === MARKET ORDER FALLBACK ===
        slippage = max_slippage_pct / 100
        
        for attempt in range(1, max_retries + 1):
            current_slippage = slippage + (0.001 * (attempt - 1))
            print(f"🚨 MARKET ORDER (attempt {attempt}/{max_retries}): {side.upper()} {size:.4f} {symbol} with slippage {current_slippage*100:.2f}%")
            
            try:
                result = self.exchange.market_open(symbol, is_buy=is_buy, sz=size, px=None, slippage=current_slippage)
                print(f"📊 Order result: {result}")
                
                if isinstance(result, dict):
                    if result.get("status") == "ok":
                        result["type"] = "market"
                        return result
                    error = result.get("response", {}).get("error") or result.get("error", "")
                    if error and attempt < max_retries:
                        print(f"⚠️ Order failed: {error}. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                return result
                
            except Exception as e:
                print(f"❌ Order attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    print(f"🔄 Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    return {"status": "error", "error": str(e)}
        
        return {"status": "error", "error": "Max retries exceeded"}

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
        # Convert to proper types
        size_float = round(float(size), 4)
        price_float = round(float(trigger_price), 2)
        
        # Hyperliquid trigger order structure - triggerPx must be string
        order_type = {"trigger": {"triggerPx": f"{price_float:.2f}", "isMarket": True, "tpsl": "tp" if not is_stop else "sl"}}
        
        print(f"🎯 Placing {'Stop Loss' if is_stop else 'Take Profit'}: {side.upper()} {size_float} {symbol} @ ${price_float}")
        
        try:
            result = self.exchange.order(
                symbol,
                is_buy=is_buy,
                sz=size_float,
                limit_px=price_float,
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

    def close_position(self, symbol: str, size: Optional[float] = None, max_slippage_pct: float = 0.5, price: float = None, max_retries: int = 10, retry_delay: float = 2.0, use_limit: bool = True, limit_timeout: int = 15) -> Dict[str, Any]:
        """
        Close position with limit-first strategy to save fees.
        
        Strategy:
        1. Place limit order at 0.03% better price (saves ~70% on fees)
        2. Wait up to limit_timeout seconds for fill (shorter than open - exits are urgent!)
        3. If not filled, cancel and use market order (safety net)
        
        Args:
            use_limit: If True, try limit order first. Set False to force market.
            limit_timeout: Seconds to wait for limit fill (default 15s - shorter for closes)
        """
        # Get position info before closing for PNL calculation
        positions = self.positions()
        entry_price = 0
        position_size = 0
        position_side = None
        if positions:
            entry_price = positions[0].get("entry_price", 0)
            position_size = abs(positions[0].get("size", 0))
            position_side = "long" if positions[0].get("size", 0) > 0 else "short"
        
        if size is not None:
            size = round(size, 4)
        else:
            size = position_size
        
        # === LIMIT ORDER STRATEGY FOR CLOSE ===
        if use_limit and price and price > 0 and position_size > 0:
            # To close: sell if long, buy if short
            is_buy = position_side == "short"
            
            # Calculate limit price: 0.03% better than current
            # Closing LONG (selling): slightly above current price
            # Closing SHORT (buying): slightly below current price
            offset_pct = 0.0003  # 0.03%
            if is_buy:  # Closing short = buying
                limit_price = price * (1 - offset_pct)
            else:  # Closing long = selling
                limit_price = price * (1 + offset_pct)
            
            print(f"💰 FEE SAVER: Trying limit close first (0.01% fee vs 0.035% market)")
            print(f"   Current price: ${price:.2f} → Limit: ${limit_price:.2f}")
            
            # Place limit order with reduce_only
            limit_price = round(limit_price, 2)
            try:
                result = self.exchange.order(
                    symbol,
                    is_buy=is_buy,
                    sz=size,
                    limit_px=limit_price,
                    order_type={"limit": {"tif": "Gtc"}},
                    reduce_only=True  # Important: only close, don't open new position
                )
                
                if result.get("status") == "ok":
                    order_id = None
                    try:
                        statuses = result.get("response", {}).get("data", {}).get("statuses", [])
                        if statuses and "resting" in statuses[0]:
                            order_id = statuses[0]["resting"]["oid"]
                    except:
                        pass
                    
                    if order_id:
                        print(f"⏳ Limit close placed (ID: {order_id}). Waiting up to {limit_timeout}s for fill...")
                        
                        for i in range(limit_timeout):
                            time.sleep(1)
                            
                            # Check if position is closed
                            current_positions = self.positions()
                            if not current_positions or abs(current_positions[0].get("size", 0)) < 0.0001:
                                # Position closed!
                                pnl = (price - entry_price) * position_size if position_side == "long" else (entry_price - price) * position_size
                                print(f"✅ LIMIT CLOSE FILLED! Saved ~70% on fees!")
                                return {"status": "ok", "type": "limit", "pnl": pnl, "close_price": limit_price}
                            
                            # Check if order still open
                            open_orders = self.get_open_orders(symbol)
                            order_still_open = any(o.get("oid") == order_id for o in open_orders)
                            
                            if not order_still_open:
                                current_positions = self.positions()
                                if not current_positions or abs(current_positions[0].get("size", 0)) < 0.0001:
                                    pnl = (price - entry_price) * position_size if position_side == "long" else (entry_price - price) * position_size
                                    print(f"✅ LIMIT CLOSE FILLED! Saved ~70% on fees!")
                                    return {"status": "ok", "type": "limit", "pnl": pnl, "close_price": limit_price}
                                break
                            
                            if i % 5 == 4:
                                print(f"   Still waiting... {limit_timeout - i - 1}s remaining")
                        
                        # Timeout - cancel limit order
                        print(f"⏰ Limit close timeout. Cancelling and using market order...")
                        self.cancel_order(symbol, order_id)
                        time.sleep(0.5)
            except Exception as e:
                print(f"⚠️ Limit close failed: {e}, falling back to market")
        
        # === MARKET ORDER FALLBACK ===
        slippage = max_slippage_pct / 100
        
        result = None
        for attempt in range(1, max_retries + 1):
            current_slippage = slippage + (0.001 * (attempt - 1))
            print(f"🚨 MARKET CLOSE (attempt {attempt}/{max_retries}): {symbol} with slippage {current_slippage*100:.2f}%")
            
            try:
                result = self.exchange.market_close(symbol, sz=size, px=None, slippage=current_slippage)
                
                if isinstance(result, dict):
                    if result.get("status") == "ok":
                        break
                    error = result.get("response", {}).get("error") or result.get("error", "")
                    if error and attempt < max_retries:
                        print(f"⚠️ Close failed: {error}. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                break
                
            except Exception as e:
                print(f"❌ Close attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    print(f"🔄 Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    return {"status": "error", "error": str(e), "pnl": 0}
        
        if result is None:
            return {"status": "error", "error": "Max retries exceeded", "pnl": 0}
        
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
                            pnl = float(filled.get("closedPnl", 0))
                            close_price = float(filled.get("avgPx", 0))
        
        # If Hyperliquid didn't provide PNL, calculate it manually
        if pnl == 0 and entry_price > 0 and close_price > 0 and position_size > 0:
            if position_side == "long":
                pnl = (close_price - entry_price) * position_size
            else:
                pnl = (entry_price - close_price) * position_size
            print(f"📊 Calculated PnL manually: ${pnl:.2f}")
        
        result["pnl"] = pnl
        result["close_price"] = close_price if close_price > 0 else None
        result["type"] = "market"
        print(f"📊 Close result: {position_side.upper() if position_side else 'Position'} closed @ ${close_price:.2f} (PnL: ${pnl:+.2f})")
        return result
