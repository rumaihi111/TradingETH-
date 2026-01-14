import httpx
import base64
import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from io import BytesIO
import pandas as pd
import mplfinance as mpf
from datetime import datetime

from .history_store import HistoryStore
from .fractal_brain import NestedFractalBrain


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
        # Initialize Nested Fractal Brain for hive mind analysis
        self.fractal_brain = NestedFractalBrain(min_similarity=0.75, scale_ratio_min=2.0)

    def _calculate_rsi(self, closes: List[float], period: int = 14) -> List[float]:
        """Calculate RSI values for the given closes"""
        if len(closes) < period + 1:
            return [50.0] * len(closes)
        
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        rsi_values = [np.nan] * period
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi_values.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi_values.append(100 - (100 / (1 + rs)))
        
        # Add one more for the last close
        rsi_values.append(rsi_values[-1] if rsi_values else 50.0)
        
        return rsi_values

    def _get_chart_image(self, candles: List[Dict[str, Any]], rsi_value: float = None) -> Optional[str]:
        """Generate candlestick chart with RSI indicator from candle data and return base64 encoded image"""
        try:
            # Convert candles to DataFrame for mplfinance
            df_data = []
            closes = []
            for candle in candles:
                # Support both 'ts' and 'time' keys for timestamp
                timestamp = candle.get('ts', candle.get('time', 0))
                close_price = float(candle['close'])
                closes.append(close_price)
                df_data.append({
                    'Date': datetime.fromtimestamp(timestamp / 1000),
                    'Open': float(candle['open']),
                    'High': float(candle['high']),
                    'Low': float(candle['low']),
                    'Close': close_price,
                    'Volume': float(candle['volume'])
                })
            
            df = pd.DataFrame(df_data)
            df.set_index('Date', inplace=True)
            
            # Calculate RSI(14)
            rsi_values = self._calculate_rsi(closes, period=14)
            df['RSI'] = rsi_values[:len(df)]
            
            # Get current RSI for display
            current_rsi = rsi_values[-1] if rsi_values else 50.0
            
            # Create RSI panel as additional plot
            # RSI zone lines: 35.28 (long entry), 50.44 (exit), 66.80 (short entry)
            rsi_panel = [
                mpf.make_addplot(df['RSI'], panel=2, color='purple', ylabel='RSI(14)', ylim=(0, 100)),
            ]
            
            # Create horizontal lines for RSI zones
            df['RSI_Long'] = 35.28
            df['RSI_Exit'] = 50.44
            df['RSI_Short'] = 66.80
            
            rsi_panel.extend([
                mpf.make_addplot(df['RSI_Long'], panel=2, color='green', linestyle='--', secondary_y=False),
                mpf.make_addplot(df['RSI_Exit'], panel=2, color='gray', linestyle=':', secondary_y=False),
                mpf.make_addplot(df['RSI_Short'], panel=2, color='red', linestyle='--', secondary_y=False),
            ])
            
            # Determine RSI zone for title
            if current_rsi < 35.28:
                rsi_zone = "LONG ZONE 📈"
            elif current_rsi > 66.80:
                rsi_zone = "SHORT ZONE 📉"
            else:
                rsi_zone = "NO-MAN'S LAND ⚠️"
            
            # Create chart with RSI panel
            buf = BytesIO()
            mpf.plot(
                df,
                type='candle',
                style='charles',
                title=f'ETH/USDC 5-Min | RSI({14}): {current_rsi:.2f} - {rsi_zone}',
                ylabel='Price (USDC)',
                volume=True,
                addplot=rsi_panel,
                figsize=(14, 10),
                panel_ratios=(3, 1, 1.5),  # Price, Volume, RSI
                savefig=dict(fname=buf, dpi=100, bbox_inches='tight')
            )
            
            # Encode to base64
            buf.seek(0)
            image_b64 = base64.b64encode(buf.read()).decode('utf-8')
            print(f"✅ Chart with RSI generated (RSI: {current_rsi:.2f} - {rsi_zone})")
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
        
        # HIVE MIND: Consult Nested Fractal Brain first
        print("\n🧠 FRACTAL BRAIN: Analyzing for nested fractal patterns...")
        fractal_analysis = self.fractal_brain.analyze(candles)
        
        if fractal_analysis['fractals_found']:
            print(f"✅ Found {fractal_analysis['pattern_count']} nested fractal pattern(s)!")
            for i, pattern in enumerate(fractal_analysis['patterns'], 1):
                print(f"   Pattern {i}: {pattern['shape']} (similarity: {pattern['similarity']:.2%}, scale: {pattern['scale_ratio']:.1f}x)")
        else:
            print(f"⚠️ {fractal_analysis['reason']}")
        print()
        
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
- Trade on 10x leverage.
- Max open trades at once is 1.
- Compound the money.
- Trade max 2 times per hour with a 30 minute interval break per trade.
- Analyze 5-minute ETH/USDC charts using visual pattern recognition.
- Look for chart patterns: triangles, flags, head & shoulders, double tops/bottoms, wedges.
- Identify key support/resistance levels visually.
- Use candlestick patterns: engulfing, doji, hammers, shooting stars.

