#!/usr/bin/env python
"""Startup wrapper to catch import errors and display them"""
import sys
import traceback
import os

# Force unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'

print("=" * 50, flush=True)
print("🚀 Starting TradingETH bot...", flush=True)
print(f"Python version: {sys.version}", flush=True)
print(f"Working directory: {os.getcwd()}", flush=True)
print(f"Files in directory: {os.listdir('.')}", flush=True)
print("=" * 50, flush=True)

try:
    print("📦 Importing modules...", flush=True)
    from src.runner_live import run_live
    print("✅ Imports successful!", flush=True)
    run_live()
except Exception as e:
    print(f"💥 CRASH: {type(e).__name__}: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)
