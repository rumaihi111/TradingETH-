import json
import os
from typing import Any, Dict, List, Optional, Tuple


class PaperExchange:
    def __init__(self, starting_equity: float = 10000.0, state_file: str = "data/paper_wallet.json", leverage: float = 10.0):
        self.state_file = state_file
        self.leverage = leverage  # 10x leverage means 10% move = 100% gain/loss
        self.liquidation_threshold = 0.90  # Liquidate if loss reaches 90% of margin
        self.trigger_orders: List[Dict[str, Any]] = []  # Store SL/TP orders
        data_dir = os.path.dirname(self.state_file)
        os.makedirs(data_dir, exist_ok=True)
        
        # Debug: show what's in the data directory
        print(f"📁 Checking volume at: {os.path.abspath(data_dir)}")
        if os.path.exists(data_dir):
            files = os.listdir(data_dir)
            print(f"📁 Files in data/: {files if files else '(empty)'}")
        
        # Load existing state or initialize new
        if os.path.exists(self.state_file):
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                self.equity = state.get("equity", starting_equity)
                self.position = state.get("position", {"coin": None, "size": 0.0, "entry": 0.0, "margin": 0.0})
                self.trigger_orders = state.get("trigger_orders", [])
                print(f"Paper wallet loaded: ${self.equity:.2f} equity, position={self.position}, leverage={self.leverage}x")
        else:
            self.equity = starting_equity
            self.position = {"coin": None, "size": 0.0, "entry": 0.0, "margin": 0.0}
            self.trigger_orders = []
            print(f"Paper wallet initialized: ${self.equity:.2f}, leverage={self.leverage}x (file not found: {self.state_file})")
            
        self.trades: List[Dict[str, Any]] = []
        self._save_state()
    
    def _save_state(self):
        """Persist wallet state to disk"""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump({
                "equity": self.equity, 
                "position": self.position,
                "trigger_orders": self.trigger_orders
            }, f, indent=2)

    def account(self) -> Dict[str, Any]:
        return {"equity": self.equity}

    def positions(self) -> List[Dict[str, Any]]:
        if self.position["size"] == 0:
            return []
        return [self.position]

    def place_market(self, symbol: str, side: str, size: float, max_slippage_pct: float, price: float = None) -> Dict[str, Any]:
        # price is required for simulation
        if price is None:
            raise RuntimeError("Paper mode requires price input")
        is_buy = side.lower() == "long"
        
        # With leverage: size is multiplied, but margin (actual capital locked) is size * price / leverage
        leveraged_size = size * self.leverage
        signed_size = leveraged_size if is_buy else -leveraged_size
        margin_required = abs(size) * price  # Capital locked for this position
        
        self.position = {"coin": symbol, "size": signed_size, "entry": price, "margin": margin_required}
        self.trades.append({"symbol": symbol, "side": side, "size": leveraged_size, "price": price, "type": "open", "margin": margin_required})
        self._save_state()
        print(f"📈 Leveraged {self.leverage}x: Position size={leveraged_size:.4f} ETH, Margin=${margin_required:.2f}")
        return {"status": "filled", "paper": True, "price": price, "size": leveraged_size, "side": side}

    def close_position(self, symbol: str, size: float = None, max_slippage_pct: float = 0.5, price: float = None) -> Dict[str, Any]:
        if price is None:
            raise RuntimeError("Paper mode requires price input")
        if self.position["size"] == 0:
            return {"status": "noop", "paper": True}
        pos_size = self.position["size"] if size is None else size if self.position["size"] > 0 else -size
        
        # P&L is already leveraged (size includes leverage multiplier)
        pnl = (price - self.position["entry"]) * pos_size
        self.equity += pnl
        
        # Clear trigger orders when position closes
        self.trigger_orders = []
        
        self.trades.append({"symbol": symbol, "side": "close", "size": pos_size, "price": price, "pnl": pnl, "type": "close"})
        self.position = {"coin": None, "size": 0.0, "entry": 0.0, "margin": 0.0}
        self._save_state()
        print(f"Paper wallet updated: ${self.equity:.2f} (Leveraged P&L: ${pnl:+.2f})")
        return {"status": "closed", "paper": True, "price": price, "pnl": pnl, "close_price": price}
    
    def place_trigger_order(self, symbol: str, side: str, size: float, trigger_price: float, is_stop: bool = True, reduce_only: bool = True) -> Dict[str, Any]:
        """Place a simulated stop loss or take profit order"""
        order = {
            "symbol": symbol,
            "side": side,
            "size": size,
            "trigger_price": trigger_price,
            "is_stop": is_stop,
            "reduce_only": reduce_only,
            "type": "sl" if is_stop else "tp"
        }
        self.trigger_orders.append(order)
        self._save_state()
        order_type = "Stop Loss" if is_stop else "Take Profit"
        print(f"📝 Paper {order_type}: {side.upper()} {size:.4f} {symbol} @ ${trigger_price:.2f}")
        return {"status": "ok", "paper": True, "order": order}
    
    def cancel_all_orders(self, symbol: str) -> Dict[str, Any]:
        """Cancel all trigger orders for a symbol"""
        before = len(self.trigger_orders)
        self.trigger_orders = [o for o in self.trigger_orders if o.get("symbol") != symbol]
        after = len(self.trigger_orders)
        self._save_state()
        print(f"🧹 Paper: Cancelled {before - after} orders for {symbol}")
        return {"status": "ok", "cancelled": before - after}
    
    def check_trigger_orders(self, current_price: float) -> Optional[Dict[str, Any]]:
        """Check if any trigger orders should execute. Returns triggered order info or None."""
        if self.position["size"] == 0 or not self.trigger_orders:
            return None
        
        is_long = self.position["size"] > 0
        
        for order in self.trigger_orders:
            trigger_price = order["trigger_price"]
            is_stop = order["is_stop"]
            
            triggered = False
            
            if is_long:
                # Long position: SL triggers when price drops below, TP triggers when price rises above
                if is_stop and current_price <= trigger_price:
                    triggered = True
                    print(f"🛑 STOP LOSS TRIGGERED @ ${current_price:.2f} (trigger: ${trigger_price:.2f})")
                elif not is_stop and current_price >= trigger_price:
                    triggered = True
                    print(f"🎯 TAKE PROFIT TRIGGERED @ ${current_price:.2f} (trigger: ${trigger_price:.2f})")
            else:
                # Short position: SL triggers when price rises above, TP triggers when price drops below
                if is_stop and current_price >= trigger_price:
                    triggered = True
                    print(f"🛑 STOP LOSS TRIGGERED @ ${current_price:.2f} (trigger: ${trigger_price:.2f})")
                elif not is_stop and current_price <= trigger_price:
                    triggered = True
                    print(f"🎯 TAKE PROFIT TRIGGERED @ ${current_price:.2f} (trigger: ${trigger_price:.2f})")
            
            if triggered:
                # Execute the close at trigger price
                result = self.close_position(order["symbol"], price=trigger_price)
                result["trigger_type"] = "sl" if is_stop else "tp"
                return result
        
        return None
    
    def check_liquidation(self, current_price: float) -> bool:
        """Check if position should be liquidated"""
        if self.position["size"] == 0:
            return False
        
        pos_size = self.position["size"]
        entry = self.position["entry"]
        margin = self.position.get("margin", 0)
        
        if margin == 0:
            return False
        
        # Calculate unrealized P&L
        unrealized_pnl = (current_price - entry) * pos_size
        
        # Check if loss exceeds liquidation threshold
        loss_pct = abs(unrealized_pnl / margin) if margin > 0 else 0
        
        if unrealized_pnl < 0 and loss_pct >= self.liquidation_threshold:
            # Liquidate position
            print(f"⚠️ LIQUIDATION: Loss {loss_pct*100:.1f}% exceeds threshold {self.liquidation_threshold*100:.1f}%")
            self.equity += unrealized_pnl  # Apply the loss
            self.position = {"coin": None, "size": 0.0, "entry": 0.0, "margin": 0.0}
            self._save_state()
            return True
        
        return False
