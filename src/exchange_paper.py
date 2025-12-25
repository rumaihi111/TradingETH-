from typing import Any, Dict, List


class PaperExchange:
    def __init__(self, starting_equity: float = 10000.0):
        self.equity = starting_equity
        self.position: Dict[str, Any] = {"coin": None, "size": 0.0, "entry": 0.0}
        self.trades: List[Dict[str, Any]] = []

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
        return {"status": "closed", "paper": True, "price": price, "pnl": pnl}
