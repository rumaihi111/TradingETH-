"""
Time-of-Day Filter - Prevents trading during low-liquidity periods

Lunch hours, end-of-session drift, and other periods where:
- Liquidity collapses
- Algorithms dominate
- Patterns fail structurally
"""

from typing import List, Tuple
from datetime import datetime, time
import pytz


class TimeFilter:
    """
    Filters out no-trade windows based on time of day.
    Focuses on US market hours and known low-liquidity periods.
    """
    
    def __init__(
        self,
        timezone: str = "America/New_York",
        no_trade_windows: List[Tuple[time, time]] = None
    ):
        """
        Args:
            timezone: Timezone for time checks (default: ET for US markets)
            no_trade_windows: List of (start_time, end_time) tuples for no-trade periods
        """
        self.timezone = pytz.timezone(timezone)
        
        # Default no-trade windows (all times in specified timezone)
        if no_trade_windows is None:
            self.no_trade_windows = [
                # Lunch period (low liquidity, choppy)
                (time(11, 30), time(13, 0)),
                
                # Pre-market close drift (last 30 min - algos dominate)
                (time(15, 30), time(16, 0)),
                
                # After hours / overnight (crypto trades 24/7 but thin liquidity)
                (time(18, 0), time(23, 59)),
                (time(0, 0), time(8, 30)),
            ]
        else:
            self.no_trade_windows = no_trade_windows
    
    def can_trade(self, timestamp: int = None) -> dict:
        """
        Check if current time allows trading.
        
        Args:
            timestamp: Unix timestamp in milliseconds (default: now)
            
        Returns:
            Dict with:
                - can_trade: bool
                - reason: str
                - current_time: str
                - window: str (if in no-trade window)
        """
        if timestamp is None:
            dt = datetime.now(self.timezone)
        else:
            # Convert milliseconds to seconds
            dt = datetime.fromtimestamp(timestamp / 1000, tz=pytz.UTC)
            dt = dt.astimezone(self.timezone)
        
        current_time = dt.time()
        current_time_str = dt.strftime("%H:%M:%S %Z")
        
        # Check if current time falls in any no-trade window
        for start, end in self.no_trade_windows:
            # Handle windows that cross midnight
            if start > end:
                # Window crosses midnight (e.g., 18:00 to 08:30)
                if current_time >= start or current_time <= end:
                    return {
                        "can_trade": False,
                        "reason": f"No-trade window: {start.strftime('%H:%M')} - {end.strftime('%H:%M')}",
                        "current_time": current_time_str,
                        "window": f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"
                    }
            else:
                # Normal window
                if start <= current_time <= end:
                    return {
                        "can_trade": False,
                        "reason": f"No-trade window: {start.strftime('%H:%M')} - {end.strftime('%H:%M')}",
                        "current_time": current_time_str,
                        "window": f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"
                    }
        
        # Not in any no-trade window
        return {
            "can_trade": True,
            "reason": "Time-of-day check passed",
            "current_time": current_time_str,
            "window": None
        }
    
    def get_next_trade_window(self, timestamp: int = None) -> dict:
        """
        Get information about the next available trade window.
        
        Returns:
            Dict with:
                - next_trade_time: datetime
                - minutes_until: int
        """
        if timestamp is None:
            dt = datetime.now(self.timezone)
        else:
            dt = datetime.fromtimestamp(timestamp / 1000, tz=pytz.UTC)
            dt = dt.astimezone(self.timezone)
        
        current_time = dt.time()
        
        # Find the next window end time
        for start, end in sorted(self.no_trade_windows):
            if start > end:  # Crosses midnight
                if current_time >= start or current_time <= end:
                    # We're in this window, next trade time is 'end'
                    next_trade = dt.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
                    if current_time > end:
                        # Already past end, must be before start, so tomorrow
                        next_trade = next_trade.replace(day=dt.day + 1)
                    break
            else:
                if start <= current_time <= end:
                    # We're in this window
                    next_trade = dt.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
                    break
        else:
            # Not in any window, already can trade
            return {
                "next_trade_time": dt,
                "minutes_until": 0
            }
        
        minutes_until = int((next_trade - dt).total_seconds() / 60)
        
        return {
            "next_trade_time": next_trade,
            "minutes_until": minutes_until
        }
    
    @staticmethod
    def create_crypto_optimized() -> "TimeFilter":
        """
        Factory method for crypto-optimized time filter.
        Focuses on peak liquidity hours for crypto markets.
        """
        # Crypto has different optimal hours - peak liquidity during:
        # - US trading hours (9:30 AM - 4:00 PM ET)
        # - Avoid overnight low-liquidity periods
        
        no_trade_windows = [
            # Overnight low liquidity
            (time(0, 0), time(8, 30)),
            
            # Lunch doldrums
            (time(11, 45), time(12, 45)),
            
            # Evening low liquidity
            (time(18, 0), time(23, 59)),
        ]
        
        return TimeFilter(
            timezone="America/New_York",
            no_trade_windows=no_trade_windows
        )
