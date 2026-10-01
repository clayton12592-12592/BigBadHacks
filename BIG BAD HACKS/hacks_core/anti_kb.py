"""Anti-Knockback: scale down (or drop) the velocity packets the server sends
for your own player after you get hit."""
import struct

from config import S
from protocol import ENTITY_VELOCITY, decode_varint
from . import movement


def clientbound(session, pid, payload):
    if pid != ENTITY_VELOCITY or not S["antikb"]:
        return payload
    eid, p = decode_varint(payload, 0)
    if eid != movement.st.eid:
        return payload
    pct = S["antikb_pct"]
    if pct <= 0:
        return None
    x, y, z = struct.unpack(">hhh", payload[p:p + 6])
    k = pct / 100
    return payload[:p] + struct.pack(">hhh", int(x * k), int(y * k), int(z * k)) + payload[p + 6:]
