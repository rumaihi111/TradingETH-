import httpx
import base64
from typing import Any, Dict, List, Optional
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
        venice_api_key: Optional[str] = None,
        venice_endpoint: str = "https://api.venice.ai/v1/chat/completions",
        venice_model: str = "mistral-31-24b",
    ):
        self.api_key = api_key
        self.endpoint = endpoint
        self.history_store = history_store
        self.history_hours = history_hours
        self.venice_api_key = venice_api_key
        self.venice_endpoint = venice_endpoint
        self.venice_model = venice_model
        # Initialize Nested Fractal Brain for hive mind analysis
        self.fractal_brain = NestedFractalBrain(min_similarity=0.75, scale_ratio_min=2.0)

    def _get_chart_image(self, candles: List[Dict[str, Any]]) -> Optional[str]:
        """Generate candlestick chart from candle data and return base64 encoded image"""
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
            
            # Create chart
            buf = BytesIO()
            mpf.plot(
                df,
                type='candle',
                style='charles',
                title='ETH/USDC 5-Minute Chart',
                ylabel='Price (USDC)',
                volume=True,
                figsize=(14, 8),
                savefig=dict(fname=buf, dpi=100, bbox_inches='tight')
            )
            
            # Encode to base64
            buf.seek(0)
            image_b64 = base64.b64encode(buf.read()).decode('utf-8')
            print(f"✅ Chart image generated successfully ({len(image_b64)} chars)")
            return image_b64
            
        except Exception as e:
            print(f"⚠️ Failed to generate chart image: {e}")
            print(f"   Falling back to text-based analysis")
            return None

    def fetch_signal(self, candles: List[Dict[str, Any]], current_position: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY missing")
        # Use last 130 candles for AI vision (optimal chart density for pattern recognition)
        candles = candles[-130:] if len(candles) > 130 else candles
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

        # Determine trade direction using Venice (when not monitoring an open position)
        venice_side: Optional[str] = None
        venice_reason: Optional[str] = None
        venice_pattern: Optional[str] = None
        if current_position is None and self.venice_api_key:
            venice_decision = self._get_direction_with_venice(candles, chart_image, fractal_analysis)
            if venice_decision and venice_decision.get("side"):
                venice_side = venice_decision.get("side")
                venice_reason = venice_decision.get("reason")
                venice_pattern = venice_decision.get("pattern")
                print(f"🤖 Venice direction: {venice_side.upper()} — {venice_pattern or 'pattern'} | {venice_reason or 'no rationale'}")

        # Constrain Claude's role depending on context
        if current_position is not None:
            pos_side = "long" if current_position.get("size", 0) > 0 else "short"
            entry = current_position.get("entry", 0)
            current_price = candles[-1]["close"] if candles else 0
            pnl_pct = ((current_price - entry) / entry) * (1 if current_position.get("size", 0) > 0 else -1) if entry > 0 else 0
            
            # Get SL/TP from recent decision
            last_decision = recent_decisions[-1].get('decision', {}) if recent_decisions else {}
            sl_pct = last_decision.get('stop_loss_pct', 0)
            tp_pct = last_decision.get('take_profit_pct', 0)
            
            monitor_info = f"\n\nMONITORING MODE:\n- You are monitoring an OPEN {pos_side.upper()} position.\n"
            monitor_info += f"- Entry: ${entry:.2f}, Current: ${current_price:.2f}, Unrealized P&L: {pnl_pct*100:+.2f}%\n"
            if sl_pct > 0:
                monitor_info += f"- Stop Loss set at {sl_pct*100:.1f}% from entry\n"
            if tp_pct > 0:
                monitor_info += f"- Take Profit set at {tp_pct*100:.1f}% from entry\n"
            monitor_info += "- Decide whether to CLOSE (side=\"flat\") or HOLD (side=\"" + pos_side + "\").\n"
            monitor_info += "- Close if: SL/TP reached, reversal pattern detected, or risk increases.\n"
            monitor_info += "- Hold if: trend intact, price action supports continuation.\n"
            monitor_info += "- Do NOT flip direction while monitoring."
            system_prompt = system_prompt + monitor_info
        elif venice_side:
            extra = "\n\nDIRECTION PROVIDED:\n- Use this side decided by Venice: side=\"" + venice_side + "\".\n"
            if venice_pattern:
                extra += "- Venice pattern: " + venice_pattern + "\n"
            if venice_reason:
                extra += "- Venice rationale: " + venice_reason + "\n"
            extra += "- Do NOT change the side; only set stop_loss_pct, take_profit_pct, max_slippage_pct.\n- Validate the described pattern in the image/data and base SL/TP on real support/resistance and volatility."
            system_prompt = system_prompt + extra

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
            # Enforce Venice side if provided (opening decision only)
            if venice_side:
                parsed["side"] = venice_side
                if venice_reason:
                    parsed["venice_reason"] = venice_reason
                if venice_pattern:
                    parsed["venice_pattern"] = venice_pattern
            
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

    def _get_direction_with_venice(
        self,
        candles: List[Dict[str, Any]],
        chart_image_b64: Optional[str],
        fractal_analysis: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Call Venice Mistral model to determine direction and rationale.
        Returns dict: {side: 'long'|'short'|'flat', reason: str, pattern: str} or None on error.
        """
        if not self.venice_api_key:
            return None
        try:
            system = (
                "You are a stateless trading direction decider with vision. Analyze the provided ETH/USDC 5m chart image."
                " Return a JSON object ONLY with fields: side ('long'|'short'|'flat'), pattern (string), reason (concise rationale)."
                " Base decision solely on the attached image and text."
            )
            user_parts: List[Dict[str, Any]] = []
            if chart_image_b64:
                user_parts.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": chart_image_b64},
                })
            user_parts.append({
                "type": "text",
                "text": (
                    "Text context (if image missing):\n" + self._format_candles(candles) +
                    "\n\nNested Fractal Brain:\n" + self._format_fractal_analysis(fractal_analysis) +
                    "\n\nReturn JSON only, e.g.: {\"side\": \"long\", \"pattern\": \"falling wedge\", \"reason\": \"breakout above resistance with volume\"}"
                ),
            })
            payload = {
                "model": self.venice_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_parts},
                ],
                "temperature": 0.1,
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.venice_api_key}",
            }
            with httpx.Client(timeout=15) as client:
                resp = client.post(self.venice_endpoint, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            text = None
            if isinstance(data, dict) and "choices" in data:
                try:
                    text = data["choices"][0]["message"]["content"]
                except Exception:
                    text = None
            if not text and isinstance(data, dict) and "content" in data:
                text = data.get("content")
            if not text:
                return None
            # Try to parse JSON object
            import json as _json
            decision_obj = None
            try:
                start = text.find("{")
                end = text.rfind("}") + 1
                if start != -1 and end > start:
                    decision_obj = _json.loads(text[start:end])
            except Exception:
                decision_obj = None
            if not decision_obj:
                # Fallback: extract tokens from text
                normalized = text.strip().upper()
                if "LONG" in normalized and "SHORT" in normalized:
                    side_token = "long" if normalized.index("LONG") < normalized.index("SHORT") else "short"
                elif "LONG" in normalized:
                    side_token = "long"
                elif "SHORT" in normalized:
                    side_token = "short"
                elif "FLAT" in normalized or "NEUTRAL" in normalized:
                    side_token = "flat"
                else:
                    side_token = None
                decision_obj = {"side": side_token, "pattern": None, "reason": text.strip()} if side_token else None
            # Normalize side
            side = (decision_obj.get("side") or "").lower() if decision_obj else None
            if side not in {"long", "short", "flat"}:
                return None
            return {
                "side": side,
                "pattern": decision_obj.get("pattern"),
                "reason": decision_obj.get("reason"),
            }
        except Exception as e:
            print(f"⚠️ Venice direction fetch failed: {e}")
            return None
    
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
