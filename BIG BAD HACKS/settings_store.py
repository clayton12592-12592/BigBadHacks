"""Saves slider values and hotkeys to settings.json. Hack on/off switches are
never restored, so nothing starts enabled by surprise."""
import json
import os

import registry
from config import S

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


def load(path=None):
    try:
        with open(path or PATH) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return
    for k, v in data.items():
        if k in registry.PANIC_KEYS or k not in S:
            continue
        cur = S[k]
        if k == "hotkeys" and isinstance(v, dict):
            S["hotkeys"].update({a: n for a, n in v.items() if isinstance(n, str)})
        elif isinstance(cur, bool):
            if isinstance(v, bool):
                S[k] = v
        elif isinstance(cur, (int, float)):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                S[k] = v


def save(path=None):
    data = {k: v for k, v in S.items() if k not in registry.PANIC_KEYS}
    try:
        with open(path or PATH, "w") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass
