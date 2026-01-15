"""
Multi-Timeframe Market Structure Analyzer

Analyzes market structure across multiple timeframes:
- 15-minute for bias (HH/HL = bullish, LH/LL = bearish)
- 5-minute for execution (nested fractals)

Rules:
- HH/HL on 15m → ONLY long fractals on 5m
- LH/LL on 15m → ONLY short fractals on 5m  
- Mixed / flat → NO TRADES
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class MultiTimeframeAnalyzer:
    """
    Analyzes market structure across multiple timeframes.
    Primary timeframe (15m) determines bias.
    Execution timeframe (5m) provides entry signals.
    """
    
    def __init__(
        self,
        bias_lookback: int = 20,  # Candles to look back for bias determination
        swing_sensitivity: float = 0.5  # Sensitivity for swing detection (as % of ATR)
    ):
        """
        Args:
            bias_lookback: Number of candles to analyze for bias
            swing_sensitivity: Minimum move size to qualify as swing (% of ATR)
        """
        self.bias_lookback = bias_lookback
        self.swing_sensitivity = swing_sensitivity
    
    def analyze_bias(
        self,
        candles_15m: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze 15-minute timeframe to determine bias.
        
        Returns:
            Dict with:
                - bias: str (bullish/bearish/neutral)
                - structure: str (HH_HL/LH_LL/mixed)
                - confidence: float (0-1)
                - last_swing_high: float
                - last_swing_low: float
                - reason: str
        """
        if len(candles_15m) < self.bias_lookback:
            return {
                "bias": "neutral",
                "structure": "insufficient_data",
                "confidence": 0.0,
                "last_swing_high": None,
                "last_swing_low": None,
                "reason": "Insufficient 15m data for bias determination"
            }
        
        # Get recent candles for analysis
        recent = candles_15m[-self.bias_lookback:]
        
        # Calculate ATR for swing detection
        atr = self._calculate_atr(recent, period=14)
        
        # Find swing highs and lows
        swings = self._find_swings(recent, atr * self.swing_sensitivity)
        
        if len(swings) < 2:
            return {
                "bias": "neutral",
                "structure": "insufficient_swings",
                "confidence": 0.0,
                "last_swing_high": None,
                "last_swing_low": None,
                "reason": "Not enough swing points for structure analysis"
            }
        
        # Analyze structure (HH/HL vs LH/LL)
        structure_analysis = self._analyze_structure(swings)
        
        return structure_analysis
    
    def check_alignment(
        self,
        bias_15m: Dict[str, Any],
        direction_5m: str
    ) -> Dict[str, bool]:
        """
        Check if 5m trade direction aligns with 15m bias.
        
        Args:
            bias_15m: Result from analyze_bias()
            direction_5m: Proposed trade direction on 5m ("long" or "short")
            
        Returns:
            Dict with:
                - aligned: bool
                - can_trade: bool
                - reason: str
        """
        bias = bias_15m["bias"]
        structure = bias_15m["structure"]
        confidence = bias_15m["confidence"]
        
        # Neutral bias = NO TRADES
        if bias == "neutral":
            return {
                "aligned": False,
                "can_trade": False,
                "reason": f"15m bias is neutral ({structure}) - NO TRADES"
            }
        
        # Check alignment
        if bias == "bullish" and direction_5m == "long":
            return {
                "aligned": True,
                "can_trade": True,
                "reason": f"15m bullish ({structure}), 5m long - ALIGNED ✓",
                "confidence": confidence
            }
        
        if bias == "bearish" and direction_5m == "short":
            return {
                "aligned": True,
                "can_trade": True,
                "reason": f"15m bearish ({structure}), 5m short - ALIGNED ✓",
                "confidence": confidence
            }
        
        # Misaligned
        return {
            "aligned": False,
            "can_trade": False,
            "reason": f"15m {bias} ({structure}), but 5m {direction_5m} - MISALIGNED ✗",
            "confidence": confidence
        }
    
    def _calculate_atr(self, candles: List[Dict[str, Any]], period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(candles) < period + 1:
            # Fallback: use simple range
            highs = [float(c['high']) for c in candles]
            lows = [float(c['low']) for c in candles]
            return (max(highs) - min(lows)) / len(candles)
        
        highs = np.array([float(c['high']) for c in candles])
        lows = np.array([float(c['low']) for c in candles])
        closes = np.array([float(c['close']) for c in candles])
        
        # Calculate True Range
        tr = np.zeros(len(candles))
        tr[0] = highs[0] - lows[0]
        
        for i in range(1, len(candles)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            tr[i] = max(hl, hc, lc)
        
        # Return average of recent true ranges
        return np.mean(tr[-period:])
    
    def _find_swings(
        self,
        candles: List[Dict[str, Any]],
        min_move: float
    ) -> List[Dict[str, Any]]:
        """
        Find significant swing highs and lows.
        
        Returns:
            List of swing points with type (high/low), price, and index
        """
        swings = []
        
        for i in range(2, len(candles) - 2):
            high = float(candles[i]['high'])
            low = float(candles[i]['low'])
            
            # Check for swing high (higher than 2 candles before and after)
            if (high > float(candles[i-1]['high']) and
                high > float(candles[i-2]['high']) and
                high > float(candles[i+1]['high']) and
                high > float(candles[i+2]['high'])):
                
                # Check if significant enough
                if not swings or abs(high - swings[-1]['price']) >= min_move:
                    swings.append({
                        'type': 'high',
                        'price': high,
                        'index': i,
                        'time': candles[i].get('ts', candles[i].get('time', 0))
                    })
            
            # Check for swing low (lower than 2 candles before and after)
            if (low < float(candles[i-1]['low']) and
                low < float(candles[i-2]['low']) and
                low < float(candles[i+1]['low']) and
                low < float(candles[i+2]['low'])):
                
                # Check if significant enough
                if not swings or abs(low - swings[-1]['price']) >= min_move:
                    swings.append({
                        'type': 'low',
                        'price': low,
                        'index': i,
                        'time': candles[i].get('ts', candles[i].get('time', 0))
                    })
        
        return swings
    
    def _analyze_structure(self, swings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze swing structure to determine bias.
        
        HH/HL = Higher Highs and Higher Lows = Bullish
        LH/LL = Lower Highs and Lower Lows = Bearish
        Mixed = Neutral
        """
        highs = [s for s in swings if s['type'] == 'high']
        lows = [s for s in swings if s['type'] == 'low']
        
        if len(highs) < 2 or len(lows) < 2:
            return {
                "bias": "neutral",
                "structure": "insufficient_swings",
                "confidence": 0.0,
                "last_swing_high": highs[-1]['price'] if highs else None,
                "last_swing_low": lows[-1]['price'] if lows else None,
                "reason": "Need at least 2 swing highs and 2 swing lows"
            }
        
        # Check for HH (Higher Highs)
        recent_highs = highs[-2:]
        hh = recent_highs[-1]['price'] > recent_highs[-2]['price']
        
        # Check for HL (Higher Lows)
        recent_lows = lows[-2:]
        hl = recent_lows[-1]['price'] > recent_lows[-2]['price']
        
        # Check for LH (Lower Highs)
        lh = recent_highs[-1]['price'] < recent_highs[-2]['price']
        
        # Check for LL (Lower Lows)
        ll = recent_lows[-1]['price'] < recent_lows[-2]['price']
        
        # Determine structure
        if hh and hl:
            # Higher Highs and Higher Lows = Bullish
            return {
                "bias": "bullish",
                "structure": "HH_HL",
                "confidence": 0.8,
                "last_swing_high": highs[-1]['price'],
                "last_swing_low": lows[-1]['price'],
                "reason": "Higher Highs and Higher Lows detected on 15m"
            }
        elif lh and ll:
            # Lower Highs and Lower Lows = Bearish
            return {
                "bias": "bearish",
                "structure": "LH_LL",
                "confidence": 0.8,
                "last_swing_high": highs[-1]['price'],
                "last_swing_low": lows[-1]['price'],
                "reason": "Lower Highs and Lower Lows detected on 15m"
            }
        else:
            # Mixed structure = Neutral
            return {
                "bias": "neutral",
                "structure": "mixed",
                "confidence": 0.3,
                "last_swing_high": highs[-1]['price'],
                "last_swing_low": lows[-1]['price'],
                "reason": f"Mixed structure on 15m: HH={hh}, HL={hl}, LH={lh}, LL={ll}"
            }
