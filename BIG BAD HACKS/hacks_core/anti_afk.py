"""Anti-AFK: every few seconds send a tiny view change so the server's idle
timer resets."""
import struct
import time

from config import S
from protocol import SB_PLAYER_LOOK
from . import movement


def session_tick(session):
    if not S["anti_afk"] or not movement.st.have_pos:
        return
    now = time.monotonic()
    if now - session.afk_last < S["afk_interval"]:
        return
    session.afk_last = now
    session.afk_flip = not session.afk_flip
    st = movement.st
    yaw = st.yaw + (2.0 if session.afk_flip else -2.0)
    session.send_server(SB_PLAYER_LOOK, struct.pack(">ffB", yaw, st.pitch, 1 if st.on_ground else 0))
