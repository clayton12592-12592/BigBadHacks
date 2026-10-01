"""Minecraft 1.21.5 (protocol 770) helpers and packet IDs.
IDs come from the PrismarineJS minecraft-data protocol definition."""
import struct

# client -> server, PLAY state
SERVERBOUND_PLAY = {
    0x00: "teleport_confirm",
    0x1C: "player_position",
    0x1D: "player_position_and_look",
    0x1E: "player_look",
    0x1F: "player_on_ground",
    0x28: "entity_action",
    0x29: "player_input",
}
SB_CONFIGURATION_ACK = 0x0E      # play -> configuration
SB_CLIENT_COMMAND = 0x0A         # action 0 = perform respawn
SB_PLAYER_LOOK = 0x1E

# server -> client
CB_LOGIN_DISCONNECT = 0x00
CB_ENCRYPTION_REQUEST = 0x01
CB_SET_COMPRESSION = 0x03
CB_PLAY_LOGIN = 0x2B
ENTITY_VELOCITY = 0x5E
CB_DEATH = 0x3D
CB_POSITION = 0x41               # server teleports the player


def encode_varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def decode_varint(buf, pos=0):
    n = shift = 0
    while True:
        b = buf[pos]
        pos += 1
        n |= (b & 0x7F) << shift
        if not b & 0x80:
            return n, pos
        shift += 7


async def read_varint(reader):
    n = shift = 0
    while True:
        b = (await reader.readexactly(1))[0]
        n |= (b & 0x7F) << shift
        if not b & 0x80:
            return n
        shift += 7


def mc_string(s):
    raw = s.encode()
    return encode_varint(len(raw)) + raw


def handshake(protocol, host, port, next_state):
    return (encode_varint(protocol) + mc_string(host)
            + struct.pack(">H", port) + encode_varint(next_state))
