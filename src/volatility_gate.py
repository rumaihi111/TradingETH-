"""
Volatility Gate - Prevents trading in low-volatility compressed conditions

The bot may only trade nested fractals when volatility is NOT compressed.
Low volatility = spreads eat you, breakouts fail, fractals become meaningless geometry.
"""

from typing import Any, Dict, List
import numpy as np


class VolatilityGate:
    """
    Measures current ATR vs recent ATR average to detect compression.
    Blocks trades during compressed volatility conditions.
    """
    
    def __init__(
        self,
        atr_period: int = 14,
        lookback_multiplier: int = 3,
        compression_threshold: float = 0.75,  # 75% of average
        require_expansion: bool = True
    ):
        """
        Args:
            atr_period: Period for ATR calculation
            lookback_multiplier: Multiplier for lookback (lookback = atr_period * multiplier)
            compression_threshold: Ratio below which volatility is considered compressed (0.7-0.8)
            require_expansion: Whether to require expansion or expansion transition
        """
        self.atr_period = atr_period
        self.lookback_period = atr_period * lookback_multiplier
        self.compression_threshold = compression_threshold
        self.require_expansion = require_expansion
    
    def check(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check if volatility conditions allow trading.
        
        Returns:
            Dict with:
                - can_trade: bool
                - reason: str
                - current_atr: float
                - average_atr: float
                - ratio: float
                - state: str (compressed/normal/expanding)
        """
        if len(candles) < self.lookback_period + self.atr_period:
            return {
                "can_trade": False,
                "reason": "Insufficient data for volatility analysis",
                "current_atr": 0,
                "average_atr": 0,
                "ratio": 0,
                "state": "unknown"
            }
        
        # Calculate ATR for all candles
        atr_values = self._calculate_atr(candles, self.atr_period)
        
        # Current ATR (most recent)
        current_atr = atr_values[-1]
        
        # Average ATR over lookback period
        lookback_atr_values = atr_values[-self.lookback_period:]
        average_atr = np.mean(lookback_atr_values)
        
        # Calculate ratio
        ratio = current_atr / average_atr if average_atr > 0 else 0
        
        # Determine state
        if ratio < self.compression_threshold:
            state = "compressed"
        elif ratio > 1.2:  # Expanding if > 120% of average
            state = "expanding"
        else:
            state = "normal"
        
        # Check for compression -> expansion transition
        if self.require_expansion and len(atr_values) >= 3:
            # Check if we're transitioning from compressed to expanding
            prev_ratio = atr_values[-2] / average_atr if average_atr > 0 else 0
            is_transitioning = (
                prev_ratio < self.compression_threshold and 
                ratio >= self.compression_threshold
            )
        else:
            is_transitioning = False
        
        # Decision logic
        can_trade = False
        reason = ""
        
        if state == "compressed":
            reason = f"Volatility compressed: {ratio:.2%} of average (threshold: {self.compression_threshold:.2%})"
        elif state == "expanding" or is_transitioning:
            can_trade = True
            reason = f"Volatility expanding: {ratio:.2%} of average - TRADE ALLOWED"
        elif state == "normal" and not self.require_expansion:
            can_trade = True
            reason = f"Volatility normal: {ratio:.2%} of average - TRADE ALLOWED"
        else:
            reason = f"Volatility not expanding: {ratio:.2%} of average - waiting for expansion"
        
        return {
            "can_trade": can_trade,
            "reason": reason,
            "current_atr": current_atr,
            "average_atr": average_atr,
            "ratio": ratio,
            "state": state,
            "is_transitioning": is_transitioning if self.require_expansion else None
        }
    
    def _calculate_atr(self, candles: List[Dict[str, Any]], period: int) -> np.ndarray:
        """
        Calculate Average True Range (ATR) for candles.
        
        True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
        ATR = moving average of True Range
        """
        highs = np.array([float(c['high']) for c in candles])
        lows = np.array([float(c['low']) for c in candles])
        closes = np.array([float(c['close']) for c in candles])
        
        # Calculate True Range
        tr = np.zeros(len(candles))
        tr[0] = highs[0] - lows[0]  # First candle has no previous close
        
        for i in range(1, len(candles)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            tr[i] = max(hl, hc, lc)
        
        # Calculate ATR using exponential moving average
        atr = np.zeros(len(candles))
        atr[period-1] = np.mean(tr[:period])
        
        multiplier = 2 / (period + 1)
        for i in range(period, len(candles)):
            atr[i] = (tr[i] * multiplier) + (atr[i-1] * (1 - multiplier))
        
        return atr
    
    def get_normalized_leg_size(self, candles: List[Dict[str, Any]], start_idx: int, end_idx: int) -> float:
        """
        Calculate normalized leg size as a ratio of ATR.
        This makes leg sizes comparable regardless of absolute price.
        
        Args:
            candles: Candle data
            start_idx: Start index of leg
            end_idx: End index of leg
            
        Returns:
            Leg size normalized by ATR (ratio)
        """
        if end_idx <= start_idx or end_idx >= len(candles):
            return 0.0
        
        # Calculate ATR
        atr_values = self._calculate_atr(candles, self.atr_period)
        
        # Get price change
        start_price = float(candles[start_idx]['close'])
        end_price = float(candles[end_idx]['close'])
        price_change = abs(end_price - start_price)
        
        # Normalize by ATR at the end of the leg
        atr = atr_values[end_idx]
        if atr == 0:
            return 0.0
        
        return price_change / atr
