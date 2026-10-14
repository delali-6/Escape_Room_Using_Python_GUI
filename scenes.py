"""Minecraft-style scenes built from a 48x16 grid of 20px blocks.

Tags used by the game: hs_0/hs_1 (clickable), doorgap/doorpanel (door animation),
bubble (rising), blink / star (flicker), player (Steve sprite).
"""
import random

# ---------- Grid size: 1 block = B pixels; the floor starts at row FLOOR ----------
B = 20
COLS, ROWS, FLOOR = 48, 16, 12
W, H = COLS * B, ROWS * B

# ---------- Block palettes: each block picks a random colour from its list for a textured look ----------
STONE = ["#7f7f7f", "#8a8a8a", "#757575"]
STONEBRICK = ["#6b6b6b", "#757575", "#636363"]
QUARTZ = ["#ece6df", "#e4ded6", "#f2ede7"]
PLANKS = ["#b8945f", "#a98550", "#bd9a64"]
DARK_OAK = ["#4a3621", "#52391f", "#45301c"]
FLOORWOOD = ["#9c7a4d", "#a8835a", "#936f45"]
IRON = ["#d8d8d8", "#cfcfcf", "#c4c4c4"]
DEEPSLATE = ["#3c3c44", "#45454d", "#36363e"]
BOOKS = ["#8e2c2c", "#2c4a8e", "#2c7a3c", "#7a5a2c", "#6a2c8e", "#c9a227"]
WOOL = ["#e53935", "#fb8c00", "#fdd835", "#43a047", "#1e88e5", "#8e24aa", "#f5f5f5"]
DIRT = ["#8b5a2b", "#7d4f26", "#95623a"]
GRASS = ["#5ea84a", "#69b553", "#559a42"]

_rng = random.Random()  # re-seeded per scene so each room always looks the same


# ---------- Building helpers: use these to build or edit rooms ----------
def darker(color, f):
    """Return a darker version of a #rrggbb colour (f<1), used for block outlines and speckles."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


def block(c, col, row, color, tags=(), speckle=True):
    """Draw one block at grid position (col, row); tags make it clickable (hs_0/hs_1) or animated."""
    x, y = col * B, row * B
    c.create_rectangle(x, y, x + B, y + B, fill=color, outline=darker(color, 0.75), tags=tags)
    if speckle and _rng.random() < 0.6:
        sx, sy = x + _rng.randint(2, B - 8), y + _rng.randint(2, B - 8)
        c.create_rectangle(sx, sy, sx + 6, sy + 6, fill=darker(color, 0.88), outline="", tags=tags)


def fill(c, c0, r0, c1, r1, palette, tags=(), speckle=True):
    """Fill the grid area cols c0..c1-1, rows r0..r1-1 with random blocks from a palette."""
    for r in range(r0, r1):
        for col in range(c0, c1):
            block(c, col, r, _rng.choice(palette), tags, speckle)


def blob(c, col, row, color, tags=()):
    """3x3 round-ish cluster (corners removed), like a Minecraft moon/planet."""
    for dr in range(3):
        for dc in range(3):
            if (dr, dc) not in ((0, 0), (0, 2), (2, 0), (2, 2)):
                block(c, col + dc, row + dr, color, tags, speckle=False)


def draw_door(c, x1, y1, x2, y2):
    """Oak-plank door; 'doorpanel' swings open (EscapeRoom.open_door) revealing 'doorgap'."""
    c.create_rectangle(x1 - 6, y1 - 6, x2 + 6, y2, fill="#2b2b2b", outline="")
    c.create_rectangle(x1, y1, x2, y2, fill="#fff3b0", outline="", tags="doorgap")
    rng = random.Random(x1)
    cell = 10
    for gy in range(y1, y2, cell):
        for gx in range(x1, x2, cell):
            row = (gy - y1) // cell
            window = row in (1, 2) and gx > x1 and gx + cell < x2
            c.create_rectangle(gx, gy, min(gx + cell, x2), min(gy + cell, y2),
                               fill="#6fa8dc" if window else rng.choice(["#a1783f", "#9c7239", "#b08a4c", "#8f6a35"]),
                               outline="#6b4a22", tags="doorpanel")
    c.create_oval(x2 - 12, (y1 + y2) // 2, x2 - 5, (y1 + y2) // 2 + 7, fill="#222", outline="", tags="doorpanel")


def door(c, col):
    """Place the room's exit door (2 blocks wide, 4 tall) standing on the floor at grid column col."""
    draw_door(c, col * B, (FLOOR - 4) * B, col * B + 2 * B, FLOOR * B)


# ---------- Player character (Steve) ----------
U = 2  # pixel size of the Steve sprite


