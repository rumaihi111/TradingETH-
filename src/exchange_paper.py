import json
import os
from typing import Any, Dict, List


class PaperExchange:
    def __init__(self, starting_equity: float = 10000.0, state_file: str = "data/paper_wallet.json"):
        self.state_file = state_file
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
                self.position = state.get("position", {"coin": None, "size": 0.0, "entry": 0.0})
                print(f"Paper wallet loaded: ${self.equity:.2f} equity, position={self.position}")
        else:
            self.equity = starting_equity
            self.position = {"coin": None, "size": 0.0, "entry": 0.0}
            print(f"Paper wallet initialized: ${self.equity:.2f} (file not found: {self.state_file})")
            
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
        signed_size = size if is_buy else -size
        self.position = {"coin": symbol, "size": signed_size, "entry": price}
        self.trades.append({"symbol": symbol, "side": side, "size": size, "price": price, "type": "open"})
        self._save_state()
        return {"status": "filled", "paper": True, "price": price, "size": size, "side": side}

    def close_position(self, symbol: str, size: float = None, max_slippage_pct: float = 0.5, price: float = None) -> Dict[str, Any]:
        if price is None:
            raise RuntimeError("Paper mode requires price input")
        if self.position["size"] == 0:
            return {"status": "noop", "paper": True}
        pos_size = self.position["size"] if size is None else size if self.position["size"] > 0 else -size
        pnl = (price - self.position["entry"]) * pos_size
        self.equity += pnl
        self.trades.append({"symbol": symbol, "side": "close", "size": pos_size, "price": price, "pnl": pnl, "type": "close"})
        self.position = {"coin": None, "size": 0.0, "entry": 0.0}
        self._save_state()
        print(f"Paper wallet updated: ${self.equity:.2f} (PnL: ${pnl:+.2f})")
        return {"status": "closed", "paper": True, "price": price, "pnl": pnl}
