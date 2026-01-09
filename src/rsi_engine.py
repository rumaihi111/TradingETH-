"""
RSI Trading Engine - Pure RSI-based trading decisions
This module handles all RSI-based trading logic independently of AI
"""

from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class RSIDecision:
    """RSI-based trading decision"""
    action: str  # 'open_long', 'open_short', 'close_profit', 'close_flip', 'hold', 'wait'
    reason: str
    rsi_value: float
    stop_loss_pct: float
    take_profit_pct: float
    confidence: float


class RSITradingEngine:
    """
    Pure RSI-based trading engine.
    RSI is the ONLY indicator used for entries and exits.
    """
    
    # RSI Thresholds
    OVERBOUGHT = 66.80      # Enter SHORT when RSI goes above this
    OVERSOLD = 35.28        # Enter LONG when RSI goes below this
    EXIT_ZONE = 50.44       # Close position if in profit and RSI near this
    EXIT_ZONE_RANGE = 3.0   # +/- range around EXIT_ZONE
    
    def __init__(self):
        self.last_rsi = None
        self.entry_rsi = None  # RSI when we entered the trade
    
    def calculate_rsi(self, candles: List[Dict[str, Any]], period: int = 14) -> float:
        """Calculate RSI from candle data"""
        if len(candles) < period + 1:
            return 50.0  # Neutral if not enough data
        
        closes = [float(c['close']) for c in candles]
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def get_zone(self, rsi: float) -> str:
        """Determine which RSI zone we're in"""
        if rsi > self.OVERBOUGHT:
            return "overbought"  # SHORT zone
        elif rsi < self.OVERSOLD:
            return "oversold"    # LONG zone
        elif abs(rsi - self.EXIT_ZONE) <= self.EXIT_ZONE_RANGE:
            return "exit"        # Exit zone (close if in profit)
        else:
            return "noman"       # No-man zone (no action)
    
    def make_decision(
        self, 
        candles: List[Dict[str, Any]], 
        current_position: Optional[Dict[str, Any]] = None,
        unrealized_pnl: float = 0
    ) -> RSIDecision:
        """
        Make a trading decision based ONLY on RSI.
        
        Rules:
        - RSI > 66.80: Enter SHORT (if no position or in LONG)
        - RSI < 35.28: Enter LONG (if no position or in SHORT)
        - RSI near 50.44: Close if IN PROFIT only
        - No-Man Zone (35.28-66.80): NO new entries, only manage existing
        
        Args:
            candles: OHLCV candle data
            current_position: Current position dict (size, entry, etc.)
            unrealized_pnl: Current unrealized P&L in dollars
            
        Returns:
            RSIDecision with action and reasoning
        """
        rsi = self.calculate_rsi(candles, period=14)
        zone = self.get_zone(rsi)
        
        # Determine current position state
        has_position = current_position is not None and abs(current_position.get('size', 0)) > 0.0001
        current_side = None
        if has_position:
            size = current_position.get('size', 0)
            current_side = "long" if size > 0 else "short"
        
        # Default stop/take profit
        stop_loss = 0.05  # 5%
        take_profit = 0.10  # 10%
        
        # ========== DECISION LOGIC ==========
        
        # 1. OVERBOUGHT ZONE - SHORT signals
        if zone == "overbought":
            if not has_position:
                return RSIDecision(
                    action="open_short",
                    reason=f"RSI {rsi:.2f} > {self.OVERBOUGHT} (OVERBOUGHT) → ENTER SHORT",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.9
                )
            elif current_side == "long":
                # We're long but RSI says short - FLIP position
                return RSIDecision(
                    action="close_flip",
                    reason=f"RSI {rsi:.2f} OVERBOUGHT while LONG → CLOSE LONG and ENTER SHORT",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.85
                )
            else:
                # Already short, hold
                return RSIDecision(
                    action="hold",
                    reason=f"RSI {rsi:.2f} OVERBOUGHT - Already SHORT, holding position",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.8
                )
        
        # 2. OVERSOLD ZONE - LONG signals
        elif zone == "oversold":
            if not has_position:
                return RSIDecision(
                    action="open_long",
                    reason=f"RSI {rsi:.2f} < {self.OVERSOLD} (OVERSOLD) → ENTER LONG",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.9
                )
            elif current_side == "short":
                # We're short but RSI says long - FLIP position
                return RSIDecision(
                    action="close_flip",
                    reason=f"RSI {rsi:.2f} OVERSOLD while SHORT → CLOSE SHORT and ENTER LONG",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.85
                )
            else:
                # Already long, hold
                return RSIDecision(
                    action="hold",
                    reason=f"RSI {rsi:.2f} OVERSOLD - Already LONG, holding position",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.8
                )
        
        # 3. EXIT ZONE - Close ONLY if in profit
        elif zone == "exit":
            if has_position and unrealized_pnl > 0:
                return RSIDecision(
                    action="close_profit",
                    reason=f"RSI {rsi:.2f} near {self.EXIT_ZONE} (EXIT ZONE) + IN PROFIT (${unrealized_pnl:+.2f}) → CLOSE POSITION",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.85
                )
            elif has_position:
                # In exit zone but NOT in profit - HOLD, let it run
                return RSIDecision(
                    action="hold",
                    reason=f"RSI {rsi:.2f} in EXIT ZONE but NOT in profit (${unrealized_pnl:+.2f}) → HOLDING (let it recover)",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.7
                )
            else:
                # No position, just wait
                return RSIDecision(
                    action="wait",
                    reason=f"RSI {rsi:.2f} in EXIT ZONE - No position, waiting for extreme",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.5
                )
        
        # 4. NO-MAN ZONE - NO new entries, only hold or let stops/TPs work
        else:  # zone == "noman"
            if has_position:
                return RSIDecision(
                    action="hold",
                    reason=f"RSI {rsi:.2f} in NO-MAN ZONE ({self.OVERSOLD}-{self.OVERBOUGHT}) → HOLDING position (let SL/TP work)",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.6
                )
            else:
                return RSIDecision(
                    action="wait",
                    reason=f"RSI {rsi:.2f} in NO-MAN ZONE → NO ENTRY ALLOWED, waiting for extreme",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.5
                )
    
    def should_override_ai(self, ai_decision: str, rsi_decision: RSIDecision) -> Tuple[bool, str]:
        """
        Check if RSI should override AI's decision.
        RSI has final say on all trades.
        
        Returns:
            (should_override, reason)
        """
        # AI wants to close (flat) but RSI doesn't agree
        if ai_decision == "flat" and rsi_decision.action in ["hold", "wait"]:
            return True, f"RSI says HOLD: {rsi_decision.reason}"
        
        # AI wants to enter but RSI is in no-man zone
        if ai_decision in ["long", "short"] and rsi_decision.action == "wait":
            return True, f"RSI blocks entry: {rsi_decision.reason}"
        
        # RSI and AI agree
        return False, "AI and RSI aligned"
    
    def get_rsi_status_message(self, rsi: float, position_side: Optional[str] = None, pnl: float = 0) -> str:
        """Generate a human-readable RSI status message"""
        zone = self.get_zone(rsi)
        
        messages = []
        messages.append(f"📊 RSI: {rsi:.2f}")
        
        if zone == "overbought":
            messages.append(f"🔴 OVERBOUGHT (>{self.OVERBOUGHT})")
            if position_side == "short":
                messages.append("✅ Good - Aligned with SHORT")
            elif position_side == "long":
                messages.append("⚠️ Warning - Consider closing LONG")
            else:
                messages.append("💡 Signal: ENTER SHORT")
                
        elif zone == "oversold":
            messages.append(f"🟢 OVERSOLD (<{self.OVERSOLD})")
            if position_side == "long":
                messages.append("✅ Good - Aligned with LONG")
            elif position_side == "short":
                messages.append("⚠️ Warning - Consider closing SHORT")
            else:
                messages.append("💡 Signal: ENTER LONG")
                
        elif zone == "exit":
            messages.append(f"🟠 EXIT ZONE (near {self.EXIT_ZONE})")
            if pnl > 0:
                messages.append(f"💰 In profit ${pnl:+.2f} - Consider closing")
            else:
                messages.append("📉 Not in profit - Hold position")
                
        else:
            messages.append(f"⚪ NO-MAN ZONE ({self.OVERSOLD}-{self.OVERBOUGHT})")
            messages.append("🚫 No new entries allowed")
        
        return "\n".join(messages)
