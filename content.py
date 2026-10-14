"""Game content. Edit here to add rooms, riddles and questions.

Step types:
  riddle: prompt, answers (accepted lowercase answers), hint, points
  quiz  : prompt, options, answer (must match an option), hint, points
  lock  : speed lock; difficulty rises with every lock opened
Each room has two clickable hotspots (scene objects) that reveal clues.
"""

ROOMS = [
    {
        "name": "The Laboratory",
        "scene": "lab",
        "item": ("Beaker", "#66bb6a"),
        "intro": "You wake up in a locked science lab. Click objects to examine them, then solve the puzzles.",
        "hotspots": [
            "The periodic table poster: the first cell reads 'H' - atomic number 1, the lightest element.",
            "A bubbling flask is labelled 'Au - Aurum'. Aurum is Latin for gold.",
        ],
        "steps": [
            {"type": "riddle", "points": 10,
             "prompt": "I am the lightest element in the universe, and I make up water along with oxygen. What am I?",
             "answers": ["hydrogen"], "hint": "Atomic number 1. Symbol H."},
            {"type": "quiz", "points": 10,
             "prompt": "What is the chemical symbol for gold?",
             "options": ["Au", "Ag", "Gd", "Go"], "answer": "Au", "hint": "Look at the flask."},
            {"type": "lock"},
        ],
    },
    {
        "name": "The Library",
        "scene": "library",
        "item": ("Book", "#c62828"),
        "intro": "The lab door opens onto an old library. The shelves hold more than books.",
        "hotspots": [
            "A thick volume of plays lies open: 'Romeo and Juliet' by William Shakespeare.",
            "The globe has a pin in the Sahara - the largest hot desert, in northern Africa.",
        ],
        "steps": [
            {"type": "riddle", "points": 10,
             "prompt": "The more of me there is, the less you see. What am I?",
             "answers": ["darkness", "dark"], "hint": "Turn off the lamp."},
            {"type": "quiz", "points": 10,
             "prompt": "Who wrote 'Romeo and Juliet'?",
             "options": ["Charles Dickens", "William Shakespeare", "Mark Twain", "Jane Austen"],
             "answer": "William Shakespeare", "hint": "Check the open book."},
            {"type": "quiz", "points": 10,
             "prompt": "On which continent is the Sahara Desert?",
             "options": ["Asia", "Australia", "Africa", "South America"],
             "answer": "Africa", "hint": "Check the globe."},
            {"type": "lock"},
        ],
    },
    {
        "name": "The Observatory",
        "scene": "observatory",
        "item": ("Star", "#fdd835"),
        "intro": "A spiral stair leads up to a dome under the night sky.",
        "hotspots": [
            "A star chart: Mars glows red because of iron oxide (rust) on its surface.",
            "A note beside the telescope: 'Sunlight takes about 8 minutes to reach Earth.'",
        ],
        "steps": [
            {"type": "riddle", "points": 10,
             "prompt": "I have cities but no houses, mountains but no land, and water but no fish. What am I?",
             "answers": ["map", "a map"], "hint": "You can fold me."},
            {"type": "quiz", "points": 10,
             "prompt": "Which planet is known as the Red Planet?",
             "options": ["Venus", "Mars", "Jupiter", "Mercury"], "answer": "Mars",
             "hint": "Iron oxide gives it its colour."},
            {"type": "quiz", "points": 10,
             "prompt": "About how long does sunlight take to reach Earth?",
             "options": ["8 seconds", "8 minutes", "8 hours", "8 days"], "answer": "8 minutes",
             "hint": "Read the telescope note."},
            {"type": "lock"},
        ],
    },
    {
        "name": "The Control Room",
        "scene": "control",
        "item": ("Chip", "#1e88e5"),
        "intro": "The final room hums with computers. Two locks guard the exit.",
        "hotspots": [
            "A monitor shows binary: 101 = 1x4 + 0x2 + 1x1.",
            "A sticker on the case: CPU - the 'brain' of a computer.",
        ],
        "steps": [
            {"type": "riddle", "points": 10,
             "prompt": "I have keys but open no locks, and a space but no room. What am I?",
             "answers": ["keyboard", "a keyboard"], "hint": "You are probably typing on one."},
            {"type": "quiz", "points": 10,
             "prompt": "What does CPU stand for?",
             "options": ["Central Processing Unit", "Computer Power Utility",
                         "Core Program Updater", "Central Peripheral Unit"],
             "answer": "Central Processing Unit", "hint": "Read the sticker."},
            {"type": "quiz", "points": 10,
             "prompt": "What is the binary number 101 in decimal?",
             "options": ["3", "4", "5", "6"], "answer": "5", "hint": "4 + 0 + 1."},
            {"type": "lock"},
            {"type": "lock"},
        ],
    },
]
