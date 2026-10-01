"""Single source of truth: default settings, the module list (used by the GUI
and by hotkeys) and the queue of one-shot actions."""
import collections

ACTIONS = collections.deque()    # one-shot actions queued by hotkeys / GUI buttons


def f_bps(v): return f"{v * 20:.0f} b/s"
def f_x(v): return f"x{v:.1f}"
def f_2(v): return f"{v:.2f}"
def f_pct(v): return f"{v:.0f}%"
def f_sec(v): return f"{v:.0f} s"
def f_blocks(v): return f"{v:.0f} blocks"


# tab, key (None = no on/off switch), title, description, sliders, buttons
MODULES = [
    dict(tab="Movement", key="fly", title="Fly",
         desc="Hover and glide. Steer with W/A/S/D, Space to rise, Shift to sink.",
         sliders=[("Fly speed", "fly_speed", 0.1, 4.0, 0.05, f_bps)]),
    dict(tab="Movement", key="speed_on", title="Speed",
         desc="Boost your movement speed on the ground and in the air.",
         sliders=[("Multiplier", "speed_mult", 1.0, 5.0, 0.1, f_x)]),
    dict(tab="Movement", key="bunny_hop", title="Bunny Hop",
         desc="Hop automatically while you move, with a speed boost.",
         sliders=[("Hop speed", "bhop_speed", 1.0, 3.0, 0.1, f_x)]),
    dict(tab="Movement", key="inf_jump", title="Infinite Jump",
         desc="Press Space in mid-air to jump again.",
         sliders=[("Jump power", "jump_power", 0.2, 1.5, 0.02, f_2)]),
    dict(tab="Movement", key="high_jump", title="High Jump",
         desc="Jump much higher when you leave the ground.",
         sliders=[("Jump power", "high_jump_power", 0.5, 3.0, 0.05, f_2)]),
    dict(tab="Movement", key="auto_jump", title="Auto Jump",
         desc="Jump automatically when you run into a block."),
    dict(tab="Movement", key="spider", title="Spider",
         desc="Climb walls by walking into them.",
         sliders=[("Climb speed", "spider_speed", 0.05, 1.0, 0.05, f_bps)]),
    dict(tab="Movement", key="glide", title="Glide",
         desc="Fall slowly and softly instead of dropping.",
         sliders=[("Fall speed", "glide_speed", 0.01, 0.3, 0.01, f_bps)]),
    dict(tab="Movement", key=None, title="VClip",
         desc="Teleport straight up or down. Stay under 10 blocks or the server "
              "will rubber-band you back.",
         sliders=[("Distance", "vclip_dist", 1, 9, 1, f_blocks)],
         buttons=[("Up", "vclip_up"), ("Down", "vclip_down")]),

    dict(tab="Player", key="nofall", title="NoFall", desc="Take no fall damage."),
    dict(tab="Player", key="nofood", title="NoFood",
         desc="Stops sprinting from draining your hunger."),
    dict(tab="Player", key="antikb", title="Anti-Knockback",
         desc="Reduce or cancel the knockback you take from hits.",
         sliders=[("Knockback taken", "antikb_pct", 0, 100, 5, f_pct)]),
    dict(tab="Player", key="auto_respawn", title="Auto Respawn",
         desc="Respawn right after you die, no need to click."),
    dict(tab="Player", key="anti_afk", title="Anti-AFK",
         desc="Nudges your view now and then so idle kicks don't hit you.",
         sliders=[("Every", "afk_interval", 5, 120, 5, f_sec)]),
    dict(tab="Player", key="blink", title="Blink",
         desc="Holds your movement back. Turn it off and you jump to where "
              "you really are, all at once."),
     dict(tab="Player", key="haste", title="Haste",
         desc="Mine and swing faster, like a Haste potion effect (client-side).",
         sliders=[("Level", "haste_level", 1, 5, 1, lambda v: f"Haste {v:.0f}")]),
]

ACTION_ITEMS = [
    ("vclip_up", "VClip up"),
    ("vclip_down", "VClip down"),
    ("panic", "Panic (turn everything off)"),
]

DEFAULT_HOTKEYS = {
    "fly": "F6", "speed_on": "F7", "inf_jump": "F8", "blink": "F9",
    "vclip_up": "PageUp", "vclip_down": "PageDown", "panic": "End",
}

TITLES = {m["key"]: m["title"] for m in MODULES if m["key"]}
PANIC_KEYS = [m["key"] for m in MODULES if m["key"]]

DEFAULTS = {
    "nofall": True, "nofood": True,
    "fly": False, "fly_speed": 0.5,            # blocks per tick (x20 = blocks/sec)
    "speed_on": False, "speed_mult": 1.5,
    "bunny_hop": False, "bhop_speed": 1.3,
    "inf_jump": False, "jump_power": 0.42,     # 0.42 = vanilla jump
    "high_jump": False, "high_jump_power": 0.8,
    "auto_jump": False,
    "spider": False, "spider_speed": 0.2,
    "glide": False, "glide_speed": 0.05,
    "vclip_dist": 8,
    "antikb": False, "antikb_pct": 0,
    "auto_respawn": False,
    "anti_afk": False, "afk_interval": 30,
    "blink": False,
    "topmost": True,
    "debug": False,
     "haste": False, "haste_level": 5,
}
