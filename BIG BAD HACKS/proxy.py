"""Transparent 1.21.5 proxy: relays packets between client and server and
lets hacks_core edit a few of them. Written from scratch because quarry has
no 1.21.5 support. Logs in to online-mode servers with your Microsoft account."""
import asyncio
import json
import struct
import os
import zlib

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_der_public_key

import auth
import config
import hacks_core
import registry
from hacks_core import movement
from protocol import (
    SERVERBOUND_PLAY, SB_CONFIGURATION_ACK, CB_LOGIN_DISCONNECT,
    CB_ENCRYPTION_REQUEST, CB_SET_COMPRESSION, CB_PLAY_LOGIN, ENTITY_VELOCITY,
    encode_varint, decode_varint, read_varint, mc_string, handshake,
)

PROFILE = None      # filled in by serve() after the Microsoft login


class CipherReader:
    """AES/CFB8-decrypting wrapper (Minecraft's stream encryption)."""
    def __init__(self, reader, secret):
        self.r = reader
        self.dec = Cipher(algorithms.AES(secret), modes.CFB8(secret)).decryptor()

    async def readexactly(self, n):
        return self.dec.update(await self.r.readexactly(n))


class CipherWriter:
    def __init__(self, writer, secret):
        self.w = writer
        self.enc = Cipher(algorithms.AES(secret), modes.CFB8(secret)).encryptor()

    def write(self, data):
        self.w.write(self.enc.update(data))

    async def drain(self):
        await self.w.drain()

    def close(self):
        self.w.close()


class Session:
    def __init__(self, client_w, server_w):
        self.client_w = client_w
        self.server_w = server_w
        self.state = "handshake"
        self.threshold = -1          # -1 = compression off
        self.tick_task = None
        self.dead = False
        self.blink_queue = []        # movement frames held back by Blink
        self.afk_last = 0.0
        self.afk_flip = False

    # ---- framing ---------------------------------------------------------
    def frame(self, packet_id, payload):
        pkt = encode_varint(packet_id) + payload
        if self.threshold >= 0:
            if len(pkt) >= self.threshold:
                body = encode_varint(len(pkt)) + zlib.compress(pkt)
            else:
                body = b"\x00" + pkt
        else:
            body = pkt
        return encode_varint(len(body)) + body

    def split(self, body, full=True):
        """Return (packet_id, payload). full=False only decodes the id."""
        data = body
        if self.threshold >= 0:
            size, pos = decode_varint(body, 0)
            if size == 0:
                data = body[pos:]
            elif full:
                data = zlib.decompress(body[pos:])
            else:
                data = zlib.decompressobj().decompress(body[pos:], 8)
        pid, pos = decode_varint(data, 0)
        return pid, data[pos:]

    # ---- client -> server ------------------------------------------------
    def on_serverbound(self, body, out):
        pid, payload = self.split(body)
        st = self.state
        if st == "handshake" and pid == 0:
            proto, p = decode_varint(payload, 0)
            slen, p = decode_varint(payload, p)
            nxt, _ = decode_varint(payload, p + slen + 2)
            self.state = "status" if nxt == 1 else "login"
            # tell the real server its own hostname, not "localhost"
            return self.frame(0, handshake(proto, config.TARGET_HOST, config.TARGET_PORT, nxt))
        if st == "login" and pid == 0x03:
            self.state = "configuration"
        elif st == "configuration" and pid == 0x03:
            self.state = "play"
        elif st == "play":
            if pid == SB_CONFIGURATION_ACK:
                self.state = "configuration"
                return out
            name = SERVERBOUND_PLAY.get(pid)
            if name:
                new = hacks_core.process_upstream(name, payload)
                if new is None:
                    return None
                if config.S.get("blink") and name in hacks_core.blink.MOVE:
                    self.blink_queue.append(self.frame(pid, new))   # hold it back
                    return None
                if new != payload:
                    return self.frame(pid, new)
        return out

    # ---- server -> client ------------------------------------------------
    def on_clientbound(self, body, out):
        st = self.state
        if st == "login":
            pid, payload = self.split(body)
            if pid == CB_SET_COMPRESSION:
                self.threshold, _ = decode_varint(payload, 0)
        elif st == "play":
            pid, _ = self.split(body, full=False)
            if pid == CB_PLAY_LOGIN:
                _, payload = self.split(body)
                movement.st.eid = struct.unpack(">i", payload[:4])[0]
                if self.tick_task is None:
                    self.tick_task = asyncio.ensure_future(self.tick_loop())
            elif pid in hacks_core.CLIENTBOUND_WATCH:
                _, payload = self.split(body)
                new = hacks_core.process_clientbound(self, pid, payload)
                if new is None:
                    return None
                if new != payload:
                    return self.frame(pid, new)
        return out

    # ---- injection -------------------------------------------------------
    def inject(self, packet_id, payload):
        """Send a packet to the game client."""
        self.client_w.write(self.frame(packet_id, payload))

    def send_server(self, packet_id, payload):
        """Send a packet to the real server."""
        self.server_w.write(self.frame(packet_id, payload))

    async def tick_loop(self):
        while True:
            await asyncio.sleep(0.05)        # one Minecraft tick
            if self.state == "play":
                try:
                    movement.tick(self.inject)
                    hacks_core.session_tick(self)
                except Exception as e:       # never let a bug kill the loop
                    if repr(e) != getattr(self, "_last_err", None):
                        self._last_err = repr(e)
                        print("tick error:", repr(e))

    async def pump(self, reader, writer, serverbound):
        try:
            while True:
                length = await read_varint(reader)
                body = await reader.readexactly(length)
                out = encode_varint(length) + body
                out = (self.on_serverbound if serverbound else self.on_clientbound)(body, out)
                if out is not None:
                    writer.write(out)
                    await writer.drain()
                if self.dead:
                    break
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()


