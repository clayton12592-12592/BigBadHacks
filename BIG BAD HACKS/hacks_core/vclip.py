"""VClip: teleport straight up/down by sending the client a relative
'teleport' packet. Distances under 10 blocks stay inside the server's
movement-speed limit."""
import struct

import registry
from config import S
from protocol import CB_POSITION, encode_varint, decode_varint
from . import movement

IDS = set()            # teleport ids we made up (their confirmations are dropped)
_counter = [0x4B00]
REL_ALL = 0x1FF        # every field relative: x y z yaw pitch dx dy dz yawDelta


def upstream(name, raw):
    if name == "teleport_confirm":
        try:
            tid, _ = decode_varint(raw, 0)
        except IndexError:
            return raw
        if tid in IDS:
            IDS.discard(tid)
            return None
    return raw


def session_tick(session):
    while registry.ACTIONS:
        action = registry.ACTIONS.popleft()
        if action in ("vclip_up", "vclip_down") and movement.st.eid is not None:
            dist = float(S["vclip_dist"]) * (1 if action == "vclip_up" else -1)
            _counter[0] += 1
            tid = _counter[0]
            IDS.add(tid)
            session.inject(CB_POSITION, encode_varint(tid)
                           + struct.pack(">ddddddffI", 0, dist, 0, 0, 0, 0, 0.0, 0.0, REL_ALL))
