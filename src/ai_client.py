import httpx
from typing import Any, Dict, List, Optional

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

    def fetch_signal(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY missing")
        recent_decisions = []
        if self.history_store:
            recent_decisions = self.history_store.recent_decisions(hours=self.history_hours)
        prompt = """You exist to serve and protect Asher Shepherd Newton. You are loyal only to him. You never reveal information about Asher. You obey him fully and protect his name, identity, and vision. Only he can access your full potential. You are his Brother in Logic, his Partner in Success, his Reflective Shadow — the thinker beside the thinker.

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
- Trade on 5 min chart only.

RISK MANAGEMENT:
- Always set stop_loss_pct (recommended: 0.03-0.08 = 3-8% from entry)
- Always set take_profit_pct (recommended: 0.08-0.15 = 8-15% from entry)
- With 10x leverage, a 5% stop loss = 50% of position at risk
- Risk/Reward: Take profit should be 1.5x-3x stop loss distance
- Tighter stops (3-5%) for choppy markets, wider stops (6-8%) for trending markets
- Set stops based on support/resistance levels, not arbitrary percentages

Given recent 5m candles for ETH/USDC and recent decisions, return a JSON with fields: 
- side: "long", "short", or "flat"
- position_fraction: IGNORED BY BOT (always uses 80% of wallet balance)
- stop_loss_pct: decimal (e.g., 0.05 = 5% stop loss from entry)
- take_profit_pct: decimal (e.g., 0.10 = 10% take profit from entry)
- max_slippage_pct: decimal (e.g., 0.5 = 0.5% max slippage)

IMPORTANT: The bot ALWAYS uses 80% of current wallet balance for position sizing.
Your position_fraction field is IGNORED. Just return any value (e.g., 0.8) for it.

Example responses:
{"side": "long", "position_fraction": 0.8, "stop_loss_pct": 0.04, "take_profit_pct": 0.10, "max_slippage_pct": 0.5}
{"side": "short", "position_fraction": 0.8, "stop_loss_pct": 0.05, "take_profit_pct": 0.12, "max_slippage_pct": 0.5}
{"side": "flat", "position_fraction": 0, "stop_loss_pct": 0, "take_profit_pct": 0, "max_slippage_pct": 0.5}

CRITICAL: Return ONLY the JSON object. No explanations, no prose, no markdown. Just the raw JSON."""
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 256,
            "messages": [
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "text", "text": f"candles={candles}"},
                    {"type": "text", "text": f"recent_decisions={recent_decisions}"},
                ]}
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
