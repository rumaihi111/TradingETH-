import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from ai_client import AISignalClient

api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not api_key:
    print("ANTHROPIC_API_KEY not set")
    sys.exit(1)

client = AISignalClient(api_key=api_key)

# Test with minimal candles
candles = [
    {"ts": 1703462400000, "open": 2250.0, "high": 2260.0, "low": 2240.0, "close": 2255.0, "volume": 1000},
    {"ts": 1703462700000, "open": 2255.0, "high": 2270.0, "low": 2250.0, "close": 2265.0, "volume": 1100},
]

try:
    decision = client.fetch_signal(candles)
    print("Decision:", decision)
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()
