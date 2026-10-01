"""NoFall: fall damage is calculated by the server from the client's
'on_ground' flag, so we force that bit to 1 in every movement packet.
In 1.21.5 the last byte is a flags field: bit 0 = on_ground,
bit 1 = horizontal collision (kept as-is).
"""
from config import S

MOVE_PACKETS = {
    "player_position",
    "player_position_and_look",
    "player_look",
    "player_on_ground",
}


def upstream(name, raw):
    if S["nofall"] and name in MOVE_PACKETS and raw:
        return raw[:-1] + bytes([raw[-1] | 1])
    return raw
