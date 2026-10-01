"""Movement core: tracks the player and injects velocity packets.
All velocity hacks (fly, speed, jumps, spider, glide...) are combined here.

A vanilla client applies 'entity_velocity' packets sent for its own entity
id, so every tick we send whatever velocity the enabled modules want.
Keys come from the client's own 'player_input' packet (1.21.2+):
W A S D, SPACE, SHIFT. Targets Minecraft 1.21.5.
"""
import math
import struct

from config import S
from protocol import ENTITY_VELOCITY, encode_varint
from . import fly, inf_jump, high_jump, glide, spider, auto_jump, bunny_hop

INPUT_BITS = {0x01: "w", 0x02: "s", 0x04: "a", 0x08: "d", 0x10: "space", 0x20: "shift"}


class State:
    def __init__(self):
        self.eid = None                      # own entity id (from play login)
        self.x = self.y = self.z = 0.0
        self.dx = self.dy = self.dz = 0.0    # observed motion per tick
        self.yaw = self.pitch = 0.0
        self.on_ground = True
        self.hcol = False                    # pushing against a wall
        self.have_pos = False
        self.packets = 0                     # position packets since last tick
        self.keys = set()
        self.jump_request = False


st = State()


def reset():
    st.__init__()


# ---- tracking client->server packets (runs BEFORE nofall rewrites ground) --
def _pos(x, y, z):
    if st.have_pos:
        st.dx, st.dy, st.dz = x - st.x, y - st.y, z - st.z
    st.x, st.y, st.z = x, y, z
    st.have_pos = True
    st.packets += 1


def _input(flags):
    new = {name for bit, name in INPUT_BITS.items() if flags & bit}
    if "space" in new and "space" not in st.keys:
        st.jump_request = True
    st.keys = new


def upstream(name, raw):
    try:
        if name == "player_position":
            x, y, z, f = struct.unpack(">dddB", raw[:25])
            _pos(x, y, z)
            st.on_ground, st.hcol = bool(f & 1), bool(f & 2)
        elif name == "player_position_and_look":
            x, y, z, yaw, pitch, f = struct.unpack(">dddffB", raw[:33])
            _pos(x, y, z)
            st.yaw, st.pitch, st.on_ground, st.hcol = yaw, pitch, bool(f & 1), bool(f & 2)
        elif name == "player_look":
            st.yaw, st.pitch, f = struct.unpack(">ffB", raw[:9])
            st.on_ground, st.hcol = bool(f & 1), bool(f & 2)
        elif name == "player_on_ground":
            st.on_ground, st.hcol = bool(raw[0] & 1), bool(raw[0] & 2)
        elif name == "player_input":
            _input(raw[0])
    except (struct.error, IndexError):
        pass
    return raw


# ---- speed -------------------------------------------------------------
def wish_dir():
    """Unit vector (x, z) from WASD and the player's yaw, or (0, 0)."""
    f = ("w" in st.keys) - ("s" in st.keys)
    r = ("d" in st.keys) - ("a" in st.keys)
    if not f and not r:
        return 0.0, 0.0
    yaw = math.radians(st.yaw)
    vx = -math.sin(yaw) * f - math.cos(yaw) * r
    vz = math.cos(yaw) * f - math.sin(yaw) * r
    n = math.hypot(vx, vz)
    return vx / n, vz / n


def _speed(st, wish, S):
    if not S["speed_on"] or wish == (0.0, 0.0):
        return None
    v = 0.28 * S["speed_mult"]                      # 0.28 b/tick = vanilla sprint
    if st.on_ground:
        vy = 0.42 if "space" in st.keys else -0.0784  # keep jumping working
    else:
        vy = st.dy
    return {"h": (wish[0] * v, wish[1] * v), "vy": vy}


# later entries override earlier ones when they set the same component
MODS = (_speed, bunny_hop.compute, auto_jump.compute, spider.compute,
        glide.compute, high_jump.compute, inf_jump.compute)


# ---- per-tick injection --------------------------------------------------
def tick(inject):
    """inject(packet_id, payload) sends a packet to the client."""
    if st.eid is None:
        return
    if st.packets == 0:            # client stood still this tick
        st.dx = st.dz = 0.0
    st.packets = 0
    if not S["inf_jump"]:
        st.jump_request = False

    wish = wish_dir()
    out = fly.compute(st, wish, S)        # fly takes over completely
    if not out:
        out = {}
        for mod in MODS:
            r = mod(st, wish, S)
            if r:
                out.update(r)
    if not out:
        return

    hx, hz = out.get("h", (st.dx, st.dz))
    vy = out.get("vy", st.dy)
    vx, vy, vz = (max(-32767, min(32767, int(c * 8000))) for c in (hx, vy, hz))
    inject(ENTITY_VELOCITY, encode_varint(st.eid) + struct.pack(">hhh", vx, vy, vz))
