"""IoT Escape Room: main game window and game logic.

Where to contribute:
  content.py        - rooms, riddles, quiz questions (no code changes needed)
  scenes.py         - block-built room pictures and the player sprite
  hardware.py       - Raspberry Pi / LED API
  EscapeRoom.py     - this file: UI layout, puzzles, locks, animations, timer, scoring
"""
import argparse
import random
import re
import tkinter as tk

from content import ROOMS
from hardware import HardwareBridge
from scenes import B, FLOOR, H, SCENES, W, draw_player

# ---------- Settings: tweak these to rebalance the game ----------
GAME_SECONDS = 300      # total time for the whole escape room
WRONG_PENALTY = 5       # seconds lost per wrong riddle/quiz answer
LOCK_PENALTY = 10       # seconds lost per failed speed lock
HINT_PENALTY = 15       # seconds lost per hint
BG = "#12162b"          # main background colour
FG = "#eceff1"          # main text colour
LAYOUT_HEIGHT = 650  # unscaled height of header + scene + panel + status line


# ---------- Screen scaling ----------
# Scene code draws in logical coordinates (scenes.W x scenes.H); this canvas scales them to the real screen.
class ScaledCanvas(tk.Canvas):
    """Canvas that takes logical coordinates and multiplies them by k, so scene code is size-independent."""

    def __init__(self, master, k, **kw):
        self.k = k
        for key in ("width", "height"):
            kw[key] = int(kw[key] * k)
        super().__init__(master, **kw)

    def _args(self, args):
        return [a * self.k if isinstance(a, (int, float)) else a for a in args]

    def _opts(self, kw):
        if "width" in kw:
            kw["width"] = kw["width"] * self.k
        return kw

    def move(self, tag, dx, dy):
        super().move(tag, dx * self.k, dy * self.k)

    def scale(self, tag, x, y, sx, sy):
        super().scale(tag, x * self.k, y * self.k, sx, sy)

    def bbox(self, *tags):
        box = super().bbox(*tags)
        return tuple(v / self.k for v in box) if box else None

    def coords(self, item, *new):
        if new:
            return super().coords(item, *self._args(new))
        return [v / self.k for v in super().coords(item)]


# Wrap the drawing methods so callers can keep using logical coordinates.
for _name in ("create_rectangle", "create_oval", "create_polygon", "create_line", "create_text", "create_arc"):
    def _make(base):
        def create(self, *args, **kw):
            return base(self, *self._args(args), **self._opts(kw))
        return create
    setattr(ScaledCanvas, _name, _make(getattr(tk.Canvas, _name)))


