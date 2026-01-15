"""
Session Context - Identifies key session levels and range boundaries

Fractals near session extremes behave differently.
Middle of range = garbage. Extremes = high probability.
"""

from typing import Any, Dict, List, Optional
import numpy as np
from datetime import datetime, timedelta
import pytz


class SessionContext:
    """
    Tracks session high, low, and range boundaries.
    Provides context about where price is relative to session structure.
    """
    
    def __init__(
        self,
        timezone: str = "America/New_York",
        session_start_hour: int = 9,
        session_start_minute: int = 30,
        lookback_sessions: int = 1
    ):
        """
        Args:
            timezone: Timezone for session definition
            session_start_hour: Hour when session starts (24h format)
            session_start_minute: Minute when session starts
            lookback_sessions: Number of sessions to include in analysis
        """
        self.timezone = pytz.timezone(timezone)
        self.session_start_hour = session_start_hour
        self.session_start_minute = session_start_minute
        self.lookback_sessions = lookback_sessions
    
    def analyze(self, candles: List[Dict[str, Any]], current_price: float = None) -> Dict[str, Any]:
        """
        Analyze current session context.
        
        Returns:
            Dict with:
                - session_high: float
                - session_low: float
                - session_range: float
                - current_position: str (upper/middle/lower)
                - position_pct: float (0-1, position within range)
                - distance_to_high: float
                - distance_to_low: float
                - near_extreme: bool
                - extreme_type: str (high/low/none)
        """
        if len(candles) < 10:
            return {
                "session_high": None,
                "session_low": None,
                "session_range": None,
                "current_position": "unknown",
                "position_pct": 0.5,
                "distance_to_high": None,
                "distance_to_low": None,
                "near_extreme": False,
                "extreme_type": "none"
            }
        
        # Get session candles
        session_candles = self._get_session_candles(candles)
        
        if not session_candles:
            return {
                "session_high": None,
                "session_low": None,
                "session_range": None,
                "current_position": "unknown",
                "position_pct": 0.5,
                "distance_to_high": None,
                "distance_to_low": None,
                "near_extreme": False,
                "extreme_type": "none"
            }
        
        # Calculate session high and low
        highs = [float(c['high']) for c in session_candles]
        lows = [float(c['low']) for c in session_candles]
        
        session_high = max(highs)
        session_low = min(lows)
        session_range = session_high - session_low
        
        # Use current price or last close
        if current_price is None:
            current_price = float(candles[-1]['close'])
        
        # Calculate position within range
        if session_range > 0:
            position_pct = (current_price - session_low) / session_range
        else:
            position_pct = 0.5
        
        # Determine position (upper/middle/lower third)
        if position_pct >= 0.66:
            current_position = "upper"
        elif position_pct <= 0.33:
            current_position = "lower"
        else:
            current_position = "middle"
        
        # Calculate distances
        distance_to_high = session_high - current_price
        distance_to_low = current_price - session_low
        
        # Determine if near extreme (within 10% of range)
        near_extreme = position_pct >= 0.90 or position_pct <= 0.10
        
        if position_pct >= 0.90:
            extreme_type = "high"
        elif position_pct <= 0.10:
            extreme_type = "low"
        else:
            extreme_type = "none"
        
        return {
            "session_high": session_high,
            "session_low": session_low,
            "session_range": session_range,
            "current_position": current_position,
            "position_pct": position_pct,
            "distance_to_high": distance_to_high,
            "distance_to_low": distance_to_low,
            "distance_to_high_pct": distance_to_high / session_range if session_range > 0 else 0,
            "distance_to_low_pct": distance_to_low / session_range if session_range > 0 else 0,
            "near_extreme": near_extreme,
            "extreme_type": extreme_type,
            "session_candle_count": len(session_candles)
        }
    
    def _get_session_candles(self, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter candles to only include those in the current session(s).
        """
        if not candles:
            return []
        
        # Get current time
        last_candle_ts = candles[-1].get('ts', candles[-1].get('time', 0))
        current_dt = datetime.fromtimestamp(last_candle_ts / 1000, tz=pytz.UTC)
        current_dt = current_dt.astimezone(self.timezone)
        
        # Calculate session start time for today
        session_start = current_dt.replace(
            hour=self.session_start_hour,
            minute=self.session_start_minute,
            second=0,
            microsecond=0
        )
        
        # If current time is before session start, use yesterday's session
        if current_dt < session_start:
            session_start -= timedelta(days=1)
        
        # If looking back multiple sessions, adjust start time
        if self.lookback_sessions > 1:
            session_start -= timedelta(days=self.lookback_sessions - 1)
        
        # Convert to UTC timestamp
        session_start_utc = session_start.astimezone(pytz.UTC)
        session_start_ts = int(session_start_utc.timestamp() * 1000)
        
        # Filter candles
        session_candles = [
            c for c in candles
            if c.get('ts', c.get('time', 0)) >= session_start_ts
        ]
        
        return session_candles
    
    def should_trade_at_level(self, analysis: Dict[str, Any], direction: str) -> Dict[str, bool]:
        """
        Determine if trading at current level makes sense based on session context.
        
        Args:
            analysis: Result from analyze()
            direction: "long" or "short"
            
        Returns:
            Dict with:
                - should_trade: bool
                - reason: str
                - quality_score: float (0-1)
        """
        if analysis["session_range"] is None:
            return {
                "should_trade": True,
                "reason": "No session data available",
                "quality_score": 0.5
            }
        
        position_pct = analysis["position_pct"]
        current_position = analysis["current_position"]
        near_extreme = analysis["near_extreme"]
        extreme_type = analysis["extreme_type"]
        
        # RULE: Middle of range = garbage
        if current_position == "middle" and not near_extreme:
            return {
                "should_trade": False,
                "reason": f"Price in middle of range ({position_pct:.1%}) - low quality setup",
                "quality_score": 0.2
            }
        
        # RULE: Longs near session high = risky
        if direction == "long" and extreme_type == "high":
            return {
                "should_trade": False,
                "reason": f"Long near session high ({position_pct:.1%}) - limited upside",
                "quality_score": 0.3
            }
        
        # RULE: Shorts near session low = risky
        if direction == "short" and extreme_type == "low":
            return {
                "should_trade": False,
                "reason": f"Short near session low ({position_pct:.1%}) - limited downside",
                "quality_score": 0.3
            }
        
        # RULE: Longs in lower third = good
        if direction == "long" and current_position == "lower":
            return {
                "should_trade": True,
                "reason": f"Long in lower third ({position_pct:.1%}) - room to run",
                "quality_score": 0.9
            }
        
        # RULE: Shorts in upper third = good
        if direction == "short" and current_position == "upper":
            return {
                "should_trade": True,
                "reason": f"Short in upper third ({position_pct:.1%}) - room to run",
                "quality_score": 0.9
            }
        
        # Default: allow but with medium quality
        return {
            "should_trade": True,
            "reason": f"Position acceptable ({position_pct:.1%})",
            "quality_score": 0.6
        }
