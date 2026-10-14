# IoT Escape Room

A single-player, Minecraft-style escape room game that runs on your computer. You are locked in a series of rooms (a laboratory, a library, an observatory and a control room). To escape, you answer riddles, answer general-knowledge questions, and crack number locks, all before the 5-minute timer runs out.

Later on, the game can be connected to a Raspberry Pi so that real LEDs and other electronics react to what you do. You do **not** need any of that to play.

---

## What you need

1. A Windows, Mac or Linux computer.
2. **Python 3.8 or newer** (free). Nothing else: no extra packages to install.

### Installing Python
- **Windows:** Download it from https://www.python.org/downloads/ and run the installer. **Tick the box "Add Python to PATH"** on the first screen, then click "Install Now".
- **Mac:** Download the installer from https://www.python.org/downloads/ and open it.
- **Linux:** Python is usually already installed. If the game later complains about `tkinter`, install it with `sudo apt install python3-tk`.

To check it worked, open a terminal (on Windows: press the Windows key, type `cmd`, press Enter) and type `python --version`. You should see a version number. (On Mac/Linux you may need to type `python3` instead of `python` throughout this guide.)

---

## How to run the game

1. Download or copy this project folder to your computer. If it came as a ZIP file, right-click it and choose "Extract All".
2. Open a terminal **inside the project folder**. On Windows: open the folder in File Explorer, click the address bar, type `cmd` and press Enter.
3. Type the following and press Enter:

```
python EscapeRoom.py
```

The game opens in full screen. Click **START ESCAPE** to begin.

**Leaving full screen:** press **Esc**. Press **F11** to go full screen again. To quit, close the window (or press Esc first, then close it).

---

## How to play

- You have **5 minutes** in total. The timer is at the top of the screen.
- Your character (a Minecraft-style person) stands in a room with a door. **Every time you solve something, he takes two steps toward the door.** Finish the room's puzzles and the door opens.
- Each room has three kinds of challenge:
  - **Riddles:** type your answer and press Enter.
  - **Quiz questions:** click the correct answer.
  - **Speed locks:** a secret code flashes on screen one digit at a time. Memorise it, then type it (using the keyboard or on-screen keypad) before the bar runs out.
- **Click objects in the room** (posters, bottles, books, a telescope and so on). They give you clues that help with the questions.
- Every lock you open makes the next one **harder**: more digits, shown for less time, with less time to type them.
- Penalties: a wrong answer costs 5 seconds, a failed lock costs 10 seconds, and using the **Hint** button costs 15 seconds.
- Escape all four rooms before time runs out and you win. Finishing with time to spare earns bonus points.
- The bar above the bottom slots shows your overall progress, and you collect one item per room.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Python is not installed, or "Add Python to PATH" was not ticked. Re-run the installer and tick it. |
| `No module named tkinter` | Linux only: `sudo apt install python3-tk`. |
| Nothing happens / window is hidden | Press Esc to leave full screen, or check your taskbar. |
| The game does not fill my screen | The game scales to fit your screen's height, so very wide monitors will show dark borders at the sides. |

---

## For testers and developers

Everything below is optional.

### Files
| File | Purpose |
|---|---|
| `EscapeRoom.py` | The game itself (window, timer, puzzles, locks, animations). |
| `content.py` | **Rooms, riddles and quiz questions.** Edit this to add more. |
| `scenes.py` | The block-built pictures of each room and the player character. |
| `hardware.py` | The local API used to talk to a Raspberry Pi. |
| `mock_pi_server.py` | A pretend Raspberry Pi for testing without hardware. |

### Changing the game
- **Total time:** change `GAME_SECONDS` near the top of `EscapeRoom.py` (currently 300 seconds).
- **Add a riddle or question:** add an entry to a room's `steps` list in `content.py`. Copy an existing one and change the text.
- **Skip a step while testing:** press **F9**.

### Raspberry Pi / LED connection
The game sends events (room entered, puzzle solved, lock opened, game won and so on) to a Raspberry Pi, and shows virtual LEDs at the top of the screen so you can test without hardware.

Try it with the pretend Pi:
```
python mock_pi_server.py
```
then, in a second terminal:
```
python EscapeRoom.py --pi-url http://127.0.0.1:5001
```

- **Game to Pi:** the game sends `POST <pi-url>/event` with JSON such as `{"event": "lock_unlocked", "data": {"leds": {"room1": "green", "alarm": "off"}}}`. Events: `game_start`, `room_enter`, `puzzle_solved`, `puzzle_failed`, `lock_unlocked`, `lock_failed`, `hint_used`, `puzzle_skipped`, `room_complete`, `low_time`, `game_won`, `game_over`.
- **Pi to game:** the game listens on `127.0.0.1:5000`. `GET /state` returns the current state, and `POST /command` with `{"cmd": "hint"}`, `{"cmd": "skip"}` or `{"cmd": "start"}` controls it. To let a Pi on your network reach it, start the game with `--api-host 0.0.0.0` (trusted networks only: there is no password).
