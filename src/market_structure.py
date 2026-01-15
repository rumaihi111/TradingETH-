"""
Market Structure Analysis - Multi-Timeframe & Context Awareness

Implements:
- Multi-timeframe bias detection (15m for bias, 5m for execution)
- Market structure: HH/HL (bullish) vs LH/LL (bearish)
- ATR-based volatility analysis and compression detection
- Time-of-day filtering
- Session context (high/low/range boundaries)
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, time as dt_time
import numpy as np


class MarketStructure:
    """Analyzes market structure across multiple timeframes"""
    
    def __init__(
        self,
        atr_period: int = 14,
        atr_compression_threshold: float = 0.75,  # 75% of average ATR
        structure_lookback: int = 20,  # Candles to analyze for HH/HL pattern
    ):
        self.atr_period = atr_period
        self.atr_compression_threshold = atr_compression_threshold
        self.structure_lookback = structure_lookback
    
    def analyze(
        self,
        candles_5m: List[Dict[str, Any]],
        candles_15m: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive market structure analysis
        
        Args:
            candles_5m: 5-minute candles for execution timeframe
            candles_15m: 15-minute candles for bias detection (optional)
        
        Returns:
            Dict with structure analysis results
        """
        if len(candles_5m) < 30:
            return {
                "allowed_to_trade": False,
                "reason": "Insufficient data",
                "bias": "neutral"
            }
        
        # Extract 5m data
        closes_5m = np.array([float(c['close']) for c in candles_5m])
        highs_5m = np.array([float(c['high']) for c in candles_5m])
        lows_5m = np.array([float(c['low']) for c in candles_5m])
        
        # Calculate ATR on 5m
        atr_current, atr_avg, atr_ratio = self._calculate_atr_metrics(highs_5m, lows_5m, closes_5m)
        
        # Check volatility compression
        volatility_compressed = atr_ratio < self.atr_compression_threshold
        
        # Detect bias on 15m (or fall back to 5m)
        if candles_15m and len(candles_15m) >= 20:
            bias = self._detect_bias(candles_15m)
            bias_timeframe = "15m"
        else:
            bias = self._detect_bias(candles_5m)
            bias_timeframe = "5m"
        
        # Time-of-day filter
        time_allowed, time_reason = self._check_time_filter(candles_5m[-1])
        
        # Session context
        session_context = self._analyze_session_context(candles_5m)
        
        # Determine if trading is allowed
        allowed = True
        reasons = []
        
        if volatility_compressed:
            allowed = False
            reasons.append(f"Volatility compressed (ATR {atr_ratio:.1%} of average)")
        
        if bias == "neutral":
            allowed = False
            reasons.append("No clear market bias (mixed structure)")
        
        if not time_allowed:
            allowed = False
            reasons.append(time_reason)
        
        return {
            "allowed_to_trade": allowed,
            "reason": "; ".join(reasons) if reasons else "All filters passed",
            "bias": bias,
            "bias_timeframe": bias_timeframe,
            "volatility": {
                "atr_current": float(atr_current),
                "atr_average": float(atr_avg),
                "atr_ratio": float(atr_ratio),
                "compressed": volatility_compressed,
            },
            "time_filter": {
                "allowed": time_allowed,
                "reason": time_reason,
            },
            "session": session_context,
        }
    
    def _calculate_atr_metrics(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray
    ) -> Tuple[float, float, float]:
        """
        Calculate current ATR, recent average ATR, and their ratio
        
        Returns:
            (current_atr, average_atr, ratio)
        """
        # Calculate True Range
        if len(closes) < 2:
            return 0.0, 0.0, 1.0
        
        high_low = highs - lows
        high_close = np.abs(highs[1:] - closes[:-1])
        low_close = np.abs(lows[1:] - closes[:-1])
        
        # Pad first element
        high_close = np.concatenate([[high_low[0]], high_close])
        low_close = np.concatenate([[high_low[0]], low_close])
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        
        # Calculate ATR using EMA
        if len(true_range) < self.atr_period:
            atr = np.mean(true_range)
            atr_values = true_range
        else:
            atr_values = self._ema(true_range, self.atr_period)
            atr = atr_values[-1]
        
        # Average ATR over recent period (last 50 candles or available)
        lookback = min(50, len(atr_values))
        atr_avg = np.mean(atr_values[-lookback:])
        
        # Calculate ratio
        ratio = atr / atr_avg if atr_avg > 0 else 1.0
        
        return atr, atr_avg, ratio
    
    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        
        return ema
    
    def _detect_bias(self, candles: List[Dict[str, Any]]) -> str:
        """
        Detect market bias based on Higher Highs/Higher Lows vs Lower Highs/Lower Lows
        
        Returns:
            "bullish", "bearish", or "neutral"
        """
        if len(candles) < self.structure_lookback:
            return "neutral"
        
        # Get recent highs and lows
        recent = candles[-self.structure_lookback:]
        highs = [float(c['high']) for c in recent]
        lows = [float(c['low']) for c in recent]
        
        # Find swing points (local maxima and minima)
        swing_highs = self._find_swing_points(highs, is_high=True)
        swing_lows = self._find_swing_points(lows, is_high=False)
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return "neutral"
        
        # Check for Higher Highs and Higher Lows (bullish)
        hh_count = sum(1 for i in range(1, len(swing_highs)) if swing_highs[i] > swing_highs[i-1])
        hl_count = sum(1 for i in range(1, len(swing_lows)) if swing_lows[i] > swing_lows[i-1])
        
        # Check for Lower Highs and Lower Lows (bearish)
        lh_count = sum(1 for i in range(1, len(swing_highs)) if swing_highs[i] < swing_highs[i-1])
        ll_count = sum(1 for i in range(1, len(swing_lows)) if swing_lows[i] < swing_lows[i-1])
        
        # Determine bias
        bullish_score = hh_count + hl_count
        bearish_score = lh_count + ll_count
        
        # Require clear dominance (at least 2:1 ratio)
        if bullish_score >= bearish_score * 2:
            return "bullish"
        elif bearish_score >= bullish_score * 2:
            return "bearish"
        else:
            return "neutral"
    
    def _find_swing_points(self, data: List[float], is_high: bool = True) -> List[float]:
        """Find swing highs or swing lows in price data"""
        swing_points = []
        window = 3  # Look 3 candles back and forward
        
        for i in range(window, len(data) - window):
            if is_high:
                # Check if this is a local maximum
                if all(data[i] >= data[i-j] for j in range(1, window+1)) and \
                   all(data[i] >= data[i+j] for j in range(1, window+1)):
                    swing_points.append(data[i])
            else:
                # Check if this is a local minimum
                if all(data[i] <= data[i-j] for j in range(1, window+1)) and \
                   all(data[i] <= data[i+j] for j in range(1, window+1)):
                    swing_points.append(data[i])
        
        return swing_points
    
    def _check_time_filter(self, latest_candle: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if current time is allowed for trading
        
        Blocks:
        - Lunch hour: 11:30 AM - 1:00 PM EST
        - End of session: 3:30 PM - 4:00 PM EST
        
        Note: This assumes candle timestamps are in UTC
        """
        timestamp = latest_candle.get('ts', latest_candle.get('time', 0))
        if timestamp == 0:
            return True, "No timestamp available"
        
        # Convert to UTC time
        dt = datetime.fromtimestamp(timestamp / 1000)
        current_time = dt.time()
        current_hour = dt.hour
        
        # Convert UTC to EST for market hours check (EST = UTC - 5)
        # Note: This is simplified and doesn't handle DST
        est_hour = (current_hour - 5) % 24
        
        # Lunch hour block: 11:30 AM - 1:00 PM EST (16:30 - 18:00 UTC)
        if 16 <= est_hour < 18 or (est_hour == 16 and dt.minute >= 30):
            return False, "Lunch hour trading block"
        
        # End of session block: 3:30 PM - 4:00 PM EST (20:30 - 21:00 UTC)
        if est_hour == 20 and dt.minute >= 30:
            return False, "End of session trading block"
        if est_hour == 21:
            return False, "End of session trading block"
        
        return True, "Time filter passed"
    
    def _analyze_session_context(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze session-level context: highs, lows, range boundaries
        
        Uses last 78 candles (~6.5 hours on 5m chart) to define session
        """
        session_size = min(78, len(candles))
        session_candles = candles[-session_size:]
        
        highs = [float(c['high']) for c in session_candles]
        lows = [float(c['low']) for c in session_candles]
        closes = [float(c['close']) for c in session_candles]
        
        session_high = max(highs)
        session_low = min(lows)
        session_range = session_high - session_low
        current_price = closes[-1]
        
        # Determine position in range
        if session_range > 0:
            range_position = (current_price - session_low) / session_range
        else:
            range_position = 0.5
        
        # Categorize position
        if range_position >= 0.8:
            position_label = "near_high"
        elif range_position <= 0.2:
            position_label = "near_low"
        else:
            position_label = "mid_range"
        
        return {
            "high": float(session_high),
            "low": float(session_low),
            "range": float(session_range),
            "range_pct": float(session_range / session_low * 100) if session_low > 0 else 0,
            "current_position": float(range_position),
            "position_label": position_label,
        }
    
    def get_trade_direction(self, bias: str) -> Optional[str]:
        """
        Convert market bias to allowed trade direction
        
        Args:
            bias: "bullish", "bearish", or "neutral"
        
        Returns:
            "long", "short", or None
        """
        if bias == "bullish":
            return "long"
        elif bias == "bearish":
            return "short"
        else:
            return None
