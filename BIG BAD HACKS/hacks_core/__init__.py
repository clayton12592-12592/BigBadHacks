from config import S
from registry import DEFAULTS, DEFAULT_HOTKEYS

# Filled in here so an old/short config.py can never cause missing-key errors.
for _k, _v in DEFAULTS.items():
    S.setdefault(_k, _v)
S.setdefault("hotkeys", {})
for _k, _v in DEFAULT_HOTKEYS.items():
    S["hotkeys"].setdefault(_k, _v)

import settings_store  # noqa: E402
settings_store.load()

from protocol import ENTITY_VELOCITY, CB_DEATH  # noqa: E402
from . import (movement, nofall, no_food, vclip, blink, anti_afk,   # noqa: E402,F401
               auto_respawn, anti_kb, haste)

# movement first: it must see the real on_ground value before nofall rewrites it
_ALL = [movement, nofall, no_food, vclip, blink, anti_afk, auto_respawn, anti_kb, haste]
CLIENTBOUND_WATCH = {ENTITY_VELOCITY, CB_DEATH} | haste.WATCH


def process_upstream(name, raw):
    """Client->server packet through every module.
    Returns the (possibly modified) payload, or None to drop the packet."""
    if S["debug"]:
        print("client->server:", name)
    for m in _ALL:
        f = getattr(m, "upstream", None)
        if f:
            raw = f(name, raw)
            if raw is None:
                return None
    return raw


def process_clientbound(session, pid, payload):
    """Server->client packet (only ids in CLIENTBOUND_WATCH). None = drop."""
    for m in _ALL:
        f = getattr(m, "clientbound", None)
        if f:
            payload = f(session, pid, payload)
            if payload is None:
                return None
    return payload


def session_tick(session):
    """Once per tick while in game: modules that need the live connection."""
    for m in _ALL:
        f = getattr(m, "session_tick", None)
        if f:
            f(session)