def draw_player(c, x, feet):
    """Steve, front view. Legs are tagged legL/legR so the game can swing them while walking."""
    top = feet - 32 * U
    skin, shirt, pants = "#c68642", "#00a8a8", "#3c44aa"
    parts = [
        (4, 0, 8, 8, skin, ""), (4, 0, 8, 3, "#4b2e16", ""),
        (5, 5, 2, 1, "#ffffff", ""), (6, 5, 1, 1, "#3a2a8a", ""),
        (9, 5, 2, 1, "#ffffff", ""), (9, 5, 1, 1, "#3a2a8a", ""), (6, 7, 4, 1, "#7a4a21", ""),
        (4, 8, 8, 12, shirt, ""),
        (0, 8, 4, 4, shirt, ""), (0, 12, 4, 8, skin, ""),
        (12, 8, 4, 4, shirt, ""), (12, 12, 4, 8, skin, ""),
        (4, 20, 4, 9, pants, "legL"), (4, 29, 4, 3, "#6b6b6b", "legL"),
        (8, 20, 4, 9, pants, "legR"), (8, 29, 4, 3, "#6b6b6b", "legR"),
    ]
    for ux, uy, w, h, color, tag in parts:
        c.create_rectangle(x + ux * U, top + uy * U, x + (ux + w) * U, top + (uy + h) * U,
                           fill=color, outline="", tags=("player", tag) if tag else "player")


# ---------- Rooms: one function per scene, referenced by "scene" in content.py ----------
def lab(c):
    """Room 1: quartz laboratory with periodic-table poster, counter, microscope and potions."""
    _rng.seed(1)
    fill(c, 0, 0, COLS, FLOOR, QUARTZ)
    fill(c, 0, FLOOR, COLS, ROWS, STONEBRICK)
    for col in (8, 20, 32):
        fill(c, col, 0, col + 3, 1, ["#fff6b0"], speckle=False)  # glowstone lamps
    fill(c, 17, 2, 27, 6, ["#bfe7f5", "#cdeefa"], speckle=False)
    fill(c, 22, 2, 23, 6, IRON)
    fill(c, 3, 2, 12, 6, WOOL, tags="hs_0", speckle=False)
    c.create_text(7.5 * B, 6.7 * B, text="PERIODIC TABLE", font=("Courier", 10, "bold"), fill="#333")
    fill(c, 14, 9, 36, 10, DARK_OAK)
    fill(c, 14, 10, 36, FLOOR, PLANKS)
    fill(c, 20, 8, 22, 9, IRON)  # microscope
    fill(c, 20, 6, 21, 8, IRON)
    block(c, 21, 6, "#222222", speckle=False)
    fill(c, 25, 7, 27, 9, PLANKS, tags="hs_1")
    c.create_text(26 * B, 8 * B, text="Au", font=("Courier", 14, "bold"), fill="#ffd54f", tags="hs_1")
    for col, liquid, tag in ((29, "#66bb6a", "hs_1"), (31, "#ef5350", ""), (33, "#ffd54f", "")):
        block(c, col, 7, "#cdeefa", tag, speckle=False)
        block(c, col, 8, liquid, tag, speckle=False)
        for k in range(2):
            c.create_oval(col * B + 5 + k * 6, 165 - k * 20, col * B + 11 + k * 6, 171 - k * 20,
                          fill="white", outline="", tags=("bubble", tag) if tag else "bubble")
    door(c, 43)


def library(c):
    """Room 2: oak library with bookshelves, window, lectern book (hs_0) and globe (hs_1)."""
    _rng.seed(2)
    fill(c, 0, 0, COLS, FLOOR, DARK_OAK)
    fill(c, 0, FLOOR, COLS, ROWS, FLOORWOOD)
    for c0 in (2, 15):
        for r in range(2, 12):
            if (r - 2) % 3 == 2:
                fill(c, c0, r, c0 + 11, r + 1, PLANKS)
            else:
                fill(c, c0, r, c0 + 11, r + 1, BOOKS, speckle=False)
        fill(c, c0 - 1, 2, c0, 12, PLANKS)
        fill(c, c0 + 11, 2, c0 + 12, 12, PLANKS)
    fill(c, 28, 2, 34, 7, ["#0d1b3e"], speckle=False)
    block(c, 30, 3, "#fff59d", speckle=False)
    fill(c, 28, 10, 34, 11, PLANKS)
    block(c, 28, 11, DARK_OAK[0])
    block(c, 33, 11, DARK_OAK[0])
    fill(c, 30, 9, 32, 10, ["#f5f0e0"], tags="hs_0", speckle=False)
    c.create_text(31 * B, 9.5 * B, text="BOOK", font=("Courier", 9, "bold"), fill="#555", tags="hs_0")
    fill(c, 37, 10, 39, FLOOR, PLANKS)
    for dc, dr, col in ((0, 0, "#1e88e5"), (1, 0, "#43a047"), (0, 1, "#43a047"), (1, 1, "#1e88e5")):
        block(c, 37 + dc, 8 + dr, col, "hs_1", speckle=False)
    door(c, 43)


