import time
import tkinter as tk
from tkinter import ttk

import config
import hacks_core                     # also fills in missing settings / loads settings.json
import hotkeys
import registry
import settings_store
from config import S
from registry import ACTIONS, ACTION_ITEMS, DEFAULTS, MODULES

FONT = "Segoe UI"
BG, CARD, BORDER = "#0f1117", "#171a23", "#242938"
FG, MUTED = "#e8eaf2", "#8a90a6"
ACCENT, OFF = "#7c5cff", "#2b3042"
GREEN, AMBER, BLUE, RED = "#34d399", "#f5b942", "#60a5fa", "#ff6b81"

widgets = []   # everything that can redraw itself


class Toggle(tk.Canvas):
    """Pill-shaped on/off switch bound to S[key]."""
    def __init__(self, parent, key, bg=CARD):
        super().__init__(parent, width=46, height=26, bg=bg, highlightthickness=0, cursor="hand2")
        self.key = key
        self.bind("<Button-1>", self._click)
        widgets.append(self)
        self.draw()

    def draw(self):
        self.delete("all")
        c = ACCENT if S[self.key] else OFF
        self.create_oval(1, 1, 25, 25, fill=c, outline=c)
        self.create_oval(21, 1, 45, 25, fill=c, outline=c)
        self.create_rectangle(13, 1, 33, 25, fill=c, outline=c)
        x = 33 if S[self.key] else 13
        self.create_oval(x - 9, 4, x + 9, 22, fill="#ffffff", outline="#ffffff")

    def _click(self, _):
        S[self.key] = not S[self.key]
        self.draw()


class Slider(tk.Canvas):
    """Draggable slider bound to S[key]; value shown on the right."""
    def __init__(self, parent, key, lo, hi, step, fmt):
        super().__init__(parent, height=28, bg=CARD, highlightthickness=0, cursor="hand2")
        self.key, self.lo, self.hi, self.step, self.fmt = key, lo, hi, step, fmt
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)
        widgets.append(self)

    def _track(self):
        return 8, max(self.winfo_width(), 120) - 84

    def draw(self):
        x0, x1 = self._track()
        frac = (S[self.key] - self.lo) / (self.hi - self.lo)
        kx = x0 + min(1, max(0, frac)) * (x1 - x0)
        self.delete("all")
        self.create_line(x0, 14, x1, 14, fill=OFF, width=4, capstyle="round")
        self.create_line(x0, 14, kx, 14, fill=ACCENT, width=4, capstyle="round")
        self.create_oval(kx - 8, 6, kx + 8, 22, fill="#ffffff", outline=ACCENT, width=2)
        self.create_text(self.winfo_width() - 4, 14, text=self.fmt(S[self.key]),
                         fill=FG, anchor="e", font=(FONT, 10, "bold"))

    def _drag(self, e):
        x0, x1 = self._track()
        frac = min(1, max(0, (e.x - x0) / (x1 - x0)))
        v = round((self.lo + frac * (self.hi - self.lo)) / self.step) * self.step
        S[self.key] = round(min(self.hi, max(self.lo, v)), 3)
        self.draw()


class Scroll(tk.Frame):
    """Scrollable page that stretches to the window width."""
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)

        def on_scroll(lo, hi):                  # hide the bar when everything fits
            bar.set(lo, hi)
            if float(lo) <= 0 and float(hi) >= 1:
                bar.pack_forget()
            elif not bar.winfo_ismapped():
                bar.pack(side="right", fill="y", before=self.canvas)

        self.canvas.configure(yscrollcommand=on_scroll)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y", before=self.canvas)
        self.inner = tk.Frame(self.canvas, bg=BG)
        win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(win, width=e.width))


def button(parent, text, cmd, bg=OFF, fg=FG, hover="#363c52", **kw):
    b = tk.Label(parent, text=text, bg=bg, fg=fg, font=(FONT, 10, "bold"),
                 cursor="hand2", padx=14, pady=7, **kw)
    b.bind("<Button-1>", lambda e: cmd())
    b.bind("<Enter>", lambda e: b.config(bg=hover))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


