import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from config import load_settings


def main():
    try:
        settings = load_settings()
    except Exception as e:
        print("Settings error:", e)
        return

    print("Anthropic key present:", bool(settings.anthropic_api_key))
    print("Venice key present:", bool(getattr(settings, "venice_api_key", "")))
    print("Hyperliquid testnet:", settings.hyperliquid_testnet)
    print("Private key set:", bool(settings.private_key))
    print("Ready to run basic checks.")


if __name__ == "__main__":
    main()