def observatory(c):
    """Room 3: night-sky observatory with star chart (hs_0), telescope and note (hs_1)."""
    _rng.seed(3)
    fill(c, 0, 0, COLS, FLOOR, ["#0b1030", "#0e1536", "#0a0e2a"], speckle=False)
    for _ in range(45):
        x, y = _rng.randint(30, W - 30), _rng.randint(10, 200)
        c.create_rectangle(x, y, x + 4, y + 4, fill="white", outline="", tags="star")
    fill(c, 0, FLOOR, COLS, ROWS, ["#1b1230", "#221740", "#150e28"])
    fill(c, 0, 0, 2, FLOOR, STONEBRICK)
    fill(c, 46, 0, COLS, FLOOR, STONEBRICK)
    fill(c, 0, 0, COLS, 1, STONEBRICK)
    blob(c, 38, 2, "#fff4c4")
    blob(c, 8, 3, "#d84315")
    fill(c, 4, 7, 9, 11, ["#e0d3a8"], tags="hs_0", speckle=False)
    for col, row in ((5, 8), (7, 8), (6, 9), (5, 10), (8, 10)):
        block(c, col, row, "#d84315", "hs_0", speckle=False)
    for col in (22, 24):
        fill(c, col, 10, col + 1, FLOOR, IRON)
    for col, row in ((22, 9), (23, 9), (24, 8), (25, 8), (26, 7), (27, 7)):
        block(c, col, row, IRON[0], "hs_1")
    block(c, 28, 6, "#6fa8dc", "hs_1", speckle=False)
    fill(c, 30, 9, 33, 11, PLANKS, tags="hs_1")
    c.create_text(31.5 * B, 10 * B, text="8 min?", font=("Courier", 10, "bold"), tags="hs_1")
    door(c, 43)


def control(c):
    """Room 4: server/control room with racks, monitor (hs_0) and Raspberry Pi (hs_1)."""
    _rng.seed(4)
    fill(c, 0, 0, COLS, FLOOR, DEEPSLATE)
    fill(c, 0, FLOOR, COLS, ROWS, ["#2a2a30", "#303038"])
    for c0 in (2, 6):
        fill(c, c0, 2, c0 + 3, FLOOR, ["#16161a"])
        for r in range(3, FLOOR, 2):
            for k in range(3):
                c.create_oval((c0 + k) * B + 5, r * B + 5, (c0 + k) * B + 13, r * B + 13,
                              fill="#00e676", outline="", tags="blink")
    fill(c, 14, 3, 23, 8, IRON)
    c.create_rectangle(14 * B + 10, 3 * B + 10, 23 * B - 10, 8 * B - 10, fill="#000", outline="", tags="hs_0")
    for i, txt in enumerate(["01100110", "10101101", "101 = 5", "11001010"]):
        c.create_text(15 * B, 3.8 * B + i * 18, text=txt, anchor="w", fill="#00e676",
                      font=("Courier", 11, "bold"), tags="hs_0")
    fill(c, 12, 9, 37, 10, DARK_OAK)
    fill(c, 12, 10, 13, FLOOR, DARK_OAK)
    fill(c, 36, 10, 37, FLOOR, DARK_OAK)
    fill(c, 28, 8, 31, 9, ["#2e7d32"], tags="hs_1", speckle=False)
    c.create_text(29.5 * B, 8.5 * B, text="CPU", font=("Courier", 10, "bold"), fill="#fdd835", tags="hs_1")
    c.create_oval(30 * B + 2, 8 * B + 2, 30 * B + 9, 8 * B + 9, fill="#ff1744", outline="", tags="blink")
    fill(c, 42, 6, 46, 7, ["#17dd62", "#13c455"], speckle=False)
    c.create_text(44 * B, 6.5 * B, text="EXIT", font=("Courier", 11, "bold"), fill="#052")
    door(c, 43)


def title(c):
    """Title / end-screen backdrop (no gameplay objects)."""
    _rng.seed(5)
    fill(c, 0, 0, COLS, 11, ["#7ec8f5", "#87cefa", "#76c1ee"], speckle=False)
    fill(c, 39, 1, 42, 4, ["#ffe066"], speckle=False)
    for col, row in ((4, 2), (5, 2), (6, 2), (5, 1), (20, 4), (21, 4), (22, 4), (21, 3), (30, 6), (31, 6), (32, 6)):
        block(c, col, row, "#ffffff", speckle=False)
    fill(c, 0, 11, COLS, 12, GRASS)
    fill(c, 0, 12, COLS, ROWS, DIRT)
    draw_door(c, 22 * B, 7 * B, 24 * B + 20, 11 * B)
    draw_player(c, 17 * B, 11 * B + 4)
    c.create_text(W // 2 + 3, 63, text="IoT ESCAPE ROOM", fill="#3a3a3a", font=("Courier", 44, "bold"))
    c.create_text(W // 2, 60, text="IoT ESCAPE ROOM", fill="#ffd54f", font=("Courier", 44, "bold"))
    c.create_text(W // 2, 105, text="Learn. Solve. Unlock. Escape.", fill="#ffffff", font=("Courier", 16, "bold"))


# To add a room: write a scene function above and register it here.
SCENES = {"lab": lab, "library": library, "observatory": observatory, "control": control, "title": title}
