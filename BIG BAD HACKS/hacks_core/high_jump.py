"""High jump: a stronger jump when you leave the ground."""


def compute(st, wish, S):
    if S["high_jump"] and st.on_ground and "space" in st.keys:
        return {"vy": S["high_jump_power"]}
