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
- Trade on 0x leverage.
- Max open trades at once is 1.
- Compound the money.
- Trade max 2 times per hour with a 30 minute interval break per trade.
- Trade on 5 min chart only.

Given recent 5m candles for ETH/USDC and recent decisions, return a JSON with fields: side in {long, short, flat}, position_fraction (0-0.5), stop_loss_pct, take_profit_pct, max_slippage_pct. Keep trades sparse and avoid overtrading. Return JSON only."""
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

            # Strip markdown code fence or "json" prefix if present
            if combined.startswith("json"):
                combined = combined[4:].strip()
            if combined.startswith("```json"):
                combined = combined[7:]
            if combined.endswith("```"):
                combined = combined[:-3]
            combined = combined.strip()
            
            parsed = json.loads(combined)
            if self.history_store:
                self.history_store.record_decision(parsed)
            return parsed
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Failed to parse AI response: {combined}") from exc
