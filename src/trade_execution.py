"""
Enhanced Trade Execution - Stop placement and entry logic

EXECUTION LOGIC (WHERE MOST BOTS DIE):
- Stop placement: beyond invalidation, outside noise, volatility-adjusted
- Entry logic: break + retest, pullback, or limit at fractal midpoint
- Time-based stops: exit if no movement within N candles
"""

from typing import Any, Dict, List, Optional
import numpy as np
from datetime import datetime


class TradeExecution:
    """
    Handles entry logic, stop placement, and time-based position management.
    """
    
    def __init__(
        self,
        entry_mode: str = "break_retest",  # break_retest, pullback, limit_midpoint
        stop_atr_multiplier: float = 1.5,  # Stop distance in ATR units
        min_rr_ratio: float = 2.0,  # Minimum risk:reward ratio
        time_stop_candles: int = 8,  # Max candles to hold if no movement
        atr_period: int = 14
    ):
        """
        Args:
            entry_mode: Entry strategy (break_retest, pullback, limit_midpoint)
            stop_atr_multiplier: Stop distance as multiple of ATR
            min_rr_ratio: Minimum risk:reward ratio required
            time_stop_candles: Exit after this many candles with no progress
            atr_period: Period for ATR calculation
        """
        valid_entry_modes = ["break_retest", "pullback", "limit_midpoint"]
        if entry_mode not in valid_entry_modes:
            raise ValueError(f"entry_mode must be one of {valid_entry_modes}")
        
        self.entry_mode = entry_mode
        self.stop_atr_multiplier = stop_atr_multiplier
        self.min_rr_ratio = min_rr_ratio
        self.time_stop_candles = time_stop_candles
        self.atr_period = atr_period
    
    def calculate_entry_stop_target(
        self,
        candles: List[Dict[str, Any]],
        direction: str,
        fractal_level: float = None,
        invalidation_level: float = None
    ) -> Dict[str, Any]:
        """
        Calculate entry price, stop loss, and target based on execution rules.
        
        Args:
            candles: Price data
            direction: "long" or "short"
            fractal_level: Key fractal level (swing high/low)
            invalidation_level: Price level that invalidates the setup
            
        Returns:
            Dict with entry, stop, target, and risk metrics
        """
        if len(candles) < self.atr_period:
            return {
                "valid": False,
                "reason": "Insufficient data for execution calculation"
            }
        
        current_price = float(candles[-1]['close'])
        
        # Calculate ATR for volatility-adjusted stops
        atr = self._calculate_current_atr(candles)
        
        # Determine entry price based on entry mode
        if self.entry_mode == "break_retest":
            entry_price = self._calculate_break_retest_entry(
                candles, direction, fractal_level, current_price
            )
        elif self.entry_mode == "pullback":
            entry_price = self._calculate_pullback_entry(
                candles, direction, fractal_level, current_price
            )
        else:  # limit_midpoint
            entry_price = self._calculate_limit_entry(
                candles, direction, fractal_level, current_price
            )
        
        # Calculate stop loss (beyond invalidation, outside noise)
        stop_loss = self._calculate_stop_loss(
            entry_price, direction, atr, invalidation_level
        )
        
        # Calculate risk
        if direction == "long":
            risk = entry_price - stop_loss
        else:  # short
            risk = stop_loss - entry_price
        
        # Calculate target (based on min R:R ratio)
        if direction == "long":
            target = entry_price + (risk * self.min_rr_ratio)
        else:  # short
            target = entry_price - (risk * self.min_rr_ratio)
        
        # Validate R:R ratio
        if risk <= 0:
            return {
                "valid": False,
                "reason": "Invalid risk calculation (risk <= 0)"
            }
        
        reward = abs(target - entry_price)
        rr_ratio = reward / risk
        
        if rr_ratio < self.min_rr_ratio:
            return {
                "valid": False,
                "reason": f"R:R ratio {rr_ratio:.2f} below minimum {self.min_rr_ratio:.2f}"
            }
        
        return {
            "valid": True,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target": target,
            "risk": risk,
            "reward": reward,
            "rr_ratio": rr_ratio,
            "atr": atr,
            "direction": direction,
            "entry_mode": self.entry_mode
        }
    
    def _calculate_current_atr(self, candles: List[Dict[str, Any]]) -> float:
        """Calculate current ATR value"""
        highs = np.array([float(c['high']) for c in candles[-self.atr_period-1:]])
        lows = np.array([float(c['low']) for c in candles[-self.atr_period-1:]])
        closes = np.array([float(c['close']) for c in candles[-self.atr_period-1:]])
        
        # Calculate True Range
        tr = np.zeros(len(highs))
        tr[0] = highs[0] - lows[0]
        
        for i in range(1, len(highs)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            tr[i] = max(hl, hc, lc)
        
        # Return average of recent true ranges
        return np.mean(tr[-self.atr_period:])
    
    def _calculate_break_retest_entry(
        self,
        candles: List[Dict[str, Any]],
        direction: str,
        fractal_level: float,
        current_price: float
    ) -> float:
        """
        Break + retest entry: enter on pullback after initial break
        """
        if fractal_level is None:
            return current_price
        
        # For longs: enter slightly above fractal level on retest
        # For shorts: enter slightly below fractal level on retest
        if direction == "long":
            return fractal_level * 1.0005  # 0.05% above
        else:
            return fractal_level * 0.9995  # 0.05% below
    
    def _calculate_pullback_entry(
        self,
        candles: List[Dict[str, Any]],
        direction: str,
        fractal_level: float,
        current_price: float
    ) -> float:
        """
        Pullback entry: enter on pullback to key level
        """
        if fractal_level is None:
            return current_price
        
        # Enter at the fractal level on pullback
        return fractal_level
    
    def _calculate_limit_entry(
        self,
        candles: List[Dict[str, Any]],
        direction: str,
        fractal_level: float,
        current_price: float
    ) -> float:
        """
        Limit entry at fractal midpoint
        """
        if fractal_level is None:
            return current_price
        
        # Enter at midpoint between current price and fractal level
        return (current_price + fractal_level) / 2
    
    def _calculate_stop_loss(
        self,
        entry_price: float,
        direction: str,
        atr: float,
        invalidation_level: float = None
    ) -> float:
        """
        Calculate stop loss:
        - Beyond invalidation level
        - Outside noise (ATR-based buffer)
        - Volatility-adjusted
        """
        # Base stop: ATR multiple from entry
        stop_distance = atr * self.stop_atr_multiplier
        
        if direction == "long":
            # Stop below entry
            atr_stop = entry_price - stop_distance
            
            # If invalidation level provided, use the lower of the two
            if invalidation_level is not None:
                # Add small buffer below invalidation
                invalidation_stop = invalidation_level - (atr * 0.2)
                return min(atr_stop, invalidation_stop)
            
            return atr_stop
        
        else:  # short
            # Stop above entry
            atr_stop = entry_price + stop_distance
            
            # If invalidation level provided, use the higher of the two
            if invalidation_level is not None:
                # Add small buffer above invalidation
                invalidation_stop = invalidation_level + (atr * 0.2)
                return max(atr_stop, invalidation_stop)
            
            return atr_stop
    
    def check_time_stop(
        self,
        entry_time: int,
        current_time: int,
        entry_price: float,
        current_price: float,
        direction: str,
        candles_since_entry: int
    ) -> Dict[str, Any]:
        """
        Check if position should be closed due to time stop.
        
        Args:
            entry_time: Entry timestamp (ms)
            current_time: Current timestamp (ms)
            entry_price: Entry price
            current_price: Current price
            direction: "long" or "short"
            candles_since_entry: Number of candles since entry
            
        Returns:
            Dict with should_exit and reason
        """
        # Check if exceeded max candles
        if candles_since_entry >= self.time_stop_candles:
            # Check if price has moved meaningfully
            price_change_pct = abs(current_price - entry_price) / entry_price
            
            # If less than 0.3% movement, exit (stagnation)
            if price_change_pct < 0.003:
                return {
                    "should_exit": True,
                    "reason": f"Time stop triggered: {candles_since_entry} candles with minimal movement ({price_change_pct:.2%})",
                    "exit_type": "time_stop"
                }
        
        return {
            "should_exit": False,
            "reason": "Time stop not triggered",
            "exit_type": None
        }
