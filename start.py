#!/usr/bin/env python
"""Startup wrapper to catch import errors and display them"""
import sys
print("HELLO FROM PYTHON", flush=True)
sys.stdout.flush()

import traceback
import os

# Force unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'

print("=" * 50, flush=True)
print("🚀 Starting TradingETH bot...", flush=True)
print(f"Python version: {sys.version}", flush=True)
print(f"Working directory: {os.getcwd()}", flush=True)

try:
    print("Listing files...", flush=True)
    print(f"Files: {os.listdir('.')}", flush=True)
except Exception as e:
    print(f"Error listing files: {e}", flush=True)

print("=" * 50, flush=True)

try:
    print("📦 Importing modules...", flush=True)
    from src.runner_live import run_live
    print("✅ Imports successful!", flush=True)
    run_live()
except Exception as e:
    print(f"💥 CRASH: {type(e).__name__}: {e}", flush=True)
    traceback.print_exc()
    # Keep the process alive for a bit so logs can be captured
    import time
    time.sleep(30)
    sys.exit(1)
