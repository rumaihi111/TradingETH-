"""
RSI Brain - Second Brain / Hive Mind for Trading Bot

Uses RSI(14) on 5-minute charts with sophisticated analysis:
- Expectation tracking (did price deliver?)
- Second reaction confirmation
- Speed/momentum changes
- Behavioral analysis
- Trapped trader detection

Works alongside Claude to filter and validate trades.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class MarketPhase(Enum):
    ACCUMULATION = "accumulation"  # Tight, sideways, overlapping
    EXPANSION = "expansion"        # Fast, directional, long candles
    DISTRIBUTION = "distribution"  # Stalling after expansion
    RETRACEMENT = "retracement"    # Controlled pullback


class Expectation(Enum):
    CONTINUATION = "continuation"
    BOUNCE = "bounce"
    FOLLOW_THROUGH = "follow_through"
    NEUTRAL = "neutral"


@dataclass
class RSIAnalysis:
    """Complete RSI brain analysis result"""
    rsi_value: float
    zone: str  # "long_zone", "short_zone", "no_mans_land"
    should_enter: bool
    should_exit: bool
    exit_reason: Optional[str]
    phase: MarketPhase
    expectation: Expectation
    expectation_met: bool
    momentum_signal: str  # "accelerating", "decelerating", "stable"
    trapped_side: Optional[str]  # "longs", "shorts", None
    confidence: float  # 0-1
    analysis_notes: List[str]


class RSIBrain:
    """
    Second brain that uses RSI and behavioral analysis.
    
    RSI Zones:
    - Long Zone: RSI < 30 (oversold - look for longs)
    - Short Zone: RSI > 70 (overbought - look for shorts)
    - No Man's Land: 30-70 (especially 40-60 is dead zone)
    
    Exit triggers:
    - If in a trade and RSI enters mid no-man's zone (45-55), exit
    """
    
    # RSI Zone thresholds
    OVERSOLD = 30          # Below = long zone
    OVERBOUGHT = 70        # Above = short zone
    DEAD_ZONE_LOW = 40     # Below this in no-mans is still actionable
    DEAD_ZONE_HIGH = 60    # Above this in no-mans is still actionable
    EXIT_ZONE_LOW = 45     # Mid no-mans zone lower bound
    EXIT_ZONE_HIGH = 55    # Mid no-mans zone upper bound
    
    def __init__(self, rsi_period: int = 14):
        self.rsi_period = rsi_period
        self.history: List[Dict] = []
        self.last_expectations: List[Tuple[Expectation, bool]] = []
        
    def calculate_rsi(self, candles: List[Dict]) -> float:
        """Calculate RSI(14) from candle data"""
        if len(candles) < self.rsi_period + 1:
            return 50.0  # Neutral if not enough data
            
        closes = [float(c.get('close', c.get('c', 0))) for c in candles]
        
        # Calculate price changes
        deltas = np.diff(closes)
        
        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Calculate average gains and losses (Wilder's smoothing)
        avg_gain = np.mean(gains[:self.rsi_period])
        avg_loss = np.mean(losses[:self.rsi_period])
        
        # Apply Wilder's smoothing for remaining periods
        for i in range(self.rsi_period, len(gains)):
            avg_gain = (avg_gain * (self.rsi_period - 1) + gains[i]) / self.rsi_period
            avg_loss = (avg_loss * (self.rsi_period - 1) + losses[i]) / self.rsi_period
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def get_rsi_zone(self, rsi: float) -> str:
        """Determine which RSI zone we're in"""
        if rsi <= self.OVERSOLD:
            return "long_zone"
        elif rsi >= self.OVERBOUGHT:
            return "short_zone"
        else:
            return "no_mans_land"
    
    def should_block_entry(self, rsi: float, side: str) -> Tuple[bool, str]:
        """
        Check if RSI says we should NOT enter this trade.
        
        Rules:
        - Don't long if RSI not in/near long zone (< 40)
        - Don't short if RSI not in/near short zone (> 60)
        - Block all entries in dead zone (40-60)
        """
        zone = self.get_rsi_zone(rsi)
        
        # Dead zone - block all entries
        if self.DEAD_ZONE_LOW <= rsi <= self.DEAD_ZONE_HIGH:
            return True, f"RSI {rsi:.1f} in dead zone ({self.DEAD_ZONE_LOW}-{self.DEAD_ZONE_HIGH})"
        
        # Check if RSI supports the trade direction
        if side.lower() == "long":
            if rsi > self.DEAD_ZONE_LOW:  # RSI > 40, not good for longs
                return True, f"RSI {rsi:.1f} too high for long entry (need < {self.DEAD_ZONE_LOW})"
        elif side.lower() == "short":
            if rsi < self.DEAD_ZONE_HIGH:  # RSI < 60, not good for shorts
                return True, f"RSI {rsi:.1f} too low for short entry (need > {self.DEAD_ZONE_HIGH})"
        
        return False, ""
    
    def should_exit_position(self, rsi: float, position_side: str) -> Tuple[bool, str]:
        """
        Check if RSI says we should EXIT current position.
        
        Exit if RSI hits middle of no-man's zone (45-55) during a trade.
        """
        # Mid no-mans zone exit trigger
        if self.EXIT_ZONE_LOW <= rsi <= self.EXIT_ZONE_HIGH:
            return True, f"RSI {rsi:.1f} hit mid no-mans zone ({self.EXIT_ZONE_LOW}-{self.EXIT_ZONE_HIGH})"
        
        # Also exit if RSI goes opposite extreme
        if position_side.lower() == "long" and rsi >= self.OVERBOUGHT:
            return True, f"RSI {rsi:.1f} reached overbought - take profit on long"
        elif position_side.lower() == "short" and rsi <= self.OVERSOLD:
            return True, f"RSI {rsi:.1f} reached oversold - take profit on short"
            
        return False, ""
    
    def detect_market_phase(self, candles: List[Dict]) -> MarketPhase:
        """
        Identify market phase: accumulation, expansion, distribution, retracement
        """
        if len(candles) < 20:
            return MarketPhase.ACCUMULATION
            
        recent = candles[-20:]
        
        # Calculate candle sizes
        sizes = []
        for c in recent:
            high = float(c.get('high', c.get('h', 0)))
            low = float(c.get('low', c.get('l', 0)))
            sizes.append(high - low)
        
        avg_size = np.mean(sizes)
        recent_avg = np.mean(sizes[-5:])
        
        # Calculate direction
        closes = [float(c.get('close', c.get('c', 0))) for c in recent]
        direction = closes[-1] - closes[0]
        
        # Calculate overlap (accumulation indicator)
        highs = [float(c.get('high', c.get('h', 0))) for c in recent[-10:]]
        lows = [float(c.get('low', c.get('l', 0))) for c in recent[-10:]]
        range_pct = (max(highs) - min(lows)) / min(lows) * 100
        
        # Classify phase
        if recent_avg > avg_size * 1.5 and abs(direction) > avg_size * 3:
            return MarketPhase.EXPANSION
        elif recent_avg < avg_size * 0.7 and range_pct < 2:
            return MarketPhase.ACCUMULATION
        elif recent_avg < avg_size * 0.8 and direction > 0:
            return MarketPhase.DISTRIBUTION
        else:
            return MarketPhase.RETRACEMENT
    
    def detect_expectation(self, candles: List[Dict]) -> Tuple[Expectation, bool]:
        """
        Watch expectations, not candles.
        
        Every candle creates an expectation:
        - After strong green → expectation = continuation
        - After a pullback → expectation = bounce
        - After a breakout → expectation = follow-through
        
        Then: Did price deliver on the expectation?
        """
        if len(candles) < 10:
            return Expectation.NEUTRAL, True
            
        recent = candles[-10:]
        
        # Analyze last few candles
        last_candle = recent[-1]
        prev_candles = recent[-5:-1]
        
        last_open = float(last_candle.get('open', last_candle.get('o', 0)))
        last_close = float(last_candle.get('close', last_candle.get('c', 0)))
        last_change = last_close - last_open
        
        # Calculate average candle size for context
        avg_size = np.mean([
            abs(float(c.get('close', c.get('c', 0))) - float(c.get('open', c.get('o', 0))))
            for c in prev_candles
        ])
        
        # Determine what expectation was set by previous candles
        prev_closes = [float(c.get('close', c.get('c', 0))) for c in prev_candles]
        prev_direction = prev_closes[-1] - prev_closes[0]
        
        # Strong green move → expect continuation
        if prev_direction > avg_size * 2:
            expectation = Expectation.CONTINUATION
            met = last_change > 0  # Did we continue up?
        # Strong red move → expect continuation down
        elif prev_direction < -avg_size * 2:
            expectation = Expectation.CONTINUATION
            met = last_change < 0  # Did we continue down?
        # Pullback after uptrend → expect bounce
        elif prev_direction < 0 and len(candles) > 15:
            earlier = [float(c.get('close', c.get('c', 0))) for c in candles[-15:-5]]
            if earlier[-1] > earlier[0]:  # Was trending up before
                expectation = Expectation.BOUNCE
                met = last_change > 0
            else:
                expectation = Expectation.NEUTRAL
                met = True
        else:
            expectation = Expectation.NEUTRAL
            met = True
            
        return expectation, met
    
    def analyze_speed_changes(self, candles: List[Dict]) -> str:
        """
        Track speed changes, not direction changes.
        
        Direction lies. Speed doesn't.
        - Is price accelerating or decelerating?
        - Are candles getting longer or shorter?
        """
        if len(candles) < 15:
            return "stable"
            
        # Calculate candle body sizes
        sizes = []
        for c in candles[-15:]:
            body = abs(float(c.get('close', c.get('c', 0))) - float(c.get('open', c.get('o', 0))))
            sizes.append(body)
        
        early_avg = np.mean(sizes[:5])
        mid_avg = np.mean(sizes[5:10])
        recent_avg = np.mean(sizes[10:])
        
        # Detect acceleration/deceleration
        if recent_avg > mid_avg > early_avg:
            return "accelerating"
        elif recent_avg < mid_avg < early_avg:
            return "decelerating"
        else:
            return "stable"
    
    def detect_trapped_traders(self, candles: List[Dict], rsi: float) -> Optional[str]:
        """
        Who is trapped? Every move creates losers.
        
        - Who bought late?
        - Who sold too early?
        - Trapped traders become fuel
        """
        if len(candles) < 20:
            return None
            
        closes = [float(c.get('close', c.get('c', 0))) for c in candles[-20:]]
        highs = [float(c.get('high', c.get('h', 0))) for c in candles[-20:]]
        lows = [float(c.get('low', c.get('l', 0))) for c in candles[-20:]]
        
        current_price = closes[-1]
        recent_high = max(highs[-10:])
        recent_low = min(lows[-10:])
        
        # Longs trapped if we're well below recent highs and RSI dropping
        if current_price < recent_high * 0.97 and rsi < 45:
            return "longs"
        
        # Shorts trapped if we're well above recent lows and RSI rising
        if current_price > recent_low * 1.03 and rsi > 55:
            return "shorts"
            
        return None
    
    def analyze_pullback_quality(self, candles: List[Dict]) -> str:
        """
        Pullbacks are honesty tests.
        
        - Shallow + slow pullback = strength
        - Deep + fast pullback = weakness
        """
        if len(candles) < 20:
            return "neutral"
            
        # Find the last impulse and pullback
        closes = [float(c.get('close', c.get('c', 0))) for c in candles[-20:]]
        
        # Calculate impulse (first 10 candles)
        impulse = closes[9] - closes[0]
        impulse_time = 10
        
        # Calculate pullback (last 10 candles relative to impulse high/low)
        if impulse > 0:  # Uptrend
            pullback_start = max(closes[5:15])
            pullback_depth = pullback_start - closes[-1]
        else:  # Downtrend
            pullback_start = min(closes[5:15])
            pullback_depth = closes[-1] - pullback_start
            
        # Compare depth
        if abs(impulse) > 0:
            depth_ratio = abs(pullback_depth) / abs(impulse)
        else:
            depth_ratio = 0
            
        if depth_ratio < 0.3:
            return "shallow_strong"
        elif depth_ratio > 0.6:
            return "deep_weak"
        else:
            return "neutral"
    
    def analyze_wicks(self, candles: List[Dict]) -> str:
        """
        Wicks tell intent. Clusters matter more than singles.
        
        - Repeated wicks = someone defending
        - No wicks = no opposition
        """
        if len(candles) < 10:
            return "neutral"
            
        upper_wicks = 0
        lower_wicks = 0
        
        for c in candles[-10:]:
            high = float(c.get('high', c.get('h', 0)))
            low = float(c.get('low', c.get('l', 0)))
            open_p = float(c.get('open', c.get('o', 0)))
            close = float(c.get('close', c.get('c', 0)))
            
            body_top = max(open_p, close)
            body_bottom = min(open_p, close)
            body_size = body_top - body_bottom
            
            upper_wick = high - body_top
            lower_wick = body_bottom - low
            
            # Count significant wicks (> 50% of body)
            if body_size > 0:
                if upper_wick > body_size * 0.5:
                    upper_wicks += 1
                if lower_wick > body_size * 0.5:
                    lower_wicks += 1
        
        if upper_wicks >= 5:
            return "sellers_defending"
        elif lower_wicks >= 5:
            return "buyers_defending"
        else:
            return "neutral"
    
    def calculate_confidence(self, analysis_factors: Dict) -> float:
        """Calculate overall confidence score 0-1"""
        score = 0.5  # Start neutral
        
        # RSI zone alignment
        if analysis_factors.get('zone_aligned', False):
            score += 0.2
        
        # Expectation met
        if analysis_factors.get('expectation_met', True):
            score += 0.1
        
        # Momentum aligned
        if analysis_factors.get('momentum_aligned', False):
            score += 0.1
        
        # Pullback quality
        if analysis_factors.get('pullback') == 'shallow_strong':
            score += 0.1
        elif analysis_factors.get('pullback') == 'deep_weak':
            score -= 0.1
        
        return min(max(score, 0), 1)
    
    def full_analysis(
        self, 
        candles: List[Dict], 
        current_position: Optional[str] = None,
        proposed_side: Optional[str] = None
    ) -> RSIAnalysis:
        """
        Complete RSI brain analysis.
        
        Args:
            candles: List of OHLCV candles
            current_position: Current position side ("long", "short", or None)
            proposed_side: Side Claude wants to trade ("long", "short", "flat")
        
        Returns:
            RSIAnalysis with complete assessment
        """
        notes = []
        
        # Calculate RSI
        rsi = self.calculate_rsi(candles)
        zone = self.get_rsi_zone(rsi)
        notes.append(f"RSI({self.rsi_period}): {rsi:.1f} [{zone}]")
        
        # Check entry blocking
        should_enter = True
        if proposed_side and proposed_side.lower() not in ["flat", "close"]:
            blocked, block_reason = self.should_block_entry(rsi, proposed_side)
            if blocked:
                should_enter = False
                notes.append(f"🚫 Entry blocked: {block_reason}")
            else:
                notes.append(f"✅ RSI supports {proposed_side} entry")
        
        # Check exit trigger
        should_exit = False
        exit_reason = None
        if current_position:
            should_exit, exit_reason = self.should_exit_position(rsi, current_position)
            if should_exit:
                notes.append(f"⚠️ Exit signal: {exit_reason}")
        
        # Market phase
        phase = self.detect_market_phase(candles)
        notes.append(f"Phase: {phase.value}")
        
        # Expectation analysis
        expectation, expectation_met = self.detect_expectation(candles)
        if not expectation_met:
            notes.append(f"⚠️ Expectation ({expectation.value}) NOT met - warning sign")
        else:
            notes.append(f"Expectation ({expectation.value}) delivered")
        
        # Speed/momentum
        momentum = self.analyze_speed_changes(candles)
        notes.append(f"Momentum: {momentum}")
        
        # Trapped traders
        trapped = self.detect_trapped_traders(candles, rsi)
        if trapped:
            notes.append(f"🎯 Trapped {trapped} detected - potential fuel")
        
        # Pullback quality
        pullback = self.analyze_pullback_quality(candles)
        notes.append(f"Pullback: {pullback}")
        
        # Wick analysis
        wicks = self.analyze_wicks(candles)
        if wicks != "neutral":
            notes.append(f"Wicks: {wicks}")
        
        # Calculate confidence
        zone_aligned = (
            (proposed_side == "long" and zone == "long_zone") or
            (proposed_side == "short" and zone == "short_zone")
        )
        momentum_aligned = (
            (proposed_side == "long" and momentum == "accelerating") or
            (proposed_side == "short" and momentum == "decelerating")
        )
        
        confidence = self.calculate_confidence({
            'zone_aligned': zone_aligned,
            'expectation_met': expectation_met,
            'momentum_aligned': momentum_aligned,
            'pullback': pullback
        })
        
        return RSIAnalysis(
            rsi_value=rsi,
            zone=zone,
            should_enter=should_enter,
            should_exit=should_exit,
            exit_reason=exit_reason,
            phase=phase,
            expectation=expectation,
            expectation_met=expectation_met,
            momentum_signal=momentum,
            trapped_side=trapped,
            confidence=confidence,
            analysis_notes=notes
        )
    
    def print_analysis(self, analysis: RSIAnalysis):
        """Pretty print the analysis"""
        print("\n" + "="*60)
        print("🧠 RSI BRAIN ANALYSIS")
        print("="*60)
        print(f"RSI: {analysis.rsi_value:.1f} | Zone: {analysis.zone}")
        print(f"Phase: {analysis.phase.value} | Momentum: {analysis.momentum_signal}")
        print(f"Confidence: {analysis.confidence*100:.0f}%")
        print("-"*60)
        for note in analysis.analysis_notes:
            print(f"  {note}")
        print("-"*60)
        if not analysis.should_enter:
            print("❌ ENTRY BLOCKED BY RSI BRAIN")
        if analysis.should_exit:
            print(f"⚠️ EXIT SIGNAL: {analysis.exit_reason}")
        print("="*60 + "\n")
