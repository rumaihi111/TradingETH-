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
    Pure RSI-based trading engine for DOGE.
    RSI is the ONLY indicator used for entries and exits.
    
    DOGE Strategy:
    - RSI < 29: BUY (oversold, enter LONG)
    - RSI > 69: SELL (overbought, enter SHORT)
    - RSI 29-69: NO MAN'S ZONE (no new entries allowed)
    - Exit at middle (~50) when in profit
    """
    
    # RSI Thresholds
    RSI_PERIOD = 7          # RSI calculation period
    
    # Entry zones for DOGE
    OVERBOUGHT_LOW = 69.0   # Enter SHORT when RSI > 69 (overbought)
    OVERBOUGHT_HIGH = 100.0 # Upper bound for SHORT entry
    OVERSOLD_LOW = 0.0      # Lower bound for LONG entry
    OVERSOLD_HIGH = 29.0    # Enter LONG when RSI < 29 (oversold)
    
    # Exit zone (sell at middle) - close positions for profit
    EXIT_ZONE_LOW = 45.0    # Exit zone lower bound
    EXIT_ZONE_HIGH = 55.0   # Exit zone upper bound
    EXIT_ZONE = 50.0        # Center of exit zone
    
    def __init__(self):
        self.last_rsi = None
        self.entry_rsi = None  # RSI when we entered the trade
    
    def calculate_rsi(self, candles: List[Dict[str, Any]], period: int = None) -> float:
        """Calculate RSI from candle data"""
        if period is None:
            period = self.RSI_PERIOD  # Default to class RSI period (7)
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
        """Determine which RSI zone we're in for DOGE trading"""
        if rsi > self.OVERBOUGHT_LOW:
            return "overbought"  # SHORT zone (RSI > 69)
        elif rsi < self.OVERSOLD_HIGH:
            return "oversold"    # LONG zone (RSI < 29)
        elif self.EXIT_ZONE_LOW <= rsi <= self.EXIT_ZONE_HIGH:
            return "exit"        # Exit zone (45-55, middle)
        else:
            return "noman"       # No-man zone (29-69, no entries allowed)
    
    def make_decision(
        self, 
        candles: List[Dict[str, Any]], 
        current_position: Optional[Dict[str, Any]] = None,
        unrealized_pnl: float = 0,
        timeframe: str = "5m"
    ) -> RSIDecision:
        """
        Make a trading decision based ONLY on RSI for DOGE.
        
        DOGE RSI Strategy:
        - RSI < 29: BUY (enter LONG - oversold)
        - RSI > 69: SELL (enter SHORT - overbought)
        - RSI 29-69: NO MAN'S ZONE - NO new entries allowed!
        - RSI 45-55: Exit zone - close positions at middle for profit
        
        Args:
            candles: OHLCV candle data
            current_position: Current position dict (size, entry, etc.)
            unrealized_pnl: Current unrealized P&L in dollars
            timeframe: Trading timeframe ('1m' or '5m')
            
        Returns:
            RSIDecision with action and reasoning
        """
        rsi = self.calculate_rsi(candles)  # Uses RSI_PERIOD (7)
        zone = self.get_zone(rsi)
        
        # Check if we're using 1-minute chart strategy (exit at extremes)
        is_1m_strategy = timeframe == "1m"
        
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
                    reason=f"🔴 RSI {rsi:.2f} > 69 (OVERBOUGHT) → SELL/SHORT DOGE",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.9
                )
            elif current_side == "long":
                # We're LONG and RSI hit overbought - flip to short
                return RSIDecision(
                    action="close_flip",
                    reason=f"🔴 RSI {rsi:.2f} > 69 → CLOSE LONG + OPEN SHORT (flip)",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.9
                )
            else:
                # Already short, hold
                return RSIDecision(
                    action="hold",
                    reason=f"RSI {rsi:.2f} > 69 - Already SHORT, holding",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.8
                )
        
        # 2. OVERSOLD ZONE - LONG signals (RSI < 29)
        elif zone == "oversold":
            if not has_position:
                return RSIDecision(
                    action="open_long",
                    reason=f"🟢 RSI {rsi:.2f} < 29 (OVERSOLD) → BUY/LONG DOGE",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.9
                )
            elif current_side == "short":
                # We're SHORT and RSI hit oversold - flip to long
                return RSIDecision(
                    action="close_flip",
                    reason=f"🟢 RSI {rsi:.2f} < 29 → CLOSE SHORT + OPEN LONG (flip)",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.9
                )
            else:
                # Already long, hold
                return RSIDecision(
                    action="hold",
                    reason=f"RSI {rsi:.2f} < 29 - Already LONG, holding",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.8
                )
        
        # 3. EXIT ZONE - Close positions at middle for profit
        elif zone == "exit":
            if has_position and unrealized_pnl > 0:
                return RSIDecision(
                    action="close_profit",
                    reason=f"🟡 RSI {rsi:.2f} in EXIT ZONE (45-55) + IN PROFIT (${unrealized_pnl:+.2f}) → CLOSE",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.85
                )
            elif has_position:
                # In exit zone but NOT in profit - HOLD, let it recover
                return RSIDecision(
                    action="hold",
                    reason=f"RSI {rsi:.2f} in EXIT ZONE but NOT in profit (${unrealized_pnl:+.2f}) → holding",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.7
                )
            else:
                # No position, can't enter - this is no man's zone territory
                return RSIDecision(
                    action="wait",
                    reason=f"⚪ RSI {rsi:.2f} in NO MAN'S ZONE (29-69) → NO ENTRY ALLOWED",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.5
                )
        
        # 4. NO-MAN ZONE - NO new entries allowed! Only manage existing positions
        else:  # zone == "noman"
            if has_position:
                return RSIDecision(
                    action="hold",
                    reason=f"⚪ RSI {rsi:.2f} in NO MAN'S ZONE (29-69) → holding position, waiting for exit zone",
                    rsi_value=rsi,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                    confidence=0.6
                )
            else:
                return RSIDecision(
                    action="wait",
                    reason=f"⚪ RSI {rsi:.2f} in NO MAN'S ZONE (29-69) → NO ENTRY ALLOWED",
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
            messages.append(f"🔴 SHORT ZONE ({self.OVERBOUGHT_LOW}-{self.OVERBOUGHT_HIGH})")
            if position_side == "short":
                messages.append("✅ Good - Aligned with SHORT")
            elif position_side == "long":
                messages.append("⚠️ Warning - Consider closing LONG")
            else:
                messages.append("💡 Signal: ENTER SHORT")
                
        elif zone == "oversold":
            messages.append(f"🟢 LONG ZONE ({self.OVERSOLD_LOW}-{self.OVERSOLD_HIGH})")
            if position_side == "long":
                messages.append("✅ Good - Aligned with LONG")
            elif position_side == "short":
                messages.append("⚠️ Warning - Consider closing SHORT")
            else:
                messages.append("💡 Signal: ENTER LONG")
                
        elif zone == "exit":
            messages.append(f"🟠 EXIT ZONE ({self.EXIT_ZONE_LOW}-{self.EXIT_ZONE_HIGH})")
            if pnl > 0:
                messages.append(f"💰 In profit ${pnl:+.2f} - Consider closing")
            else:
                messages.append("📉 Not in profit - Hold position")
                
        else:
            messages.append(f"⚪ NO-MAN ZONE (outside entry/exit zones)")
            messages.append("🚫 No new entries allowed")
        
        return "\n".join(messages)
