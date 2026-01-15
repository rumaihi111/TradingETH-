"""
Position Tracker - Monitors position age and time-based stops

Implements:
- Time-based exit: Close position if no movement within N candles
- Position entry tracking
- Candle counting since entry
"""

from typing import Dict, Optional, Any
from datetime import datetime


class PositionTracker:
    """Tracks position entry time and candle count for time-based stops"""
    
    def __init__(self, max_candles_5m: int = 10):
        """
        Args:
            max_candles_5m: Maximum candles to wait on 5m chart before exiting
        """
        self.max_candles_5m = max_candles_5m
        self.position_entry_time: Optional[float] = None
        self.position_entry_candle_count: int = 0
        self.position_side: Optional[str] = None
        self.position_entry_price: Optional[float] = None
    
    def on_position_opened(self, side: str, entry_price: float, timestamp: float):
        """
        Record when a position is opened
        
        Args:
            side: "long" or "short"
            entry_price: Entry price
            timestamp: Timestamp in milliseconds
        """
        self.position_entry_time = timestamp
        self.position_entry_candle_count = 0
        self.position_side = side
        self.position_entry_price = entry_price
        print(f"📍 Position tracker: {side.upper()} position opened @ ${entry_price:.2f}")
    
    def on_position_closed(self):
        """Record when position is closed"""
        self.position_entry_time = None
        self.position_entry_candle_count = 0
        self.position_side = None
        self.position_entry_price = None
        print(f"📍 Position tracker: Position closed")
    
    def on_new_candle(self, candle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process new candle and check for time-based exit
        
        Args:
            candle: Latest candle data
        
        Returns:
            Dict with exit recommendation if time stop triggered, else None
        """
        if not self.position_entry_time:
            return None  # No position open
        
        # Increment candle count
        self.position_entry_candle_count += 1
        
        current_price = float(candle['close'])
        
        # Check if time stop triggered
        if self.position_entry_candle_count >= self.max_candles_5m:
            # Calculate price movement since entry
            if self.position_entry_price:
                price_change_pct = abs(current_price - self.position_entry_price) / self.position_entry_price
            else:
                price_change_pct = 0
            
            return {
                "should_exit": True,
                "reason": f"Time stop: {self.position_entry_candle_count} candles with no significant movement",
                "candles_held": self.position_entry_candle_count,
                "price_change_pct": float(price_change_pct),
            }
        
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current position tracking status"""
        if not self.position_entry_time:
            return {
                "has_position": False,
            }
        
        return {
            "has_position": True,
            "side": self.position_side,
            "entry_price": self.position_entry_price,
            "candles_held": self.position_entry_candle_count,
            "candles_remaining": max(0, self.max_candles_5m - self.position_entry_candle_count),
        }
