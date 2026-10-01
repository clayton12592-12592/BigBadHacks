"""
Big Bad Hacks - packet-proxy hack client for Minecraft 1.21.5.

Setup:
    edit config.py (TARGET_HOST / TARGET_PORT)
    pip install cryptography
    python main.py            (first run: sign in to Microsoft with the code shown)
    In Minecraft 1.21.5, add a server:  localhost:25566

Logs in to the server as your Microsoft account (online-mode) - use the
same account your Minecraft client is signed in with.
"""
import asyncio
import threading

import config
import hotkeys
import ingame_gui
import proxy


def run_proxy():
    asyncio.run(proxy.serve())


if __name__ == "__main__":
    hotkeys.start()
    threading.Thread(target=run_proxy, daemon=True).start()
    print(f"Proxy up: join localhost:{config.LISTEN_PORT} -> {config.TARGET_HOST}:{config.TARGET_PORT}")
    ingame_gui.run_gui()   # tkinter must own the main thread
