import json
import os
import time
from typing import Dict, List
from datetime import datetime, timezone


class PnLTracker:
    """Track performance metrics and P&L over time"""
    
    def __init__(self, path: str = "data/pnl_tracker.json", current_equity: float = None):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.data = self._load(current_equity)
    
    def _load(self, current_equity: float = None) -> Dict:
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"📊 P&L Tracker loaded: tracking since ${data.get('start_equity', 10000):.2f}")
                return data
        # New tracker - use current equity as baseline
        start_eq = current_equity if current_equity is not None else 10000.0
        print(f"📊 P&L Tracker initialized: baseline ${start_eq:.2f}")
        return {
            "start_time": time.time(),
            "start_equity": start_eq,
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
    
    def get_stats(self, current_equity: float = None) -> Dict:
        """Calculate performance statistics"""
        closed_trades = [t for t in self.data["trades"] if t.get("pnl") is not None]
        winning = [t for t in closed_trades if t["pnl"] > 0]
        losing = [t for t in closed_trades if t["pnl"] < 0]
        
        total_pnl = sum(t["pnl"] for t in closed_trades)
        start_eq = self.data.get("start_equity", 10000)
        curr_eq = current_equity if current_equity is not None else start_eq + total_pnl
        
        return {
            "starting_equity": start_eq,
            "start_equity": start_eq,  # Keeping both for backwards compatibility
            "current_equity": curr_eq,
            "total_pnl": total_pnl,
            "total_pnl_pct": (total_pnl / start_eq) * 100 if start_eq else 0,
            "pnl_pct": (total_pnl / start_eq) * 100 if start_eq else 0,  # Alias
            "total_closed_trades": len(closed_trades),
            "total_trades": len(closed_trades),  # Alias
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": (len(winning) / len(closed_trades) * 100) if closed_trades else 0,
            "avg_win": (sum(t["pnl"] for t in winning) / len(winning)) if winning else 0,
            "avg_loss": (sum(t["pnl"] for t in losing) / len(losing)) if losing else 0,
            "largest_win": max((t["pnl"] for t in winning), default=0),
            "largest_loss": min((t["pnl"] for t in losing), default=0),
        }

    def _filter_period(self, period: str) -> List[Dict]:
        """Return trades closed in the given period (UTC boundaries)."""
        now = datetime.now(timezone.utc)
        trades = [t for t in self.data.get("trades", []) if t.get("pnl") is not None]
        result = []
        for t in trades:
            dt = datetime.fromtimestamp(t["ts"], tz=timezone.utc)
            include = False
            if period == "daily":
                include = (dt.date() == now.date())
            elif period == "weekly":
                # ISO week number
                include = (dt.isocalendar()[:2] == now.isocalendar()[:2])
            elif period == "monthly":
                include = (dt.year == now.year and dt.month == now.month)
            if include:
                result.append(t)
        return result

    def get_period_stats(self, period: str) -> Dict:
        """Daily/weekly/monthly stats using net PnL after fees if available."""
        trades = self._filter_period(period)
        total_pnl = sum(t["pnl"] for t in trades)
        winners = [t for t in trades if t["pnl"] > 0]
        losers = [t for t in trades if t["pnl"] < 0]
        total = len(trades)
        return {
            "period": period,
            "total_closed_trades": total,
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate": (len(winners) / total * 100) if total else 0,
            "total_pnl": total_pnl,
            "avg_win": (sum(t["pnl"] for t in winners) / len(winners)) if winners else 0,
            "avg_loss": (sum(t["pnl"] for t in losers) / len(losers)) if losers else 0,
        }
    
    def print_balance_sheet(self, current_equity: float, unrealized_pnl: float = 0, position: Dict = None):
        """Print formatted balance sheet with unrealized P&L and position details"""
        stats = self.get_stats(current_equity)
        # Total account value includes unrealized P&L from open positions
        total_equity = current_equity + unrealized_pnl
        total_pnl = stats['total_pnl'] + unrealized_pnl
        total_pnl_pct = (total_pnl / stats['start_equity']) * 100 if stats['start_equity'] else 0
        
        print("\n" + "="*60)
        print("📊 BALANCE SHEET & P&L REPORT")
        print("="*60)
        print(f"Starting Equity:    ${stats['start_equity']:,.2f}")
        print(f"Current Equity:     ${current_equity:,.2f}")
        
        # Show open position details if any
        if position and abs(position.get('size', 0)) > 0.0001:
            side = "LONG" if position['size'] > 0 else "SHORT"
            size = abs(position['size'])
            entry = position.get('entry_price', position.get('entry', 0))
            print(f"Open Position:      {side} {size:.4f} ETH @ ${entry:.2f}")
            print(f"Unrealized P&L:     ${unrealized_pnl:+,.2f}")
        print(f"Total Account Value: ${total_equity:,.2f}")
        print(f"Total P&L:          ${total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)")
        print("-"*60)
        print(f"Closed Trades:      {stats['total_trades']}")
        print(f"Winning Trades:     {stats['winning_trades']} ({stats['win_rate']:.1f}%)")
        print(f"Losing Trades:      {stats['losing_trades']}")
        print("-"*60)
        print(f"Average Win:        ${stats['avg_win']:+,.2f}")
        print(f"Average Loss:       ${stats['avg_loss']:+,.2f}")
        print(f"Largest Win:        ${stats['largest_win']:+,.2f}")
        print(f"Largest Loss:       ${stats['largest_loss']:+,.2f}")
        print("="*60 + "\n")
