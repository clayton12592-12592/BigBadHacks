"""Auto respawn: when the server says you died, send 'perform respawn'."""
import asyncio

from config import S
from protocol import CB_DEATH, SB_CLIENT_COMMAND, encode_varint


def clientbound(session, pid, payload):
    if pid == CB_DEATH and S["auto_respawn"]:
        asyncio.get_running_loop().call_later(
            0.4, lambda: session.send_server(SB_CLIENT_COMMAND, encode_varint(0)))
    return payload
