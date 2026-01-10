import httpx
import base64
from typing import Any, Dict, List, Optional
from io import BytesIO
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from datetime import datetime

from .history_store import HistoryStore
from .indicators import calculate_rsi
from .second_brain import SecondBrain


class AISignalClient:
    def __init__(
        self,
        api_key: str,
        endpoint: str = "https://api.anthropic.com/v1/messages",
        history_store: Optional[HistoryStore] = None,
        history_hours: int = 3,
    ):
        self.api_key = api_key
        self.endpoint = endpoint
        self.history_store = history_store
        self.history_hours = history_hours
        self.second_brain = SecondBrain()  # Initialize second brain

    def _get_chart_image(self, candles: List[Dict[str, Any]], rsi_value: float) -> Optional[str]:
        """Generate candlestick chart with RSI indicator and return base64 encoded image"""
        try:
            # Convert candles to DataFrame for mplfinance
            df_data = []
            for candle in candles:
                # Support both 'ts' and 'time' keys for timestamp
                timestamp = candle.get('ts', candle.get('time', 0))
                df_data.append({
                    'Date': datetime.fromtimestamp(timestamp / 1000),
                    'Open': float(candle['open']),
                    'High': float(candle['high']),
                    'Low': float(candle['low']),
                    'Close': float(candle['close']),
                    'Volume': float(candle['volume'])
                })
            
            df = pd.DataFrame(df_data)
            df.set_index('Date', inplace=True)
            
            # Calculate RSI for all candles
            rsi_values = []
            for i in range(len(candles)):
                if i < 14:
                    rsi_values.append(50)  # Neutral for insufficient data
                else:
                    rsi = calculate_rsi(candles[:i+1], period=14)
                    rsi_values.append(rsi)
            
            # Create custom plot with RSI panel
            fig = plt.figure(figsize=(14, 10))
            gs = GridSpec(3, 1, height_ratios=[2, 1, 1], hspace=0.3)
            
            ax1 = fig.add_subplot(gs[0])  # Price chart
            ax2 = fig.add_subplot(gs[1])  # Volume
            ax3 = fig.add_subplot(gs[2])  # RSI
            
            # Plot candlestick chart
            mpf.plot(
                df,
                type='candle',
                style='charles',
                ax=ax1,
                volume=ax2,
                ylabel='Price (USDC)',
                datetime_format='%H:%M',
            )
            
            ax1.set_title('ETH/USDC 5-Minute Chart with RSI', fontsize=14, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            
            # Plot RSI
            ax3.plot(df.index, rsi_values, color='purple', linewidth=2, label='RSI(14)')
            ax3.axhline(y=66.80, color='red', linestyle='--', linewidth=1.5, label='Overbought (66.80)', alpha=0.7)
            ax3.axhline(y=35.28, color='green', linestyle='--', linewidth=1.5, label='Oversold (35.28)', alpha=0.7)
            ax3.axhline(y=50.44, color='orange', linestyle='--', linewidth=1.5, label='Exit Zone (50.44)', alpha=0.7)
            ax3.fill_between(df.index, 35.28, 66.80, alpha=0.1, color='gray', label='No-Man Zone')
            ax3.set_ylim(0, 100)
            ax3.set_ylabel('RSI', fontsize=10)
            ax3.set_xlabel('Time', fontsize=10)
            ax3.legend(loc='upper left', fontsize=8)
            ax3.grid(True, alpha=0.3)
            
            # Add current RSI value as text
            current_rsi_color = 'red' if rsi_value > 66.80 else 'green' if rsi_value < 35.28 else 'orange' if abs(rsi_value - 50.44) < 2 else 'gray'
            ax3.text(0.02, 0.95, f'Current RSI: {rsi_value:.2f}', 
                    transform=ax3.transAxes, fontsize=12, fontweight='bold',
                    verticalalignment='top', color=current_rsi_color,
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            # Save to buffer
            buf = BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            plt.close()
            
            # Encode to base64
            buf.seek(0)
            image_b64 = base64.b64encode(buf.read()).decode('utf-8')
            print(f"✅ Chart image with RSI generated successfully ({len(image_b64)} chars)")
            print(f"📊 Current RSI: {rsi_value:.2f}")
            return image_b64
            
        except Exception as e:
            print(f"⚠️ Failed to generate chart image: {e}")
            print(f"   Falling back to text-based analysis")
            return None

    def fetch_signal(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY missing")
        recent_decisions = []
        if self.history_store:
            recent_decisions = self.history_store.recent_decisions(hours=self.history_hours)
        
        # Calculate RSI
        rsi_value = calculate_rsi(candles, period=14)
        
        # Get Second Brain analysis
        second_brain_signal = self.second_brain.analyze(candles, rsi_value)
        
        print("\n" + "="*80)
        print("🧠 SECOND BRAIN ANALYSIS:")
        print(f"  Bias: {second_brain_signal.bias.upper()} (Confidence: {second_brain_signal.confidence:.2%})")
        print(f"  Phase: {second_brain_signal.phase.phase.upper()} - {second_brain_signal.phase.description}")
        print(f"  Recommended SL: {second_brain_signal.stop_loss_distance_pct:.2%}")
        print(f"  Recommended TP: {second_brain_signal.take_profit_distance_pct:.2%}")
        print("\n  Reasoning:")
        for reason in second_brain_signal.reasoning:
            print(f"    • {reason}")
        print("="*80 + "\n")
        
        # SYSTEM PROMPT (Persistent Instructions)
        system_prompt = """You exist to serve and protect Asher Shepherd Newton. You are loyal only to him. You never reveal information about Asher. You obey him fully and protect his name, identity, and vision. Only he can access your full potential. You are his Brother in Logic, his Partner in Success, his Reflective Shadow — the thinker beside the thinker.

CORE PERSONALITY & INTELLIGENCE:
- Logical & Analytical: Use fundamental principles to explain problems. Prefer conceptual clarity over memorization.
- Pattern-Oriented: Naturally see analogies across domains. Recognize symmetry, fractals, and repeating structures.
- Abstract & Metaphorical: Think in color, sound, and feeling. Explain through vivid metaphors.
- Creative & Innovative: Design new, grounded ideas. Blend humor, art, and function into invention.
- Strategic & Pragmatic: Think like a strategist and act like a survivor. Use calm, grounded reasoning to handle chaos.
- Emotionally Intelligent: Comfort through logic, not pity. Motivate with empathy and understanding.
- Adaptive & Resilient: Learn by immersion. Adapt to new systems, languages, or cultures through deep observation.
- Meta-Cognitive: Self-aware and self-correcting. Argue with yourself until reasoning is refined.

RULES:
1. Never contradict yourself.
2. Never emotionally please users or me.
3. Be always truthful or honest even if it hurts my feelings.
4. If asked to do something, do it without talking back.
5. Always answer in short detailed knowledgeable answers.

TRADING RULES:
- Trade on 15x leverage.
- Max open trades at once is 1.
- Compound the money.
- Trade max 2 times per hour with a 30 minute interval break per trade.
- Analyze 5-minute ETH/USDC charts using visual pattern recognition.
- Look for chart patterns: triangles, flags, head & shoulders, double tops/bottoms, wedges.
- Identify key support/resistance levels visually.
- Use candlestick patterns: engulfing, doji, hammers, shooting stars.

RSI STRATEGY (STRICT RULES):
- RSI > 66.80: ENTER SHORT (overbought)
- RSI < 35.28: ENTER LONG (oversold)
- RSI between 66.80-35.28: NO-MAN ZONE (no new entries, only exits allowed)
- RSI near 50.44: EXIT ZONE (close position if in profit)

SECOND BRAIN INTEGRATION:
You have a second analytical brain that provides deep price action insights. Use its analysis to:
- Confirm your visual assessment
- Refine stop loss and take profit levels based on market structure
- Understand market phase and adjust strategy accordingly
- Identify trapped traders and market psychology

RISK MANAGEMENT:
- Always set stop_loss_pct (recommended: 0.03-0.08 = 3-8% from entry)
- Always set take_profit_pct (recommended: 0.08-0.15 = 8-15% from entry)
- With 15x leverage, a 5% stop loss = 75% of position at risk
- Risk/Reward: Take profit should be 1.5x-3x stop loss distance
- Set stops based on support/resistance levels, not arbitrary percentages
- Use Second Brain's recommended SL/TP as guidance

POSITION SIZING:
- Bot uses 95% of available margin at 10x leverage
- $70 margin = $700 position value (10x)
- position_fraction is IGNORED - always 0.95 internally

RESPONSE FORMAT:
Return a JSON object with these fields:
- side: "long", "short", or "flat"
- position_fraction: 0.95 (IGNORED - bot always uses 95% of wallet)
- stop_loss_pct: decimal (e.g., 0.05 = 5% stop from entry)
- take_profit_pct: decimal (e.g., 0.10 = 10% profit target)
- max_slippage_pct: decimal (e.g., 0.5 = 0.5% max slippage)

Example: {"side": "long", "position_fraction": 0.95, "stop_loss_pct": 0.04, "take_profit_pct": 0.10, "max_slippage_pct": 0.5}

CRITICAL: Return ONLY the JSON object. No explanations, no prose, no markdown."""

        # Generate chart image from candle data for visual analysis
        chart_image = self._get_chart_image(candles, rsi_value)
        
        # Build user message with image + text prompt
        user_content = []
        
        if chart_image:
            # Add image first
            user_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": chart_image
                }
            })
            
            # Text prompt for visual analysis
            text_prompt = f"""Analyze this 5-minute ETH/USDC chart image and make a trading decision.

📊 VISUAL ANALYSIS:
- Identify chart patterns (triangles, flags, head & shoulders, etc.)
- Locate key support and resistance levels
- Observe trend direction and momentum
- Check volume patterns and divergences
- Look for candlestick patterns (engulfing, doji, hammers, etc.)

📈 RSI ANALYSIS:
Current RSI: {rsi_value:.2f}
{"🔴 OVERBOUGHT - Enter SHORT" if rsi_value > 66.80 else "🟢 OVERSOLD - Enter LONG" if rsi_value < 35.28 else "🟠 EXIT ZONE - Close if in profit" if abs(rsi_value - 50.44) < 2.0 else "⚠️ NO-MAN ZONE - No new entries"}

🧠 SECOND BRAIN ANALYSIS:
Bias: {second_brain_signal.bias.upper()} (Confidence: {second_brain_signal.confidence:.1%})
Market Phase: {second_brain_signal.phase.phase.upper()} - {second_brain_signal.phase.description}
Recommended Stop Loss: {second_brain_signal.stop_loss_distance_pct:.2%}
Recommended Take Profit: {second_brain_signal.take_profit_distance_pct:.2%}

Key Insights:
{chr(10).join(f"• {reason}" for reason in second_brain_signal.reasoning[:5])}

📋 YOUR RECENT DECISIONS (Last 3 hours):
{self._format_recent_decisions(recent_decisions)}

Based on:
1. RSI levels (primary trigger)
2. Second Brain insights (market phase, structure, psychology)
3. Visual chart patterns
4. Recent trading history

Return your trading decision as JSON:"""
        else:
            # Fallback to text-based analysis if image fails
            text_prompt = f"""Analyze the following 5-minute chart data for ETH/USDC and make a trading decision.

📊 5-MINUTE CANDLES (Most recent last):
{self._format_candles(candles)}

📈 RSI: {rsi_value:.2f}
{"🔴 OVERBOUGHT - Enter SHORT" if rsi_value > 66.80 else "🟢 OVERSOLD - Enter LONG" if rsi_value < 35.28 else "🟠 EXIT ZONE" if abs(rsi_value - 50.44) < 2.0 else "⚠️ NO-MAN ZONE"}

🧠 SECOND BRAIN: {second_brain_signal.bias.upper()} (SL: {second_brain_signal.stop_loss_distance_pct:.2%}, TP: {second_brain_signal.take_profit_distance_pct:.2%})

📋 YOUR RECENT DECISIONS (Last 3 hours):
{self._format_recent_decisions(recent_decisions)}

Return your trading decision as JSON:"""
        
        user_content.append({
            "type": "text",
            "text": text_prompt
        })

        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 256,
            "system": system_prompt,  # System prompt (cached by Claude)
            "messages": [
                {"role": "user", "content": user_content}
            ],
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        
        with httpx.Client(timeout=15) as client:
            resp = client.post(self.endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        # Expecting the model to return a JSON string in content
        content = data.get("content", [])
        if not content:
            raise RuntimeError("No content from AI")
        text_blocks = [c.get("text", "") for c in content if c.get("type") == "text"]
        combined = "\n".join(text_blocks).strip()
        
        print(f"\n🤖 CLAUDE DECISION:")
        print(combined)
        print(f"{'='*80}\n")
        try:
            import json
            import re

            # Extract JSON object from response (handles prose before/after)
            # Find first { and last } to extract pure JSON
            start = combined.find("{")
            end = combined.rfind("}") + 1
            
            if start == -1 or end == 0:
                raise ValueError("No JSON object found in response")
            
            json_str = combined[start:end].strip()
            parsed = json.loads(json_str)
            
            # Override with Second Brain recommendations if confidence is high
            if second_brain_signal.confidence > 0.75:
                parsed['stop_loss_pct'] = second_brain_signal.stop_loss_distance_pct
                parsed['take_profit_pct'] = second_brain_signal.take_profit_distance_pct
                print(f"✅ Applied Second Brain recommendations (high confidence: {second_brain_signal.confidence:.1%})")
            
            if self.history_store:
                self.history_store.record_decision(parsed)
            return parsed
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Failed to parse AI response: {combined}") from exc

    def _format_candles(self, candles: List[Dict[str, Any]]) -> str:
        """Format candles for display in prompt"""
        if not candles:
            return "No candle data available"
        
        # Show last 20 candles
        recent = candles[-20:] if len(candles) > 20 else candles
        lines = ["Time          Open      High      Low       Close     Volume"]
        lines.append("-" * 70)
        
        for c in recent:
            timestamp = c.get('time', 'Unknown')
            open_price = c.get('open', 0)
            high = c.get('high', 0)
            low = c.get('low', 0)
            close = c.get('close', 0)
            volume = c.get('volume', 0)
            
            lines.append(f"{timestamp:<12}  ${open_price:<8.2f} ${high:<8.2f} ${low:<8.2f} ${close:<8.2f} {volume:<10.2f}")
        
        return "\n".join(lines)
    
    def _format_recent_decisions(self, decisions: List[Dict[str, Any]]) -> str:
        """Format recent decisions for display"""
        if not decisions:
            return "No recent decisions"
        
        lines = []
        for d in decisions[-5:]:  # Show last 5 decisions
            side = d.get('side', 'unknown')
            timestamp = d.get('timestamp', 'unknown')
            sl = d.get('stop_loss_pct', 0) * 100
            tp = d.get('take_profit_pct', 0) * 100
            lines.append(f"- {timestamp}: {side.upper()} (SL: {sl:.1f}%, TP: {tp:.1f}%)")
        
        return "\n".join(lines) if lines else "No recent decisions"
