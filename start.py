#!/usr/bin/env python
"""Minimal startup test - no heavy imports"""
import sys
import os

print("STEP 1: Python started", flush=True)

# Test basic imports one by one
print("STEP 2: Testing imports...", flush=True)

try:
    print("  - importing time...", flush=True)
    import time
    print("  - importing asyncio...", flush=True)
    import asyncio
    print("  - importing json...", flush=True)
    import json
    print("  ✅ Basic imports OK", flush=True)
except Exception as e:
    print(f"  ❌ Basic import failed: {e}", flush=True)
    sys.exit(1)

try:
    print("  - importing httpx...", flush=True)
    import httpx
    print("  ✅ httpx OK", flush=True)
except Exception as e:
    print(f"  ❌ httpx failed: {e}", flush=True)

try:
    print("  - importing ccxt...", flush=True)
    import ccxt
    print("  ✅ ccxt OK", flush=True)
except Exception as e:
    print(f"  ❌ ccxt failed: {e}", flush=True)

try:
    print("  - importing pandas...", flush=True)
    import pandas
    print("  ✅ pandas OK", flush=True)
except Exception as e:
    print(f"  ❌ pandas failed: {e}", flush=True)

try:
    print("  - importing matplotlib...", flush=True)
    import matplotlib
    matplotlib.use('Agg')  # Non-GUI backend
    print("  ✅ matplotlib OK", flush=True)
except Exception as e:
    print(f"  ❌ matplotlib failed: {e}", flush=True)

print("STEP 3: All imports complete!", flush=True)
print("STEP 4: Starting main bot...", flush=True)

try:
    from src.runner_live import run_live
    print("STEP 5: Runner imported, starting...", flush=True)
    run_live()
except Exception as e:
    import traceback
    print(f"💥 CRASH: {e}", flush=True)
    traceback.print_exc()
    time.sleep(60)
    sys.exit(1)
