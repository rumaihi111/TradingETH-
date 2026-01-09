"""
Second Brain - Advanced Price Action Analysis Module
This module works as a hive mind with the main AI brain,
providing sophisticated technical analysis based on expectations,
reactions, speed changes, and market psychology.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import statistics


@dataclass
class MarketPhase:
    """Market phase classification"""
    phase: str  # 'accumulation', 'expansion', 'distribution', 'retracement'
    confidence: float  # 0-1
    description: str


@dataclass
class PriceExpectation:
    """Price expectation and whether it was delivered"""
    expectation: str  # 'continuation', 'bounce', 'follow-through', 'reversal'
    delivered: bool
    strength: float  # 0-1, how strongly it delivered or failed


@dataclass
class SecondBrainSignal:
    """Signal from second brain analysis"""
    bias: str  # 'long', 'short', 'neutral', 'aggressive_long', 'aggressive_short'
    confidence: float  # 0-1
    phase: MarketPhase
    stop_loss_distance_pct: float  # Recommended stop loss distance
    take_profit_distance_pct: float  # Recommended take profit distance
    reasoning: List[str]  # List of reasons for the signal


class SecondBrain:
    """
    Second Brain for advanced price action analysis.
    Works in parallel with the main AI to provide deeper market insight.
    """
    
    def __init__(self, rsi_overbought: float = 66.80, rsi_oversold: float = 35.28, rsi_neutral: float = 50.44):
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.rsi_neutral = rsi_neutral
        self.price_history: List[float] = []
        self.candle_history: List[Dict[str, Any]] = []
        
    def analyze(self, candles: List[Dict[str, Any]], rsi_value: float) -> SecondBrainSignal:
        """
        Perform comprehensive analysis and return a signal.
        
        Args:
            candles: List of OHLCV candle dictionaries
            rsi_value: Current RSI value
            
        Returns:
            SecondBrainSignal with bias, confidence, and reasoning
        """
        # Store candle history
        self.candle_history = candles[-50:] if len(candles) > 50 else candles
        self.price_history = [c['close'] for c in self.candle_history]
        
        # Initialize reasoning list
        reasoning = []
        confidence_factors = []
        
        # 1. Check RSI zones first (hard rules)
        rsi_bias, rsi_conf, rsi_reasoning = self._analyze_rsi_zones(rsi_value)
        reasoning.extend(rsi_reasoning)
        confidence_factors.append(rsi_conf)
        
        # 2. Identify market phase
        phase = self._identify_market_phase(candles)
        reasoning.append(f"Market Phase: {phase.phase} ({phase.description})")
        
        # 3. Check expectations vs delivery
        expectation = self._check_expectations(candles)
        if expectation:
            reasoning.append(f"Expectation: {expectation.expectation} - {'✓ Delivered' if expectation.delivered else '✗ Failed'}")
            confidence_factors.append(expectation.strength)
        
        # 4. Analyze second reactions (confirmation/exhaustion)
        second_reaction = self._analyze_second_reactions(candles)
        if second_reaction:
            reasoning.append(second_reaction)
            
        # 5. Track speed changes
        speed_signal = self._track_speed_changes(candles)
        if speed_signal:
            reasoning.append(f"Speed: {speed_signal}")
        
        # 6. Check if price "stops caring" (indifference)
        indifference = self._detect_indifference(candles)
        if indifference:
            reasoning.append(f"⚠️ Indifference detected: {indifference}")
            
        # 7. Identify hesitation vs clean passes
        hesitation = self._detect_hesitation(candles)
        if hesitation:
            reasoning.append(f"Hesitation: {hesitation}")
        
        # 8. Time-based pullbacks
        time_pullback = self._detect_time_pullback(candles)
        if time_pullback:
            reasoning.append(f"Time Pullback: {time_pullback}")
            
        # 9. Behavior change detection
        behavior_change = self._detect_behavior_change(candles)
        if behavior_change:
            reasoning.append(f"⚡ Behavior Change: {behavior_change}")
            confidence_factors.append(0.8)  # Strong signal
        
        # 10. Identify who is trapped
        trapped = self._identify_trapped_traders(candles)
        if trapped:
            reasoning.append(f"💰 Trapped: {trapped}")
            confidence_factors.append(0.7)
        
        # Determine final bias combining RSI and price action
        final_bias = self._determine_final_bias(rsi_bias, phase, expectation, candles)
        
        # Calculate stop loss and take profit based on brain analysis
        stop_distance, tp_distance = self._calculate_smart_stops(candles, phase, final_bias)
        
        # Average confidence from all factors
        avg_confidence = statistics.mean(confidence_factors) if confidence_factors else 0.5
        
        return SecondBrainSignal(
            bias=final_bias,
            confidence=avg_confidence,
            phase=phase,
            stop_loss_distance_pct=stop_distance,
            take_profit_distance_pct=tp_distance,
            reasoning=reasoning
        )
    
    def _analyze_rsi_zones(self, rsi: float) -> Tuple[str, float, List[str]]:
        """Analyze RSI and determine bias based on zones"""
        reasoning = []
        
        if rsi > self.rsi_overbought:
            reasoning.append(f"🔴 RSI {rsi:.2f} > {self.rsi_overbought} (OVERBOUGHT) → SHORT signal")
            return "short", 0.9, reasoning
        elif rsi < self.rsi_oversold:
            reasoning.append(f"🟢 RSI {rsi:.2f} < {self.rsi_oversold} (OVERSOLD) → LONG signal")
            return "long", 0.9, reasoning
        elif abs(rsi - self.rsi_neutral) < 2.0:
            reasoning.append(f"⚪ RSI {rsi:.2f} near {self.rsi_neutral} (EXIT ZONE) → Consider closing if in profit")
            return "neutral", 0.8, reasoning
        else:
            reasoning.append(f"⚠️ RSI {rsi:.2f} in NO-MAN zone ({self.rsi_oversold}-{self.rsi_overbought}) → NO NEW ENTRIES")
            return "neutral", 0.3, reasoning
    
    def _identify_market_phase(self, candles: List[Dict[str, Any]]) -> MarketPhase:
        """Classify market into accumulation, expansion, distribution, or retracement"""
        if len(candles) < 20:
            return MarketPhase("unknown", 0.3, "Insufficient data")
        
        recent = candles[-20:]
        
        # Calculate price range and volatility
        highs = [c['high'] for c in recent]
        lows = [c['low'] for c in recent]
        closes = [c['close'] for c in recent]
        
        price_range = max(highs) - min(lows)
        avg_price = statistics.mean(closes)
        range_pct = (price_range / avg_price) * 100
        
        # Calculate average candle size (measure of expansion)
        candle_sizes = [abs(c['close'] - c['open']) for c in recent]
        avg_candle_size = statistics.mean(candle_sizes)
        recent_candle_size = statistics.mean(candle_sizes[-5:])
        
        # Tight range, overlapping = Accumulation
        if range_pct < 1.5 and recent_candle_size < avg_candle_size * 0.8:
            return MarketPhase("accumulation", 0.8, "Tight, sideways, overlapping - energy building")
        
        # Large candles, directional = Expansion
        if recent_candle_size > avg_candle_size * 1.3:
            trend = "up" if closes[-1] > closes[0] else "down"
            return MarketPhase("expansion", 0.85, f"Fast, directional {trend} - strong momentum")
        
        # Slowing after expansion = Distribution
        if avg_candle_size > avg_price * 0.01 and recent_candle_size < avg_candle_size * 0.7:
            return MarketPhase("distribution", 0.75, "Stalling after expansion - momentum fading")
        
        # Controlled pullback
        return MarketPhase("retracement", 0.6, "Controlled pullback - testing support")
    
    def _check_expectations(self, candles: List[Dict[str, Any]]) -> Optional[PriceExpectation]:
        """Check if price delivered on the expectation set by previous candles"""
        if len(candles) < 5:
            return None
        
        recent = candles[-5:]
        
        # After strong green candle, expect continuation
        if recent[-2]['close'] > recent[-2]['open'] and \
           (recent[-2]['close'] - recent[-2]['open']) > (recent[-2]['high'] - recent[-2]['low']) * 0.7:
            # Did next candle continue up?
            delivered = recent[-1]['close'] > recent[-2]['close']
            strength = 0.8 if delivered else 0.7
            return PriceExpectation("continuation", delivered, strength)
        
        # After pullback, expect bounce
        if recent[-3]['close'] > recent[-2]['close'] and recent[-1]['close'] > recent[-2]['close']:
            # Price pulled back then bounced
            delivered = recent[-1]['close'] > recent[-2]['high']
            strength = 0.85 if delivered else 0.6
            return PriceExpectation("bounce", delivered, strength)
        
        return None
    
    def _analyze_second_reactions(self, candles: List[Dict[str, Any]]) -> Optional[str]:
        """Analyze second reactions to levels - confirmation or exhaustion"""
        if len(candles) < 10:
            return None
        
        recent = candles[-10:]
        
        # Find levels tested multiple times
        lows = [c['low'] for c in recent]
        highs = [c['high'] for c in recent]
        
        # Look for double bottom (two tests of low)
        if len(lows) >= 5:
            min_low = min(lows[-5:])
            tests = sum(1 for low in lows[-5:] if abs(low - min_low) / min_low < 0.002)
            if tests >= 2:
                # Check if second test was bought faster
                return "Second dip tested - buyers defending (bullish)"
        
        # Look for double top (two tests of high)
        if len(highs) >= 5:
            max_high = max(highs[-5:])
            tests = sum(1 for high in highs[-5:] if abs(high - max_high) / max_high < 0.002)
            if tests >= 2:
                return "Second top rejected - sellers defending (bearish)"
        
        return None
    
    def _track_speed_changes(self, candles: List[Dict[str, Any]]) -> Optional[str]:
        """Track acceleration/deceleration - speed doesn't lie"""
        if len(candles) < 15:
            return None
        
        # Compare recent speed vs earlier speed
        earlier_moves = [abs(candles[i]['close'] - candles[i-1]['close']) for i in range(-15, -8)]
        recent_moves = [abs(candles[i]['close'] - candles[i-1]['close']) for i in range(-7, -1)]
        
        avg_earlier = statistics.mean(earlier_moves)
        avg_recent = statistics.mean(recent_moves)
        
        if avg_recent > avg_earlier * 1.3:
            return "Accelerating - momentum building"
        elif avg_recent < avg_earlier * 0.7:
            return "Decelerating - momentum fading (warning)"
        
        return None
    
    def _detect_indifference(self, candles: List[Dict[str, Any]]) -> Optional[str]:
        """Detect when price stops caring - big moves get absorbed"""
        if len(candles) < 8:
            return None
        
        recent = candles[-8:]
        
        # Check for large wicks that don't follow through
        for i in range(1, len(recent)):
            wick_up = recent[i]['high'] - max(recent[i]['open'], recent[i]['close'])
            wick_down = min(recent[i]['open'], recent[i]['close']) - recent[i]['low']
            body = abs(recent[i]['close'] - recent[i]['open'])
            
            # Large upper wick not followed by continuation down
            if wick_up > body * 2 and i < len(recent) - 1:
                if recent[i+1]['close'] >= recent[i]['close']:
                    return "Upper wicks absorbed - sellers exhausted"
            
            # Large lower wick not followed by continuation up
            if wick_down > body * 2 and i < len(recent) - 1:
                if recent[i+1]['close'] <= recent[i]['close']:
                    return "Lower wicks absorbed - buyers exhausted"
        
        return None
    
    def _detect_hesitation(self, candles: List[Dict[str, Any]]) -> Optional[str]:
        """Detect where price hesitates vs clean passes"""
        if len(candles) < 5:
            return None
        
        recent = candles[-5:]
        
        # Count overlapping candles (hesitation)
        overlaps = 0
        for i in range(1, len(recent)):
            prev_range = (recent[i-1]['low'], recent[i-1]['high'])
            curr_range = (recent[i]['low'], recent[i]['high'])
            
            # Check if ranges overlap significantly
            overlap_low = max(prev_range[0], curr_range[0])
            overlap_high = min(prev_range[1], curr_range[1])
            
            if overlap_high > overlap_low:
                overlaps += 1
        
        if overlaps >= 3:
            return "Heavy overlapping - indecision/hesitation"
        elif overlaps == 0:
            return "Clean price action - strong imbalance"
        
        return None
    
    def _detect_time_pullback(self, candles: List[Dict[str, Any]]) -> Optional[str]:
        """Detect when market pulls back in time rather than price"""
        if len(candles) < 10:
            return None
        
        recent = candles[-10:]
        
        # Calculate price range over time
        price_range = max(c['high'] for c in recent) - min(c['low'] for c in recent)
        avg_price = statistics.mean(c['close'] for c in recent)
        range_pct = (price_range / avg_price) * 100
        
        # Narrow range over many candles = time pullback
        if range_pct < 0.8 and len(recent) >= 8:
            return "Time pullback - sideways grind, indicators resetting"
        
        return None
    
    def _detect_behavior_change(self, candles: List[Dict[str, Any]]) -> Optional[str]:
        """Detect regime change through behavior shifts"""
        if len(candles) < 20:
            return None
        
        # Compare first half vs second half behavior
        mid_point = len(candles) // 2
        first_half = candles[:mid_point]
        second_half = candles[mid_point:]
        
        # Calculate average pullback depth
        def avg_pullback_depth(chunk):
            pullbacks = []
            for i in range(1, len(chunk)):
                if chunk[i]['low'] < chunk[i-1]['close']:
                    depth = abs(chunk[i]['low'] - chunk[i-1]['close']) / chunk[i-1]['close']
                    pullbacks.append(depth)
            return statistics.mean(pullbacks) if pullbacks else 0
        
        first_pullback = avg_pullback_depth(first_half)
        second_pullback = avg_pullback_depth(second_half)
        
        if second_pullback < first_pullback * 0.6:
            return "Pullbacks getting shallower - strengthening trend"
        elif second_pullback > first_pullback * 1.5:
            return "Pullbacks getting deeper - weakening trend"
        
        return None
    
    def _identify_trapped_traders(self, candles: List[Dict[str, Any]]) -> Optional[str]:
        """Identify who is trapped and likely to provide fuel"""
        if len(candles) < 8:
            return None
        
        recent = candles[-8:]
        current_price = recent[-1]['close']
        
        # Find recent highs/lows
        recent_high = max(c['high'] for c in recent[-5:])
        recent_low = min(c['low'] for c in recent[-5:])
        
        # Trapped shorts (price broke above resistance and holding)
        if current_price > recent_high * 0.998:
            return "Late shorts likely trapped above - fuel for continuation up"
        
        # Trapped longs (price broke below support and holding)
        if current_price < recent_low * 1.002:
            return "Late longs likely trapped below - fuel for continuation down"
        
        return None
    
    def _determine_final_bias(self, rsi_bias: str, phase: MarketPhase, 
                              expectation: Optional[PriceExpectation], 
                              candles: List[Dict[str, Any]]) -> str:
        """Combine all signals to determine final bias"""
        
        # RSI rules are strict
        if rsi_bias == "short" or rsi_bias == "long":
            # Check if phase supports the bias
            if phase.phase == "expansion":
                return f"aggressive_{rsi_bias}"  # Strong confluence
            return rsi_bias
        
        # In neutral RSI zone, look at other factors
        if expectation and not expectation.delivered and phase.phase == "distribution":
            # Failed expectation + distribution = potential reversal
            if expectation.expectation == "continuation":
                return "short"  # Failed to continue up
        
        # Default to neutral in no-man zone
        return "neutral"
    
    def _calculate_smart_stops(self, candles: List[Dict[str, Any]], 
                                phase: MarketPhase, bias: str) -> Tuple[float, float]:
        """Calculate intelligent stop loss and take profit based on market structure"""
        
        if len(candles) < 10:
            return 0.05, 0.10  # Default 5% stop, 10% target
        
        recent = candles[-10:]
        
        # Calculate ATR-like volatility measure
        ranges = [c['high'] - c['low'] for c in recent]
        avg_range = statistics.mean(ranges)
        current_price = recent[-1]['close']
        atr_pct = (avg_range / current_price) * 100
        
        # Base stops on volatility and phase
        if phase.phase == "expansion":
            # Tight stops in strong trends, far targets
            stop_distance = max(0.03, atr_pct * 0.8)  # 3% minimum or 80% of ATR
            tp_distance = stop_distance * 3.0  # 3:1 R:R
        elif phase.phase == "accumulation":
            # Wider stops in ranging markets, closer targets
            stop_distance = max(0.05, atr_pct * 1.2)
            tp_distance = stop_distance * 2.0  # 2:1 R:R
        elif phase.phase == "distribution":
            # Medium stops, quick targets
            stop_distance = max(0.04, atr_pct)
            tp_distance = stop_distance * 2.5  # 2.5:1 R:R
        else:  # retracement
            stop_distance = max(0.04, atr_pct)
            tp_distance = stop_distance * 2.0
        
        # Find structural levels for more intelligent placement
        highs = [c['high'] for c in recent]
        lows = [c['low'] for c in recent]
        
        if bias == "long" or bias == "aggressive_long":
            # Stop below recent low
            recent_low = min(lows[-5:])
            structure_stop = ((current_price - recent_low) / current_price) * 100
            stop_distance = max(stop_distance, structure_stop + 0.005)  # Buffer
            
            # Target at recent high or extension
            recent_high = max(highs[-5:])
            structure_target = ((recent_high - current_price) / current_price) * 100
            tp_distance = max(tp_distance, structure_target)
            
        elif bias == "short" or bias == "aggressive_short":
            # Stop above recent high
            recent_high = max(highs[-5:])
            structure_stop = ((recent_high - current_price) / current_price) * 100
            stop_distance = max(stop_distance, structure_stop + 0.005)
            
            # Target at recent low or extension
            recent_low = min(lows[-5:])
            structure_target = ((current_price - recent_low) / current_price) * 100
            tp_distance = max(tp_distance, structure_target)
        
        # Cap at reasonable levels for 30-60 min targets
        stop_distance = min(stop_distance, 0.08)  # Max 8% stop
        tp_distance = min(tp_distance, 0.15)  # Max 15% target
        tp_distance = max(tp_distance, 0.05)  # Min 5% target
        
        return round(stop_distance / 100, 4), round(tp_distance / 100, 4)
