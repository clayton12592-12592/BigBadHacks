"""Haste: client-side Haste effect (MC 1.21.5 / protocol 770).

Injects a fake Entity Effect packet into the game client so mining speed and
arm swing behave like Haste N. The server is never told."""
from config import S
from protocol import encode_varint, decode_varint
from . import movement

CB_ENTITY_EFFECT = 0x7D          # verified: minecraft-data 1.21.5
CB_REMOVE_EFFECT = 0x47
HASTE_ID = 2                     # verified: effects.json (0-based)
DURATION = 100                   # ticks the client keeps the effect
REFRESH_EVERY = 20               # re-send once a second (survives respawns)
FLAGS = 0x00                     # 0x06 = show particles + HUD icon

WATCH = {CB_ENTITY_EFFECT, CB_REMOVE_EFFECT}
_state = {"timer": 0, "active": False, "lvl": None}


def clientbound(session, pid, payload):
    """Don't let the server's own Haste updates on us override ours."""
    if pid in WATCH and S.get("haste"):
        try:
            eid, pos = decode_varint(payload, 0)
            eff, _ = decode_varint(payload, pos)
        except IndexError:
            return payload
        if eid == movement.st.eid and eff == HASTE_ID:
            return None
    return payload


def session_tick(session):
    eid = movement.st.eid
    if eid is None:
        _state["active"] = False
        return
    if S.get("haste"):
        level = max(1, min(5, int(S.get("haste_level", 5))))
        _state["timer"] -= 1
        if not _state["active"] or _state["timer"] <= 0 or level != _state["lvl"]:
            session.inject(CB_ENTITY_EFFECT,
                           encode_varint(eid) + encode_varint(HASTE_ID)
                           + encode_varint(level - 1) + encode_varint(DURATION)
                           + bytes([FLAGS]))
            _state.update(active=True, lvl=level, timer=REFRESH_EVERY)
    elif _state["active"]:
        session.inject(CB_REMOVE_EFFECT, encode_varint(eid) + encode_varint(HASTE_ID))
        _state["active"] = False