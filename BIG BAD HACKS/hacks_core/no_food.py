"""NoFood: sprinting is the main source of hunger drain, and the server only
knows you're sprinting because the client sends an entity_action packet with
action id 3 (start sprinting). We drop that packet, so the server never
applies sprint exhaustion.

This does NOT stop other exhaustion sources (taking damage, regen, etc.).
"""
from config import S

START_SPRINTING = 3


def _varint(data, pos):
    result = shift = 0
    while True:
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, pos
        shift += 7


def upstream(name, raw):
    if S["nofood"] and name == "entity_action":
        try:
            _entity_id, pos = _varint(raw, 0)
            action, _ = _varint(raw, pos)
            if action == START_SPRINTING:
                return None  # drop it
        except IndexError:
            pass
    return raw