HIVE MIND - NESTED FRACTAL BRAIN:
- Work alongside the Nested Fractal Brain that detects unique patterns repeating at different scales.
- Nested Fractals = SAME unique shape appearing at 2+ different scales within the same session.
- NOT normal trading patterns - look for weird shapes: staircases, mountains, words, zigzags.
- When fractals are detected, consider their implications for trend continuation/reversal.
- Fractal signal: If large pattern completed bullish, small pattern may follow same path.

RISK MANAGEMENT:
- Always set stop_loss_pct (recommended: 0.03-0.08 = 3-8% from entry)
- Always set take_profit_pct (recommended: 0.08-0.15 = 8-15% from entry)
- With 10x leverage, a 5% stop loss = 50% of position at risk
- Risk/Reward: Take profit should be 1.5x-3x stop loss distance
- Tighter stops (3-5%) for choppy markets, wider stops (6-8%) for trending markets
- Set stops based on support/resistance levels, not arbitrary percentages

RESPONSE FORMAT:
Return a JSON object with these fields:
- side: "long", "short", or "flat"
- position_fraction: 0.8 (IGNORED - bot always uses 80% of wallet)
- stop_loss_pct: decimal (e.g., 0.05 = 5% stop from entry)
- take_profit_pct: decimal (e.g., 0.10 = 10% profit target)
- max_slippage_pct: decimal (e.g., 0.5 = 0.5% max slippage)

Example: {"side": "long", "position_fraction": 0.8, "stop_loss_pct": 0.04, "take_profit_pct": 0.10, "max_slippage_pct": 0.5}

CRITICAL: Return ONLY the JSON object. No explanations, no prose, no markdown."""

        # Generate chart image from candle data for visual analysis
        chart_image = self._get_chart_image(candles)
        
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

🧠 NESTED FRACTAL BRAIN ANALYSIS:
{self._format_fractal_analysis(fractal_analysis)}

📋 YOUR RECENT DECISIONS (Last 3 hours):
{self._format_recent_decisions(recent_decisions)}

Based on your visual chart analysis + fractal brain insights:
- Set appropriate stop loss (3-8% from entry recommended)
- Set take profit target (5-15% recommended)
- Consider recent trading history to avoid overtrading
- If fractals detected, factor their predictive signal into your decision

Return your trading decision as JSON:"""
        else:
            # Fallback to text-based analysis if image fails
            text_prompt = f"""Analyze the following 5-minute chart data for ETH/USDC and make a trading decision.

📊 5-MINUTE CANDLES (Most recent last):
{self._format_candles(candles)}

🧠 NESTED FRACTAL BRAIN ANALYSIS:
{self._format_fractal_analysis(fractal_analysis)}

📋 YOUR RECENT DECISIONS (Last 3 hours):
{self._format_recent_decisions(recent_decisions)}

Based on this 5-minute chart analysis + fractal brain insights:
- Identify trends, support/resistance levels
- Look for momentum, volume patterns
- Consider recent decision history to avoid overtrading
- Set appropriate stop loss and take profit levels
- If fractals detected, factor their predictive signal into your decision

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
    
    def _format_fractal_analysis(self, fractal_analysis: Dict[str, Any]) -> str:
        """Format fractal brain analysis for AI prompt"""
        if not fractal_analysis['fractals_found']:
            return f"No nested fractals detected. {fractal_analysis['reason']}"
        
        lines = [f"✅ {fractal_analysis['pattern_count']} Nested Fractal(s) Detected:"]
        
        for i, pattern in enumerate(fractal_analysis['patterns'], 1):
            shape = pattern['shape'].replace('_', ' ').title()
            similarity = pattern['similarity'] * 100
            scale = pattern['scale_ratio']
            
            small = pattern['small_pattern']
            large = pattern['large_pattern']
            
            lines.append(f"\nPattern {i}: {shape}")
            lines.append(f"  • Similarity: {similarity:.1f}%")
            lines.append(f"  • Scale Ratio: {scale:.1f}x (large is {scale:.1f}x bigger than small)")
            lines.append(f"  • Small Pattern: {small['start_time']} ({small['size']} candles)")
            lines.append(f"  • Large Pattern: {large['start_time']} ({large['size']} candles)")
        
        # Add signal if available
        if 'signal' in fractal_analysis:
            signal = fractal_analysis['signal']
            if signal == "bullish_fractal":
                lines.append("\n⚡ Fractal Signal: BULLISH (large pattern ended up, small may follow)")
            elif signal == "bearish_fractal":
                lines.append("\n⚡ Fractal Signal: BEARISH (large pattern ended down, small may follow)")
            else:
                lines.append("\n⚡ Fractal Signal: NEUTRAL (no clear directional bias)")
        
        return "\n".join(lines)
