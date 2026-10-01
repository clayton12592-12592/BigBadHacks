"""Auto jump: hop over whatever you walk into."""


def compute(st, wish, S):
    if S["auto_jump"] and st.on_ground and st.hcol and wish != (0.0, 0.0):
        return {"vy": 0.42}
