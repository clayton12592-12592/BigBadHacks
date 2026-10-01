"""Infinite jump: pressing SPACE while airborne gives a fresh jump."""


def compute(st, wish, S):
    if not S["inf_jump"] or not st.jump_request:
        return None
    st.jump_request = False
    if st.on_ground:
        return None          # vanilla handles the ground jump
    return {"vy": S["jump_power"]}
