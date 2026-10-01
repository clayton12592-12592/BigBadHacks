"""Blink: the proxy holds back your movement packets (see proxy.py) while this
is on, then releases them all when you turn it off."""
from config import S

MOVE = {"player_position", "player_position_and_look", "player_look", "player_on_ground"}
QUEUED = 0      # shown on the Info tab


def session_tick(session):
    global QUEUED
    if not S["blink"] and session.blink_queue:
        for frame in session.blink_queue:
            session.server_w.write(frame)
        session.blink_queue.clear()
    QUEUED = len(session.blink_queue)
