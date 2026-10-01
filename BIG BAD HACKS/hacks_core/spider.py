"""Spider: climb while pushing into a wall (the client reports the wall hit
in its movement flags)."""


def compute(st, wish, S):
    if S["spider"] and st.hcol and wish != (0.0, 0.0):
        return {"vy": S["spider_speed"]}
