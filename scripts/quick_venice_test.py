#!/usr/bin/env python3
"""Quick Venice API test - just verify it responds"""
import os
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from src.config import load_settings

def test_venice():
    print("🧪 Quick Venice API Test\n")
    
    settings = load_settings()
    
    if not settings.venice_api_key:
        print("❌ VENICE_API_KEY not set")
        return False
    
    print(f"✅ Venice API key present")
    print(f"   Endpoint: {settings.venice_endpoint}")
    print(f"   Model: {settings.venice_model}\n")
    
    # Simple text-only test (no image to keep it fast)
    payload = {
        "model": settings.venice_model,
        "messages": [
            {"role": "system", "content": "You are a trading assistant. Answer in JSON only."},
            {"role": "user", "content": 'Say {"side": "long", "pattern": "test", "reason": "testing"}'}
        ],
        "temperature": 0.1,
        "max_tokens": 50,
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.venice_api_key}",
    }
    
    print("📡 Calling Venice API...")
    start = time.time()
    
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(settings.venice_endpoint, headers=headers, json=payload)
            elapsed = time.time() - start
            
            print(f"✅ Response received in {elapsed:.2f}s")
            print(f"   Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"   Response keys: {list(data.keys())}")
                
                # Try to extract content
                if "choices" in data:
                    content = data["choices"][0]["message"]["content"]
                    print(f"   Content: {content[:100]}")
                elif "content" in data:
                    print(f"   Content: {data['content'][:100]}")
                
                print("\n✅ Venice API is WORKING!")
                return True
            else:
                print(f"❌ Error: {resp.status_code}")
                print(f"   {resp.text}")
                return False
                
    except httpx.TimeoutException:
        print(f"❌ Timeout after 10 seconds")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_venice()
    sys.exit(0 if success else 1)