def card(parent, m):
    f = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
    f.pack(fill="x", padx=14, pady=5)
    top = tk.Frame(f, bg=CARD)
    top.pack(fill="x", padx=14, pady=(12, 0))
    tk.Label(top, text=m["title"], bg=CARD, fg=FG, font=(FONT, 12, "bold")).pack(side="left")
    if m["key"]:
        Toggle(top, m["key"]).pack(side="right")
    sliders, buttons = m.get("sliders", []), m.get("buttons", [])
    desc = tk.Label(f, text=m["desc"], bg=CARD, fg=MUTED, font=(FONT, 9), anchor="w", justify="left")
    desc.pack(fill="x", padx=14, pady=(2, 10 if sliders or buttons else 12))
    f.bind("<Configure>", lambda e, d=desc: d.config(wraplength=max(120, e.width - 32)))
    for label, skey, lo, hi, step, fmt in sliders:
        row = tk.Frame(f, bg=CARD)
        row.pack(fill="x", padx=14, pady=(0, 10))
        tk.Label(row, text=label, bg=CARD, fg=MUTED, font=(FONT, 9)).pack(anchor="w")
        Slider(row, skey, lo, hi, step, fmt).pack(fill="x")
    if buttons:
        row = tk.Frame(f, bg=CARD)
        row.pack(fill="x", padx=14, pady=(0, 12))
        for text, action in buttons:
            button(row, text, lambda a=action: ACTIONS.append(a)).pack(side="left", padx=(0, 8))