async def read_frame(reader):
    n = await read_varint(reader)
    return await reader.readexactly(n)


def disconnect_frame(s, msg):
    return s.frame(CB_LOGIN_DISCONNECT, mc_string(json.dumps({"text": msg})))


async def online_login(s, client_r, client_w, server_r, server_w):
    """Log in to the real server as the authenticated account.
    Returns the (possibly encrypted) server reader/writer."""
    await read_frame(client_r)                       # client's own login start (ignored)
    if PROFILE is None:
        raise RuntimeError("Microsoft login isn't finished yet - check the console")
    server_w.write(s.frame(0, mc_string(PROFILE["name"]) + bytes.fromhex(PROFILE["uuid"])))
    await server_w.drain()

    body = await read_frame(server_r)
    pid, payload = s.split(body)
    if pid != CB_ENCRYPTION_REQUEST:                 # offline-mode server: just relay
        client_w.write(s.on_clientbound(body, encode_varint(len(body)) + body))
        return server_r, server_w

    sid_len, p = decode_varint(payload, 0)
    server_id = payload[p:p + sid_len].decode("ascii")
    p += sid_len
    klen, p = decode_varint(payload, p)
    pubkey = payload[p:p + klen]
    p += klen
    tlen, p = decode_varint(payload, p)
    token = payload[p:p + tlen]

    secret = os.urandom(16)
    pub = load_der_public_key(pubkey)
    enc_secret = pub.encrypt(secret, padding.PKCS1v15())
    enc_token = pub.encrypt(token, padding.PKCS1v15())

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, auth.join_server, PROFILE["access_token"],
                               PROFILE["uuid"], auth.server_hash(server_id, secret, pubkey))
    server_w.write(s.frame(0x01, encode_varint(len(enc_secret)) + enc_secret
                                 + encode_varint(len(enc_token)) + enc_token))
    await server_w.drain()
    return CipherReader(server_r, secret), CipherWriter(server_w, secret)


async def handle_client(client_r, client_w):
    server_w = None
    s = None
    try:
        first = await read_frame(client_r)           # handshake (never compressed)
        _, p = decode_varint(first, 0)
        proto, q = decode_varint(first, p)
        slen, q = decode_varint(first, q)
        nxt, _ = decode_varint(first, q + slen + 2)

        server_r, server_w = await asyncio.open_connection(config.TARGET_HOST, config.TARGET_PORT)
        movement.reset()
        registry.ACTIONS.clear()
        s = Session(client_w, server_w)
        s.state = "status" if nxt == 1 else "login"
        server_w.write(s.frame(0, handshake(proto, config.TARGET_HOST, config.TARGET_PORT, nxt)))

        if nxt != 1:
            try:
                server_r, server_w = await online_login(s, client_r, client_w, server_r, server_w)
                s.server_w = server_w        # (maybe encrypted) writer used for injections
            except Exception as e:
                print("Login failed:", e)
                client_w.write(disconnect_frame(s, f"Big Bad Hacks: {e}"))
                return
        await asyncio.gather(s.pump(client_r, server_w, True), s.pump(server_r, client_w, False))
    except OSError as e:
        print("Could not reach", config.TARGET_HOST, config.TARGET_PORT, "-", e)
    except (asyncio.IncompleteReadError, ConnectionError):
        pass
    finally:
        if s and s.tick_task:
            s.tick_task.cancel()
        movement.reset()
        client_w.close()
        if server_w:
            server_w.close()


async def serve():
    global PROFILE
    print("Logging in to Microsoft (a code will appear below if needed)...", flush=True)
    PROFILE = await asyncio.get_running_loop().run_in_executor(None, auth.login)
    print(f"Logged in as {PROFILE['name']}")
    server = await asyncio.start_server(handle_client, config.LISTEN_HOST, config.LISTEN_PORT)
    async with server:
        await server.serve_forever()
