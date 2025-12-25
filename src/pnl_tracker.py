import json
import os
import time
from typing import Dict, List


class PnLTracker:
    """Track performance metrics and P&L over time"""
    
    def __init__(self, path: str = "data/pnl_tracker.json"):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.data = self._load()
    
    def _load(self) -> Dict:
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "start_time": time.time(),
            "start_equity": 10000.0,
            "trades": [],
            "snapshots": []
        }
    
    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
    
    def record_trade(self, trade_type: str, size: float, entry_price: float, exit_price: float = None, pnl: float = None):
        """Record a trade (open or close)"""
        trade = {
            "ts": time.time(),
            "type": trade_type,  # "open" or "close"
            "size": size,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": pnl
        }
        self.data["trades"].append(trade)
        self._save()
    
    def snapshot(self, equity: float, open_position: Dict = None):
        """Take equity snapshot"""
        snap = {
            "ts": time.time(),
            "equity": equity,
            "open_position": open_position
        }
        self.data["snapshots"].append(snap)
        self._save()
    
    def get_stats(self, current_equity: float) -> Dict:
        """Calculate performance statistics"""
        closed_trades = [t for t in self.data["trades"] if t.get("pnl") is not None]
        winning = [t for t in closed_trades if t["pnl"] > 0]
        losing = [t for t in closed_trades if t["pnl"] < 0]
        
        total_pnl = sum(t["pnl"] for t in closed_trades)
        start_eq = self.data.get("start_equity", 10000)
        
        return {
            "start_equity": start_eq,
            "current_equity": current_equity,
            "total_pnl": total_pnl,
            "pnl_pct": (total_pnl / start_eq) * 100 if start_eq else 0,
            "total_trades": len(closed_trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": (len(winning) / len(closed_trades) * 100) if closed_trades else 0,
            "avg_win": (sum(t["pnl"] for t in winning) / len(winning)) if winning else 0,
            "avg_loss": (sum(t["pnl"] for t in losing) / len(losing)) if losing else 0,
            "largest_win": max((t["pnl"] for t in winning), default=0),
            "largest_loss": min((t["pnl"] for t in losing), default=0),
        }
    
    def print_balance_sheet(self, current_equity: float):
        """Print formatted balance sheet"""
        stats = self.get_stats(current_equity)
        
        print("\n" + "="*60)
        print("📊 BALANCE SHEET & P&L REPORT")
        print("="*60)
        print(f"Starting Equity:    ${stats['start_equity']:,.2f}")
        print(f"Current Equity:     ${stats['current_equity']:,.2f}")
        print(f"Total P&L:          ${stats['total_pnl']:+,.2f} ({stats['pnl_pct']:+.2f}%)")
        print("-"*60)
        print(f"Total Trades:       {stats['total_trades']}")
        print(f"Winning Trades:     {stats['winning_trades']} ({stats['win_rate']:.1f}%)")
        print(f"Losing Trades:      {stats['losing_trades']}")
        print("-"*60)
        print(f"Average Win:        ${stats['avg_win']:+,.2f}")
        print(f"Average Loss:       ${stats['avg_loss']:+,.2f}")
        print(f"Largest Win:        ${stats['largest_win']:+,.2f}")
        print(f"Largest Loss:       ${stats['largest_loss']:+,.2f}")
        print("="*60 + "\n")