# ---------- The game ----------
class EscapeRoomGame:
    """Owns the window, the game state and the flow: title -> rooms (riddles, quizzes, locks) -> end screen."""

    def __init__(self, root, bridge):
        # Game state (reset in start_game)
        self.root = root
        self.bridge = bridge
        self.running = False
        self.busy = False
        self.token = 0
        self.room_idx = 0
        self.step_idx = 0
        self.score = 0
        self.time_remaining = GAME_SECONDS
        self.locks_done = 0
        self.hints_used = 0
        self.finished_rooms = 0
        self.steps_done = 0
        self.total_steps = sum(len(r["steps"]) for r in ROOMS)
        self.fx_blocks = []
        self.leg_off = (0, 0)
        self.blink_on = False

        # Window: fullscreen, key shortcuts, and a scale factor so the game fills the screen height
        root.title("IoT Escape Room")
        root.configure(bg=BG)
        root.attributes("-fullscreen", True)
        root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False))
        root.bind("<F11>", lambda e: root.attributes("-fullscreen", not root.attributes("-fullscreen")))
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        self.k = min(3.0, max(1.0, min(sw / W, sh / LAYOUT_HEIGHT)))
        root.tk.call("tk", "scaling", float(root.tk.call("tk", "scaling")) * self.k)  # scales all text
        self.build_ui()
        root.bind("<F9>", lambda e: self.skip_step())  # tester shortcut
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.show_title()
        # Start the three background loops: animation, 1-second clock, Pi commands
        root.after(150, self.animate)
        root.after(1000, self.tick)
        root.after(200, self.poll_commands)

    # ---------- UI scaffolding ----------
    def build_ui(self):
        """Create the layout: header bar (room, LEDs, timer, score, hint), scene canvas, puzzle panel, status line."""
        self.main = tk.Frame(self.root, bg=BG)
        self.main.place(relx=0.5, rely=0.5, anchor="center")
        top = tk.Frame(self.main, bg="#0b0e1f")
        top.pack(fill="x")
        self.room_lbl = tk.Label(top, text="", font=("Arial", 16, "bold"), fg="#ffd54f", bg="#0b0e1f")
        self.room_lbl.pack(side="left", padx=12, pady=6)
        self.hint_btn = tk.Button(top, text=f"Hint (-{HINT_PENALTY}s)", command=self.use_hint, state="disabled")
        self.hint_btn.pack(side="right", padx=12)
        self.score_lbl = tk.Label(top, text="Score: 0", font=("Arial", 14), fg=FG, bg="#0b0e1f")
        self.score_lbl.pack(side="right", padx=12)
        self.timer_lbl = tk.Label(top, text=f"{GAME_SECONDS // 60:02}:{GAME_SECONDS % 60:02}", font=("Courier", 18, "bold"), fg="#69f0ae", bg="#0b0e1f")
        self.timer_lbl.pack(side="right", padx=12)
        self.led_cv = ScaledCanvas(top, self.k, width=190, height=26, bg="#0b0e1f", highlightthickness=0)
        self.led_cv.pack(side="right", padx=12)
        self.leds = [self.led_cv.create_oval(8 + i * 34, 4, 28 + i * 34, 24, fill="#555", outline="#999")
                     for i in range(len(ROOMS))]
        self.alarm_led = self.led_cv.create_oval(8 + len(ROOMS) * 34, 4, 28 + len(ROOMS) * 34, 24,
                                                 fill="#333", outline="#999")

        self.canvas = ScaledCanvas(self.main, self.k, width=W, height=H, highlightthickness=0)
        self.canvas.pack()

        self.panel = tk.Frame(self.main, bg=BG, width=int(W * self.k), height=int(240 * self.k))
        self.panel.pack(fill="x")
        self.panel.pack_propagate(False)
        self.msg = tk.Label(self.panel, text="", font=("Arial", 12, "italic"), fg="#ffcc80", bg=BG,
                            wraplength=int((W - 40) * self.k), height=2)
        self.msg.pack(pady=(8, 0))
        self.body = tk.Frame(self.panel, bg=BG)
        self.body.pack(fill="both", expand=True)
        self.hw_lbl = tk.Label(self.main, text="", font=("Courier", 9), fg="#78909c", bg="#0b0e1f", anchor="w")
        self.hw_lbl.pack(fill="x")

    def clear_body(self):
        """Empty the puzzle panel. Also bumps `token`, which cancels any pending timed callbacks."""
        self.token += 1
        for w in self.body.winfo_children():
            w.destroy()

    def label(self, text, size=14, **kw):
        """Add a wrapped text label to the puzzle panel."""
        lbl = tk.Label(self.body, text=text, font=("Arial", size), fg=FG, bg=BG, wraplength=int((W - 80) * self.k), **kw)
        lbl.pack(pady=6)
        return lbl

    # ---------- Scene, player and HUD ----------
    def draw_scene(self, name):
        """Redraw the scene from scenes.py, wire up clickable hotspots, then add Steve and the HUD."""
        for item in self.canvas.find_all():
            if "fx" not in self.canvas.gettags(item):
                self.canvas.delete(item)
        SCENES[name](self.canvas)
        self.canvas.config(cursor="")
        for i in range(2):
            tag = f"hs_{i}"
            self.canvas.tag_bind(tag, "<Button-1>", lambda e, i=i: self.examine(i))
            self.canvas.tag_bind(tag, "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
            self.canvas.tag_bind(tag, "<Leave>", lambda e: self.canvas.config(cursor=""))
        if self.running and name != "title":
            self.place_player()
        self.draw_hud()

    def place_player(self):
        """Steve starts far enough back that each solved step (2 blocks) brings him to the door."""
        box = self.canvas.bbox("doorgap")
        if not box:
            return
        remaining = len(ROOMS[self.room_idx]["steps"]) - self.step_idx
        draw_player(self.canvas, box[0] - 2 * B - 2 * B * remaining, FLOOR * B + 4)
        self.leg_off = (0, 0)

    def swing_legs(self, n):
        """Alternate Steve's legs for walking frame n (None = standing)."""
        new = (0, 0) if n is None else ((-4, 0) if (n // 3) % 2 else (0, -4))
        self.canvas.move("legL", 0, new[0] - self.leg_off[0])
        self.canvas.move("legR", 0, new[1] - self.leg_off[1])
        self.leg_off = new

    def walk(self, dist, done, token):
        """Walk Steve right by dist pixels, then call done()."""
        frames = dist // 4

        def step(n):
            if token != self.token or not self.running:
                return
            if n >= frames:
                self.swing_legs(None)
                return done()
            self.canvas.move("player", 4, 0)
            self.swing_legs(n)
            self.root.after(30, step, n + 1)

        step(0)

    def enter_door(self, done, token):
        """Walk through the open doorway and vanish."""
        def gone():
            self.canvas.delete("player")
            done()

        self.walk(2 * B + 8, gone, token)

    def draw_hud(self):
        """Minecraft-style XP bar (progress) and hotbar (one item per cleared room)."""
        c = self.canvas
        c.delete("hud")
        if not self.running:
            return
        n = len(ROOMS)
        x0 = (W - n * 44) // 2
        c.create_rectangle(x0, 266, x0 + n * 44, 272, fill="#222", outline="#000", tags="hud")
        c.create_rectangle(x0, 266, x0 + n * 44 * self.steps_done / self.total_steps, 272,
                           fill="#7cfc00", outline="", tags="hud")
        for i, room in enumerate(ROOMS):
            sx = x0 + i * 44
            c.create_rectangle(sx, 276, sx + 42, 318, fill="#8b8b8b", outline="#373737", width=3, tags="hud")
            if i < self.finished_rooms:
                name, col = room["item"]
                c.create_rectangle(sx + 9, 284, sx + 33, 308, fill=col, outline="#000", width=2, tags="hud")
                c.create_text(sx + 21, 296, text=name[0], font=("Courier", 12, "bold"), fill="white", tags="hud")
        if c.find_withtag("fx"):
            c.tag_raise("fx")

    # ---------- transitions ----------
    def open_door(self, done, token):
        """Swing the scene's door open, then call done()."""
        box = self.canvas.bbox("doorgap")
        if not box:
            return done()
        hinge = box[0]

        def step(n):
            if token != self.token or not self.running:
                return
            if n >= 10:
                return done()
            self.canvas.scale("doorpanel", hinge, 0, 0.75, 1)
            self.root.after(45, step, n + 1)

        step(0)

    def dissolve(self, cover, done, token):
        """Fill (cover=True) or clear the screen with dark blocks in random order."""
        size = 24
        if cover:
            cells = [(x, y) for x in range(0, W, size) for y in range(0, H, size)]
            random.shuffle(cells)
            self.fx_blocks = cells
        pending = list(self.fx_blocks)
        shades = ["#050505", "#0d0d0d", "#161616"]

        def frame():
            if token != self.token:
                return
            for _ in range(45):
                if not pending:
                    break
                if cover:
                    x, y = pending.pop()
                    self.canvas.create_rectangle(x, y, x + size, y + size, fill=random.choice(shades),
                                                 outline="", tags="fx")
                else:
                    self.canvas.delete(pending.pop())
            if pending:
                self.root.after(25, frame)
            else:
                done()

        if not cover:
            pending[:] = list(self.canvas.find_withtag("fx"))
            random.shuffle(pending)
        frame()

    def transition_to(self, build):
        """Dissolve to black, run build() (draws the next scene), dissolve back in."""
        self.busy = True
        token = self.token

        def covered():
            if token != self.token or not self.running:
                return
            build()
            self.canvas.tag_raise("fx")
            self.dissolve(False, lambda: None, self.token)

        self.dissolve(True, covered, token)

    # ---------- Screens and game flow ----------
    def show_title(self):
        """Title screen with the START button."""
        self.running = False
        self.finished_rooms = 0
        self.draw_scene("title")
        self.room_lbl.config(text="")
        self.hint_btn.config(state="disabled")
        self.msg.config(text="")
        self.clear_body()
        self.label("Solve riddles and quiz questions, then beat the speed locks.\n"
                   f"Each lock you open makes the next one harder. You have {GAME_SECONDS // 60} minutes.", 13)
        tk.Button(self.body, text="START ESCAPE", font=("Arial", 16, "bold"), bg="#43a047", fg="white",
                  command=self.start_game).pack(pady=10)
        self.update_leds()

    def start_game(self):
        """Reset all state, notify the Pi, and transition into room 1."""
        self.running = True
        self.busy = False
        self.room_idx = self.step_idx = self.score = 0
        self.locks_done = self.hints_used = self.finished_rooms = 0
        self.time_remaining = GAME_SECONDS
        self.hint_btn.config(state="normal")
        self.hw("game_start")
        self.steps_done = 0
        self.transition_to(self.enter_room)

    def enter_room(self):
        """Draw the current room and show its first step."""
        room = ROOMS[self.room_idx]
        self.busy = False
        self.step_idx = 0
        self.draw_scene(room["scene"])
        self.room_lbl.config(text=f"Room {self.room_idx + 1}/{len(ROOMS)}: {room['name']}")
        self.hw("room_enter", room=self.room_idx + 1, name=room["name"])
        self.show_step()
        self.msg.config(text=room["intro"])

    def show_step(self):
        """Build the UI for the current step by calling build_riddle / build_quiz / build_lock."""
        self.clear_body()
        self.msg.config(text="")
        step = ROOMS[self.room_idx]["steps"][self.step_idx]
        getattr(self, f"build_{step['type']}")(step)
        self.refresh_header()

    def examine(self, i):
        """Show the clue for clickable scene object i (hotspots in content.py)."""
        if self.running and not self.busy:
            self.msg.config(text="You examine it: " + ROOMS[self.room_idx]["hotspots"][i])

    # ---------- Riddles and quizzes ----------
    @staticmethod
    def normalize(text):
        """Lowercase, strip punctuation and a leading a/an/the, so 'The Map!' matches 'map'."""
        text = re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()
        return re.sub(r"^(a|an|the) ", "", text)

    def build_riddle(self, step):
        """Free-text riddle: type the answer and press Enter."""
        self.label("RIDDLE: " + step["prompt"], 15)
        entry = tk.Entry(self.body, font=("Arial", 16), width=28)
        entry.pack(pady=6)
        entry.focus_set()

        def submit(_=None):
            if self.normalize(entry.get()) in step["answers"]:
                self.solved(step)
            else:
                self.wrong("Not quite. Try again!")
                entry.delete(0, "end")

        entry.bind("<Return>", submit)
        tk.Button(self.body, text="Submit", font=("Arial", 12), command=submit).pack()

    def build_quiz(self, step):
        """Multiple choice: shuffled buttons; a wrong button is disabled so it can't be spammed."""
        self.label("QUESTION: " + step["prompt"], 15)
        opts = step["options"][:]
        random.shuffle(opts)
        row = tk.Frame(self.body, bg=BG)
        row.pack(pady=8)
        def pick(opt, btn):
            if opt == step["answer"]:
                self.solved(step)
            else:
                btn.config(state="disabled")
                self.wrong("Wrong answer!")

        for opt in opts:
            b = tk.Button(row, text=opt, font=("Arial", 12), width=22, wraplength=int(170 * self.k))
            b.config(command=lambda o=opt, b=b: pick(o, b))
            b.pack(side="left", padx=5)

    def solved(self, step):
        """Award points, tell the Pi, and move Steve forward."""
        gain = step["points"]
        self.score += gain
        self.hw("puzzle_solved", type=step["type"], points=gain)
        self.msg.config(text=f"Correct! +{gain} points")
        self.advance()

    def wrong(self, text):
        """Apply the wrong-answer time penalty."""
        self.time_remaining -= WRONG_PENALTY
        self.hw("puzzle_failed")
        self.msg.config(text=f"{text} (-{WRONG_PENALTY}s)")
        self.check_time()

    def advance(self):
        """Step finished: walk Steve 2 blocks; if the room is done, open the door and go to the next room or win."""
        room = ROOMS[self.room_idx]
        self.step_idx += 1
        self.steps_done += 1
        self.draw_hud()
        self.busy = True
        self.clear_body()
        token = self.token
        if self.step_idx < len(room["steps"]):
            self.walk(2 * B, lambda: self.next_step_ready(token), token)
            return
        self.finished_rooms += 1
        self.draw_hud()
        self.hw("room_complete", room=self.room_idx + 1)
        item = room["item"][0]
        self.msg.config(text=f"Room cleared! You obtained: {item}. The door swings open...")
        if self.room_idx + 1 >= len(ROOMS):
            def finish():
                self.open_door(lambda: self.enter_door(lambda: self.end_game(True, token), token), token)
        else:
            self.room_idx += 1

            def finish():
                self.open_door(lambda: self.enter_door(lambda: self.transition_to(self.enter_room), token), token)
        self.walk(2 * B, finish, token)

    def next_step_ready(self, token):
        """Called after the walk animation; shows the next step unless the game was reset meanwhile."""
        if token == self.token and self.running:
            self.busy = False
            self.show_step()

    # ---------- Speed locks (difficulty rises with every lock opened) ----------
    def build_lock(self, step):
        """Lock screen. Level = locks opened so far: more digits, shorter display, tighter entry time."""
        level = self.locks_done
        digits = min(8, 3 + level)
        show_ms = max(350, 900 - 80 * level)
        limit = max(6, int(4 + digits * 1.5))
        self.label(f"SPEED LOCK #{level + 1}  -  {digits} digits, {show_ms / 1000:.2f}s each, "
                   f"{limit}s to enter", 14)
        display = tk.Label(self.body, text="[ ready ]", font=("Courier", 40, "bold"), fg="#69f0ae",
                           bg="#000", width=12)
        display.pack(pady=4)
        start = tk.Button(self.body, text="Unlock (watch carefully!)", font=("Arial", 13),
                          command=lambda: self.lock_flash(display, start, digits, show_ms, limit, level))
        start.pack(pady=4)

    def lock_flash(self, display, start_btn, digits, show_ms, limit, level):
        """Phase 1: flash a random code one digit at a time."""
        start_btn.config(state="disabled")
        token = self.token
        code = "".join(random.choice("0123456789") for _ in range(digits))

        def show(i):
            if token != self.token:
                return
            if i >= digits:
                display.config(text="?" * digits)
                self.lock_entry(display, code, limit, level, token)
                return
            display.config(text=code[i])
            self.root.after(show_ms, blank, i)

        def blank(i):
            if token != self.token:
                return
            display.config(text="")
            self.root.after(150, show, i + 1)

        display.config(text="")
        self.root.after(600, show, 0)

    def lock_entry(self, display, code, limit, level, token):
        """Phase 2: keypad + countdown bar; correct code opens the lock, wrong code or timeout costs time."""
        var = tk.StringVar()
        entry = tk.Entry(self.body, textvariable=var, font=("Courier", 18), width=10, justify="center")
        entry.pack(side="left", padx=20)
        entry.focus_set()
        pad = tk.Frame(self.body, bg=BG)
        pad.pack(side="left")
        for n in range(10):
            tk.Button(pad, text=str(n), width=3, command=lambda n=n: var.set(var.get() + str(n))
                      ).grid(row=n // 5, column=n % 5, padx=1, pady=1)
        bar = ScaledCanvas(self.body, self.k, width=220, height=18, bg="#222", highlightthickness=0)
        bar.pack(side="left", padx=20)
        fill = bar.create_rectangle(0, 0, 220, 18, fill="#69f0ae", outline="")
        state = {"left": limit * 10}

        def finish(ok):
            if token != self.token:
                return
            if ok:
                self.locks_done += 1
                gain = 25 + 5 * level
                self.score += gain
                self.hw("lock_unlocked", level=level + 1, points=gain)
                self.msg.config(text=f"Lock opened! +{gain} points. The next lock will be harder.")
                self.advance()
            else:
                self.time_remaining -= LOCK_PENALTY
                self.hw("lock_failed", level=level + 1)
                self.show_step()
                self.msg.config(text=f"Lock failed (code was {code})! -{LOCK_PENALTY}s. Try again.")
                self.check_time()

        def countdown():
            if token != self.token:
                return
            state["left"] -= 1
            bar.coords(fill, 0, 0, 220 * state["left"] / (limit * 10), 18)
            if state["left"] <= 0:
                finish(False)
            else:
                self.root.after(100, countdown)

        entry.bind("<Return>", lambda e: finish(var.get() == code))
        tk.Button(self.body, text="OK", width=5, command=lambda: finish(var.get() == code)).pack(side="left")
        self.root.after(100, countdown)

    # ---------- Hints and external commands ----------
    def use_hint(self):
        """Show the step's hint (from content.py) in exchange for time."""
        if not self.running or self.busy:
            return
        step = ROOMS[self.room_idx]["steps"][self.step_idx]
        self.time_remaining -= HINT_PENALTY
        self.hints_used += 1
        self.hw("hint_used")
        self.msg.config(text="Hint: " + step.get("hint", "Stay focused and say the digits out loud as they appear."))
        self.check_time()

    def skip_step(self):
        """Testing aid: skip the current step (F9 or POST /command skip)."""
        if self.running and not self.busy:
            self.hw("puzzle_skipped")
            if ROOMS[self.room_idx]["steps"][self.step_idx]["type"] == "lock":
                self.locks_done += 1
            self.advance()

    def poll_commands(self):
        """Run commands queued by the Pi API (hint / skip / start) every 200 ms."""
        while not self.bridge.commands.empty():
            cmd = self.bridge.commands.get()
            if cmd == "hint":
                self.use_hint()
            elif cmd == "skip":
                self.skip_step()
            elif cmd == "start" and not self.running:
                self.start_game()
        self.root.after(200, self.poll_commands)

    # ---------- Clock, header, LEDs and animation ----------
    def tick(self):
        """Runs every second: counts the game clock down."""
        if self.running:
            self.time_remaining -= 1
            if self.time_remaining == 60:
                self.hw("low_time")
            self.check_time()
            self.refresh_header()
        self.root.after(1000, self.tick)

    def check_time(self):
        """End the game when the clock hits zero (also called after any time penalty)."""
        if self.running and self.time_remaining <= 0:
            self.time_remaining = 0
            self.end_game(False, self.token)

    def refresh_header(self):
        """Update the timer and score labels."""
        t = max(0, self.time_remaining)
        self.timer_lbl.config(text=f"{t // 60:02}:{t % 60:02}",
                              fg="#ff5252" if t <= 60 else "#69f0ae")
        self.score_lbl.config(text=f"Score: {self.score}")

    def led_states(self):
        """LED colours for the Pi and the on-screen LEDs: per-room off/yellow(current)/green(done), plus the alarm."""
        states = {}
        for i in range(len(ROOMS)):
            if not self.running and self.finished_rooms == 0:
                states[f"room{i + 1}"] = "off"
            elif i < self.finished_rooms:
                states[f"room{i + 1}"] = "green"
            elif i == self.room_idx and self.running:
                states[f"room{i + 1}"] = "yellow"
            else:
                states[f"room{i + 1}"] = "off"
        states["alarm"] = "red" if self.running and self.time_remaining <= 60 else "off"
        return states

    def update_leds(self):
        """Paint the virtual LEDs in the header."""
        colors = {"off": "#555", "green": "#00e676", "yellow": "#ffd600", "red": "#ff1744"}
        for i, item in enumerate(self.leds):
            self.led_cv.itemconfig(item, fill=colors[self.led_states()[f"room{i + 1}"]])

    def hw(self, event, **data):
        """Send an event (with current LED states) to the hardware bridge and refresh virtual LEDs."""
        self.update_leds()
        self.bridge.send(event, leds=self.led_states(), **data)
        self.bridge.state = {
            "running": self.running, "room": self.room_idx + 1, "step": self.step_idx + 1,
            "score": self.score, "time_remaining": self.time_remaining,
            "locks_unlocked": self.locks_done, "leds": self.led_states(),
        }
        self.hw_lbl.config(text=f" HW event: {event} {data or ''}  |  {self.bridge.status}")

    def animate(self):
        """Runs 5x a second: bubbles, blinking lights, twinkling stars, flashing alarm LED."""
        self.blink_on = not self.blink_on
        for item in self.canvas.find_withtag("bubble"):
            x1, y1, x2, y2 = self.canvas.coords(item)
            dy = -4 if y1 > 105 else 80
            self.canvas.move(item, random.randint(-1, 1), dy)
        for item in self.canvas.find_withtag("blink"):
            self.canvas.itemconfig(item, fill=random.choice(["#00e676", "#ff1744", "#222"]))
        for item in self.canvas.find_withtag("star"):
            self.canvas.itemconfig(item, fill=random.choice(["white", "white", "#78909c"]))
        if self.running and self.time_remaining <= 60:
            self.led_cv.itemconfig(self.alarm_led, fill="#ff1744" if self.blink_on else "#333")
        else:
            self.led_cv.itemconfig(self.alarm_led, fill="#333")
        self.root.after(200, self.animate)

    # ---------- End of game ----------
    def end_game(self, won, token):
        """Show the win / time's-up screen with the final score (time bonus only if won)."""
        if not self.running:
            return
        self.running = False
        self.busy = False
        self.hint_btn.config(state="disabled")
        bonus = max(0, self.time_remaining) // 5 if won else 0
        total = self.score + bonus
        self.hw("game_won" if won else "game_over", score=total)
        self.clear_body()
        self.canvas.delete("all")
        SCENES["title"](self.canvas)
        self.canvas.create_rectangle(0, 120, W, 320, fill="#0b0e1f", outline="")
        headline = "YOU ESCAPED!" if won else "TIME'S UP!"
        self.canvas.create_text(W // 2, 170, text=headline, font=("Arial", 40, "bold"),
                                fill="#69f0ae" if won else "#ff5252")
        self.canvas.create_text(W // 2, 235, justify="center", fill=FG, font=("Arial", 16),
                                text=f"Score: {self.score}  +  time bonus: {bonus}  =  {total}\n"
                                     f"Locks opened: {self.locks_done}   Hints used: {self.hints_used}")
        self.msg.config(text="")
        tk.Button(self.body, text="Play Again", font=("Arial", 16, "bold"), bg="#43a047", fg="white",
                  command=self.show_title).pack(pady=30)
        self.update_leds()

    def on_close(self):
        """Stop the API server and close the window."""
        self.bridge.close()
        self.root.destroy()


def main():
    """Entry point: parse options, start the hardware bridge, open the game window."""
    ap = argparse.ArgumentParser(description="IoT Escape Room")
    ap.add_argument("--pi-url", help="Raspberry Pi API base URL, e.g. http://192.168.1.50:5001")
    ap.add_argument("--api-host", default="127.0.0.1", help="host for the game's own API (0.0.0.0 to expose to the Pi)")
    ap.add_argument("--api-port", type=int, default=5000)
    args = ap.parse_args()
    bridge = HardwareBridge(args.pi_url, args.api_host, args.api_port)
    root = tk.Tk()
    EscapeRoomGame(root, bridge)
    root.mainloop()


if __name__ == "__main__":
    main()