def run_gui(hook=None):
    root = tk.Tk()
    root.title("Big Bad Hacks")
    root.configure(bg=BG)
    root.geometry("480x780")
    root.minsize(400, 460)                      # freely resizable
    root.attributes("-topmost", bool(S["topmost"]))

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Vertical.TScrollbar", background=OFF, troughcolor=BG, bordercolor=BG,
                    arrowcolor=FG, darkcolor=OFF, lightcolor=OFF, gripcount=0)
    try:                                        # dark title bar on Windows 10/11
        import ctypes
        root.update()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
    except Exception:
        pass

    # ---- header
    head = tk.Frame(root, bg=BG)
    head.pack(fill="x", padx=20, pady=(16, 2))
    tk.Label(head, text="BIG BAD HACKS", bg=BG, fg=FG, font=(FONT, 16, "bold")).pack(anchor="w")
    status = tk.Label(head, text="", bg=BG, fg=MUTED, font=(FONT, 10), anchor="w")
    status.pack(anchor="w", pady=(2, 0))
    toast = tk.Label(head, text=" ", bg=BG, fg=AMBER, font=(FONT, 9, "bold"), anchor="w")
    toast.pack(anchor="w")

    # ---- tab bar
    tabbar = tk.Frame(root, bg=BG)
    tabbar.pack(fill="x", padx=14, pady=(4, 0))
    tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=14)

    # ---- bottom bar (panic) - packed before the pages so it always stays visible
    bottom = tk.Frame(root, bg=BG)
    bottom.pack(side="bottom", fill="x", padx=14, pady=10)
    button(bottom, "PANIC - turn everything off", lambda: hotkeys.trigger("panic"),
           bg="#3a1d26", fg=RED, hover="#4d2431").pack(fill="x")

    container = tk.Frame(root, bg=BG)
    container.pack(fill="both", expand=True, pady=(6, 0))

    TABS = ["Movement", "Player", "Hotkeys", "Info"]
    pages = {t: Scroll(container) for t in TABS}
    tab_labels, tab_lines = {}, {}
    current = [None]

    def show(name):
        for t, p in pages.items():
            p.pack_forget()
            tab_labels[t].config(fg=FG if t == name else MUTED)
            tab_lines[t].config(bg=ACCENT if t == name else BG)
        pages[name].pack(fill="both", expand=True)
        current[0] = pages[name]

    for t in TABS:
        cell = tk.Frame(tabbar, bg=BG)
        cell.pack(side="left", padx=(0, 18))
        lab = tk.Label(cell, text=t, bg=BG, fg=MUTED, font=(FONT, 11, "bold"), cursor="hand2")
        lab.pack()
        line = tk.Frame(cell, bg=BG, height=2)
        line.pack(fill="x", pady=(3, 0))
        lab.bind("<Button-1>", lambda e, n=t: show(n))
        tab_labels[t], tab_lines[t] = lab, line

    root.bind_all("<MouseWheel>",
                  lambda e: current[0].canvas.yview_scroll(int(-e.delta / 120), "units"))

    # ---- module pages
    for m in MODULES:
        card(pages[m["tab"]].inner, m)

    # ---- hotkeys page
    hk = pages["Hotkeys"].inner
    note = "Click a key to rebind it.  Esc = cancel,  Backspace = clear."
    if not hotkeys.IS_WIN:
        note = "Global hotkeys need Windows - they are off on this system."
    tk.Label(hk, text=note, bg=BG, fg=MUTED, font=(FONT, 9), anchor="w",
             justify="left").pack(fill="x", padx=16, pady=(8, 4))
    items = [(m["key"], m["title"]) for m in MODULES if m["key"]] + ACTION_ITEMS
    hk_buttons, listening = {}, {"action": None}

    def refresh_hotkeys():
        for a, b in hk_buttons.items():
            b.config(text=S["hotkeys"].get(a) or "-", fg=FG, bg=OFF)

    def start_listen(action):
        refresh_hotkeys()
        listening["action"] = action
        hk_buttons[action].config(text="Press a key...", fg="#ffffff", bg=ACCENT)

    def on_key(e):
        action = listening["action"]
        if not action:
            return
        if e.keysym == "BackSpace":
            S["hotkeys"][action] = ""
        elif e.keysym != "Escape":
            name = hotkeys.name_from_keysym(e.keysym)
            if not name:
                return "break"               # unsupported key: keep listening
            for a, v in S["hotkeys"].items():
                if v == name and a != action:
                    S["hotkeys"][a] = ""      # one key, one action
            S["hotkeys"][action] = name
        listening["action"] = None
        refresh_hotkeys()
        return "break"

    root.bind_all("<Key>", on_key)
    for action, title in items:
        row = tk.Frame(hk, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        row.pack(fill="x", padx=14, pady=4)
        tk.Label(row, text=title, bg=CARD, fg=FG, font=(FONT, 11, "bold")).pack(side="left", padx=14, pady=10)
        b = tk.Label(row, text="", bg=OFF, fg=FG, font=(FONT, 10, "bold"), width=13,
                     cursor="hand2", pady=5)
        b.pack(side="right", padx=12)
        b.bind("<Button-1>", lambda e, a=action: start_listen(a))
        hk_buttons[action] = b
    refresh_hotkeys()

    # ---- info page
    info = pages["Info"].inner
    live = tk.Frame(info, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
    live.pack(fill="x", padx=14, pady=5)
    tk.Label(live, text="Live", bg=CARD, fg=FG, font=(FONT, 12, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
    readouts = {}
    for name in ["Position", "Speed", "On ground", "Facing", "Entity id", "Blink queue"]:
        r = tk.Frame(live, bg=CARD)
        r.pack(fill="x", padx=14, pady=2)
        tk.Label(r, text=name, bg=CARD, fg=MUTED, font=(FONT, 10)).pack(side="left")
        readouts[name] = tk.Label(r, text="-", bg=CARD, fg=FG, font=(FONT, 10, "bold"))
        readouts[name].pack(side="right")
    tk.Frame(live, bg=CARD, height=10).pack()

    sett = tk.Frame(info, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
    sett.pack(fill="x", padx=14, pady=5)
    tk.Label(sett, text="Settings", bg=CARD, fg=FG, font=(FONT, 12, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
    for text, key in [("Keep window on top", "topmost"), ("Log packets (debug)", "debug")]:
        r = tk.Frame(sett, bg=CARD)
        r.pack(fill="x", padx=14, pady=5)
        tk.Label(r, text=text, bg=CARD, fg=MUTED, font=(FONT, 10)).pack(side="left")
        Toggle(r, key).pack(side="right")

    def reset():
        S.update(DEFAULTS)
        for w in widgets:
            w.draw()

    btns = tk.Frame(sett, bg=CARD)
    btns.pack(fill="x", padx=14, pady=(8, 14))
    button(btns, "Reset to defaults", reset).pack(side="left", padx=(0, 8))
    button(btns, "Save now", settings_store.save).pack(side="left")

    # ---- live refresh
    ticks = [0]

    def refresh():
        import proxy
        from hacks_core import movement, blink
        if proxy.PROFILE is None:
            text, color = "Signing in to Microsoft... (see console)", AMBER
        elif movement.st.eid is not None:
            text, color = f"In game as {proxy.PROFILE['name']}", GREEN
        else:
            text, color = f"Ready - join localhost:{config.LISTEN_PORT}", BLUE
        status.config(text="●  " + text, fg=color)
        msg, ts = hotkeys.toast
        toast.config(text=msg if time.time() - ts < 2.5 else " ")
        st = movement.st
        readouts["Position"].config(text=f"{st.x:.1f}, {st.y:.1f}, {st.z:.1f}" if st.have_pos else "-")
        readouts["Speed"].config(text=f"{((st.dx ** 2 + st.dz ** 2) ** 0.5) * 20:.1f} b/s")
        readouts["On ground"].config(text="yes" if st.on_ground else "no")
        readouts["Facing"].config(text=f"{st.yaw:.0f} / {st.pitch:.0f}")
        readouts["Entity id"].config(text=str(st.eid) if st.eid is not None else "-")
        readouts["Blink queue"].config(text=str(blink.QUEUED))
        root.attributes("-topmost", bool(S["topmost"]))
        for w in widgets:                       # pick up changes made by hotkeys
            w.draw()
        ticks[0] += 1
        if ticks[0] % 25 == 0:                  # autosave every ~5 s
            settings_store.save()
        root.after(200, refresh)

    def on_close():
        settings_store.save()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    show("Movement")
    root.update_idletasks()
    for w in widgets:
        w.draw()
    refresh()
    if hook:
        root.after(400, lambda: hook(root, show, start_listen))
    root.mainloop()
