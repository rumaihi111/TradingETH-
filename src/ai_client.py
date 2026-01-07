import httpx
import base64
from typing import Any, Dict, List, Optional
from io import BytesIO

from .history_store import HistoryStore


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

    def _get_chart_image(self) -> Optional[str]:
        """Fetch ETH 5-minute chart from TradingView and return base64 encoded image"""
        try:
            # TradingView chart snapshot URL (5-minute ETH/USDT)
            chart_url = "https://s3.tradingview.com/snapshots/u/uHjQKZME.png"
            
            # Alternative: Generate chart URL dynamically
            # symbol = "COINBASE:ETHUSD"
            # interval = "5"
            # chart_url = f"https://api.chart-img.com/v1/tradingview/advanced-chart?symbol={symbol}&interval={interval}&studies=&width=800&height=400"
            
            with httpx.Client(timeout=10) as client:
                response = client.get(chart_url)
                response.raise_for_status()
                
                # Encode image to base64
                image_b64 = base64.b64encode(response.content).decode('utf-8')
                return image_b64
        except Exception as e:
            print(f"⚠️ Failed to fetch chart image: {e}")
            return None

    def fetch_signal(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY missing")
        recent_decisions = []
        if self.history_store:
            recent_decisions = self.history_store.recent_decisions(hours=self.history_hours)
        
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

        # Fetch chart image for visual analysis
        chart_image = self._get_chart_image()
        
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

📋 YOUR RECENT DECISIONS (Last 3 hours):
{self._format_recent_decisions(recent_decisions)}

Based on your visual chart analysis:
- Set appropriate stop loss (3-8% from entry recommended)
- Set take profit target (5-15% recommended)
- Consider recent trading history to avoid overtrading

Return your trading decision as JSON:"""
        else:
            # Fallback to text-based analysis if image fails
            text_prompt = f"""Analyze the following 5-minute chart data for ETH/USDC and make a trading decision.

📊 5-MINUTE CANDLES (Most recent last):
{self._format_candles(candles)}

📋 YOUR RECENT DECISIONS (Last 3 hours):
{self._format_recent_decisions(recent_decisions)}

Based on this 5-minute chart analysis:
- Identify trends, support/resistance levels
- Look for momentum, volume patterns
- Consider recent decision history to avoid overtrading
- Set appropriate stop loss and take profit levels

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
