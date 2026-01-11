import json
import os
from typing import Any, Dict, List


class PaperExchange:
    def __init__(self, starting_equity: float = 10000.0, state_file: str = "data/paper_wallet.json", leverage: float = 15.0):
        self.state_file = state_file
        self.leverage = leverage  # 15x leverage means 6.67% move = 100% gain/loss
        self.liquidation_threshold = 0.90  # Liquidate if loss reaches 90% of margin
        
        # Transaction fees (Hyperliquid fee structure)
        # Limit (maker): 0.01-0.02%  |  Market (taker): 0.04-0.06%
        # ~0.035% taker fee + ~0-0.02% real slippage on liquid books
        # Mid-cap/volatile perps: 0.08-0.15% total slippage
        self.maker_fee_pct = 0.015 / 100   # 0.015% maker fee
        self.taker_fee_pct = 0.05 / 100    # 0.05% taker fee
        self.market_slippage_pct = 0.10 / 100  # 0.10% slippage on market orders
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
                print(f"Paper wallet loaded: ${self.equity:.2f} equity, position={self.position}, leverage={self.leverage}x")
        else:
            self.equity = starting_equity
            self.position = {"coin": None, "size": 0.0, "entry": 0.0, "margin": 0.0}
            print(f"Paper wallet initialized: ${self.equity:.2f}, leverage={self.leverage}x (file not found: {self.state_file})")
            
        self.trades: List[Dict[str, Any]] = []
        self._save_state()
    
    def _save_state(self):
        """Persist wallet state to disk"""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump({"equity": self.equity, "position": self.position}, f, indent=2)

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
        
        # Apply slippage + taker fee to entry price (realistic simulation)
        # Slippage: worse price on entry (buy higher, sell lower)
        total_cost_pct = self.taker_fee_pct + self.market_slippage_pct
        if is_buy:
            effective_price = price * (1 + total_cost_pct)  # Pay more when buying
        else:
            effective_price = price * (1 - total_cost_pct)  # Get less when selling
        
        # With leverage: size is multiplied, but margin (actual capital locked) is size * price / leverage
        leveraged_size = size * self.leverage
        signed_size = leveraged_size if is_buy else -leveraged_size
        margin_required = abs(size) * price  # Capital locked for this position
        
        # Calculate fee cost for logging
        fee_cost = abs(leveraged_size) * price * total_cost_pct
        
        self.position = {"coin": symbol, "size": signed_size, "entry": effective_price, "margin": margin_required}
        self.trades.append({"symbol": symbol, "side": side, "size": leveraged_size, "price": effective_price, "type": "open", "margin": margin_required, "fee": fee_cost})
        self._save_state()
        print(f"📈 Leveraged {self.leverage}x: Position size={leveraged_size:.4f} ETH, Margin=${margin_required:.2f}")
        print(f"💸 Entry fee+slippage: ${fee_cost:.2f} ({total_cost_pct*100:.3f}%)")
        return {"status": "filled", "paper": True, "price": effective_price, "size": leveraged_size, "side": side, "fee": fee_cost}

    def close_position(self, symbol: str, size: float = None, max_slippage_pct: float = 0.5, price: float = None) -> Dict[str, Any]:
        if price is None:
            raise RuntimeError("Paper mode requires price input")
        if self.position["size"] == 0:
            return {"status": "noop", "paper": True}
        pos_size = self.position["size"] if size is None else size if self.position["size"] > 0 else -size
        
        # P&L is already leveraged (size includes leverage multiplier)
        pnl = (price - self.position["entry"]) * pos_size
        self.equity += pnl
        
        self.trades.append({"symbol": symbol, "side": "close", "size": pos_size, "price": price, "pnl": pnl, "type": "close"})
        self.position = {"coin": None, "size": 0.0, "entry": 0.0, "margin": 0.0}
        self._save_state()
        print(f"Paper wallet updated: ${self.equity:.2f} (Leveraged P&L: ${pnl:+.2f})")
        return {"status": "closed", "paper": True, "price": price, "pnl": pnl}
    
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
