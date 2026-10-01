"""Global hotkeys (Windows). Polls the keyboard with GetAsyncKeyState, so they
work while Minecraft has focus and need no extra packages.

Tip: pick keys you don't type in chat (F-keys, PageUp/PageDown, End...),
because hotkeys also fire while you type in other windows."""
import sys
import threading
import time

import registry
from config import S

IS_WIN = sys.platform.startswith("win")
user32 = None            # set on Windows (tests replace it with a fake)
toast = ("", 0.0)        # (message, time) - shown briefly in the GUI

VK = {c: 0x41 + i for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}
VK.update({str(i): 0x30 + i for i in range(10)})
VK.update({f"Num{i}": 0x60 + i for i in range(10)})
VK.update({f"F{i}": 0x6F + i for i in range(1, 13)})
VK.update({
    "Space": 0x20, "PageUp": 0x21, "PageDown": 0x22, "End": 0x23, "Home": 0x24,
    "Left": 0x25, "Up": 0x26, "Right": 0x27, "Down": 0x28, "Insert": 0x2D,
    "Delete": 0x2E, "Shift": 0x10, "Ctrl": 0x11, "Alt": 0x12,
    "-": 0xBD, "=": 0xBB, "[": 0xDB, "]": 0xDD, ";": 0xBA, "'": 0xDE,
    ",": 0xBC, ".": 0xBE, "/": 0xBF, "\\": 0xDC, "`": 0xC0,
})

_TK = {
    "Prior": "PageUp", "Next": "PageDown", "space": "Space",
    "Shift_L": "Shift", "Shift_R": "Shift", "Control_L": "Ctrl", "Control_R": "Ctrl",
    "Alt_L": "Alt", "Alt_R": "Alt", "minus": "-", "equal": "=", "bracketleft": "[",
    "bracketright": "]", "semicolon": ";", "apostrophe": "'", "comma": ",",
    "period": ".", "slash": "/", "backslash": "\\", "grave": "`",
}
_TK.update({f"KP_{i}": f"Num{i}" for i in range(10)})


def name_from_keysym(keysym):
    """Tk keysym -> our key name, or None if it can't be bound."""
    name = _TK.get(keysym, keysym)
    if len(name) == 1:
        name = name.upper()
    return name if name in VK else None


def say(msg):
    global toast
    toast = (msg, time.time())


def trigger(action):
    if action == "panic":
        for k in registry.PANIC_KEYS:
            S[k] = False
        say("PANIC - everything off")
    elif action in ("vclip_up", "vclip_down"):
        registry.ACTIONS.append(action)
        say("VClip up" if action == "vclip_up" else "VClip down")
    elif action in S and isinstance(S[action], bool):
        S[action] = not S[action]
        say(f"{registry.TITLES.get(action, action)} {'ON' if S[action] else 'OFF'}")


def poll_once(prev):
    """One scan of all bound keys; fires actions on key-down edges."""
    for action, key in list(S.get("hotkeys", {}).items()):
        vk = VK.get(key)
        if not vk:
            continue
        down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
        if down and not prev.get(action):
            trigger(action)
        prev[action] = down


def _loop():
    prev = {}
    while True:
        time.sleep(0.02)
        try:
            poll_once(prev)
        except Exception:
            pass


def start():
    global user32
    if not IS_WIN:
        return False
    import ctypes
    user32 = ctypes.windll.user32
    threading.Thread(target=_loop, daemon=True).start()
    return True
