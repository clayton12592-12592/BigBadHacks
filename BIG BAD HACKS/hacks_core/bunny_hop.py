"""Bunny hop: keep jumping while you move, with a speed boost."""


def compute(st, wish, S):
    if S["bunny_hop"] and st.on_ground and wish != (0.0, 0.0):
        sp = 0.28 * S["bhop_speed"]
        return {"vy": 0.42, "h": (wish[0] * sp, wish[1] * sp)}
