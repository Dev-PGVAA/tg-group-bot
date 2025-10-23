# src/forwarder_main.py
import asyncio
import sys
from forwarder import run_forwarder

if __name__ == "__main__":
    try:
        asyncio.run(run_forwarder())
    except KeyboardInterrupt:
        print("Forwarder stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Forwarder error: {e}")
        sys.exit(1)