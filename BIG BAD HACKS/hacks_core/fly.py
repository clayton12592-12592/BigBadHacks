"""Fly: cancel gravity and steer with the keyboard.
W/A/S/D = move relative to where you look, SPACE = up, SHIFT = down."""


def compute(st, wish, S):
    if not S["fly"]:
        return None
    sp = S["fly_speed"]
    vy = (("space" in st.keys) - ("shift" in st.keys)) * sp
    return {"h": (wish[0] * sp, wish[1] * sp), "vy": vy}
