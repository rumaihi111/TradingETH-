"""
Nested Fractal Brain - Pattern Recognition at Multiple Scales

This brain detects unique patterns that repeat at two different scales
within the same trading session. Looks for unusual shapes like staircases,
mountains, words, or any non-standard pattern that appears fractally.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime


class NestedFractalBrain:
    """
    Detects nested fractal patterns - same unique shape repeating at different scales.
    Focuses on unusual patterns, not standard trading patterns.
    """
    
    def __init__(self, min_similarity: float = 0.75, scale_ratio_min: float = 2.0):
        """
        Args:
            min_similarity: Minimum correlation coefficient to consider a match (0-1)
            scale_ratio_min: Minimum ratio between large and small pattern timescales
        """
        self.min_similarity = min_similarity
        self.scale_ratio_min = scale_ratio_min
    
    def analyze(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze candles for nested fractal patterns.
        
        Returns:
            Dict with fractal analysis results
        """
        if len(candles) < 30:
            return {
                "fractals_found": False,
                "reason": "Insufficient data for fractal analysis",
                "patterns": []
            }
        
        # Extract price data
        prices = [float(c['close']) for c in candles]
        times = [c.get('ts', c.get('time', 0)) for c in candles]
        
        # Normalize prices for pattern matching
        prices_norm = self._normalize(prices)
        
        # Find nested fractals at different scales
        fractals = self._find_nested_patterns(prices_norm, times)
        
        if not fractals:
            return {
                "fractals_found": False,
                "reason": "No nested fractal patterns detected",
                "patterns": []
            }
        
        return {
            "fractals_found": True,
            "pattern_count": len(fractals),
            "patterns": fractals,
            "signal": self._generate_signal(fractals, prices)
        }
    
    def _normalize(self, data: List[float]) -> np.ndarray:
        """Normalize data to 0-1 range for pattern matching"""
        arr = np.array(data)
        min_val = np.min(arr)
        max_val = np.max(arr)
        if max_val == min_val:
            return np.zeros_like(arr)
        return (arr - min_val) / (max_val - min_val)
    
    def _find_nested_patterns(self, prices: np.ndarray, times: List[int]) -> List[Dict[str, Any]]:
        """
        Find patterns that repeat at different scales.
        
        Strategy:
        1. Scan for small patterns (5-15 candles)
        2. Look for larger versions (15-40 candles) of the same shape
        3. Calculate similarity using correlation
        """
        fractals = []
        n = len(prices)
        
        # Search for small patterns (5-15 candles)
        for small_size in range(5, 16):
            for small_start in range(n - small_size):
                small_pattern = prices[small_start:small_start + small_size]
                small_pattern_norm = self._normalize(small_pattern)
                
                # Search for larger patterns (at least 2x the size)
                min_large_size = int(small_size * self.scale_ratio_min)
                max_large_size = min(40, n - small_start)
                
                for large_size in range(min_large_size, max_large_size):
                    for large_start in range(n - large_size):
                        # Don't overlap
                        if large_start + large_size > small_start and large_start < small_start + small_size:
                            continue
                        
                        large_pattern = prices[large_start:large_start + large_size]
                        
                        # Resample large pattern to match small pattern size
                        large_pattern_resampled = self._resample(large_pattern, small_size)
                        large_pattern_norm = self._normalize(large_pattern_resampled)
                        
                        # Calculate similarity
                        similarity = self._calculate_similarity(small_pattern_norm, large_pattern_norm)
                        
                        if similarity >= self.min_similarity:
                            # Describe the pattern shape
                            pattern_shape = self._describe_pattern(small_pattern_norm)
                            
                            fractal = {
                                "type": "nested_fractal",
                                "shape": pattern_shape,
                                "similarity": float(similarity),
                                "scale_ratio": large_size / small_size,
                                "small_pattern": {
                                    "start_idx": small_start,
                                    "end_idx": small_start + small_size,
                                    "size": small_size,
                                    "start_time": datetime.fromtimestamp(times[small_start] / 1000).strftime("%H:%M")
                                },
                                "large_pattern": {
                                    "start_idx": large_start,
                                    "end_idx": large_start + large_size,
                                    "size": large_size,
                                    "start_time": datetime.fromtimestamp(times[large_start] / 1000).strftime("%H:%M")
                                }
                            }
                            fractals.append(fractal)
        
        # Remove duplicate/overlapping patterns, keep best matches
        fractals = self._deduplicate_fractals(fractals)
        
        return fractals[:5]  # Return top 5 fractals
    
    def _resample(self, data: np.ndarray, target_size: int) -> np.ndarray:
        """Resample data to target size using linear interpolation"""
        if len(data) == target_size:
            return data
        
        x_old = np.linspace(0, 1, len(data))
        x_new = np.linspace(0, 1, target_size)
        return np.interp(x_new, x_old, data)
    
    def _calculate_similarity(self, pattern1: np.ndarray, pattern2: np.ndarray) -> float:
        """Calculate similarity between two patterns using correlation"""
        if len(pattern1) != len(pattern2):
            return 0.0
        
        # Pearson correlation coefficient
        corr = np.corrcoef(pattern1, pattern2)[0, 1]
        
        # Handle NaN (happens if one pattern is flat)
        if np.isnan(corr):
            return 0.0
        
        # Return absolute correlation (patterns can be inverted)
        return abs(corr)
    
    def _describe_pattern(self, pattern: np.ndarray) -> str:
        """
        Describe the shape of the pattern in creative terms.
        Look for unusual shapes, not standard trading patterns.
        """
        # Calculate features
        trend = pattern[-1] - pattern[0]
        volatility = np.std(np.diff(pattern))
        peaks = self._count_peaks(pattern)
        valleys = self._count_valleys(pattern)
        
        # Describe based on features
        if peaks >= 3 and valleys >= 3:
            return "zigzag_staircase"
        elif peaks == 1 and valleys == 0:
            return "mountain_peak"
        elif peaks == 0 and valleys == 1:
            return "valley_bottom"
        elif abs(trend) < 0.1 and volatility < 0.05:
            return "flat_plateau"
        elif trend > 0.3 and volatility < 0.1:
            return "ascending_slope"
        elif trend < -0.3 and volatility < 0.1:
            return "descending_slope"
        elif volatility > 0.2:
            return "chaotic_noise"
        elif peaks == 2:
            return "double_hump"
        elif valleys == 2:
            return "double_dip"
        else:
            return "unique_shape"
    
    def _count_peaks(self, data: np.ndarray, threshold: float = 0.1) -> int:
        """Count local maxima"""
        peaks = 0
        for i in range(1, len(data) - 1):
            if data[i] > data[i-1] + threshold and data[i] > data[i+1] + threshold:
                peaks += 1
        return peaks
    
    def _count_valleys(self, data: np.ndarray, threshold: float = 0.1) -> int:
        """Count local minima"""
        valleys = 0
        for i in range(1, len(data) - 1):
            if data[i] < data[i-1] - threshold and data[i] < data[i+1] - threshold:
                valleys += 1
        return valleys
    
    def _deduplicate_fractals(self, fractals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove overlapping fractals, keep highest similarity"""
        if not fractals:
            return []
        
        # Sort by similarity
        fractals = sorted(fractals, key=lambda x: x['similarity'], reverse=True)
        
        unique = []
        for f in fractals:
            overlap = False
            for u in unique:
                # Check if patterns overlap significantly
                if self._patterns_overlap(f, u):
                    overlap = True
                    break
            
            if not overlap:
                unique.append(f)
        
        return unique
    
    def _patterns_overlap(self, f1: Dict[str, Any], f2: Dict[str, Any]) -> bool:
        """Check if two fractal patterns overlap"""
        # Check small patterns
        s1_start = f1['small_pattern']['start_idx']
        s1_end = f1['small_pattern']['end_idx']
        s2_start = f2['small_pattern']['start_idx']
        s2_end = f2['small_pattern']['end_idx']
        
        small_overlap = not (s1_end <= s2_start or s2_end <= s1_start)
        
        # Check large patterns
        l1_start = f1['large_pattern']['start_idx']
        l1_end = f1['large_pattern']['end_idx']
        l2_start = f2['large_pattern']['start_idx']
        l2_end = f2['large_pattern']['end_idx']
        
        large_overlap = not (l1_end <= l2_start or l2_end <= l1_start)
        
        return small_overlap or large_overlap
    
    def _generate_signal(self, fractals: List[Dict[str, Any]], prices: List[float]) -> str:
        """
        Generate trading signal based on fractal patterns.
        
        Theory: If a pattern repeated at a larger scale previously,
        and now appearing at a smaller scale, the larger pattern's
        outcome might predict the smaller pattern's outcome.
        """
        if not fractals:
            return "neutral"
        
        # Get the strongest fractal
        best_fractal = max(fractals, key=lambda x: x['similarity'])
        
        # Compare timing: which came first?
        small_idx = best_fractal['small_pattern']['start_idx']
        large_idx = best_fractal['large_pattern']['start_idx']
        
        # If large pattern completed before small pattern started
        if large_idx < small_idx:
            # Check how the large pattern ended
            large_end_idx = best_fractal['large_pattern']['end_idx']
            if large_end_idx < len(prices):
                # Compare start vs end of large pattern
                large_start_price = prices[large_idx]
                large_end_price = prices[large_end_idx]
                
                if large_end_price > large_start_price * 1.02:
                    return "bullish_fractal"
                elif large_end_price < large_start_price * 0.98:
                    return "bearish_fractal"
        
        return "neutral"
