"""Glide: cap how fast you fall."""


def compute(st, wish, S):
    if S["glide"] and not st.on_ground and st.dy < -S["glide_speed"]:
        return {"vy": -S["glide_speed"]}
