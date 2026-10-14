"""Stand-in for the Raspberry Pi: receives game events and prints what the LEDs would do.

Run:   python mock_pi_server.py [--port 5001]
Game:  python EscapeRoom.py --pi-url http://127.0.0.1:5001

On a real Pi, replace the print in `apply_leds` with gpiozero LED/Buzzer calls.
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


def apply_leds(leds):
    for name, state in leds.items():
        print(f"  LED {name:<7} -> {state}")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/event":
            self.send_response(404)
            self.end_headers()
            return
        length = min(int(self.headers.get("Content-Length", 0)), 4096)
        try:
            msg = json.loads(self.rfile.read(length))
        except ValueError:
            self.send_response(400)
            self.end_headers()
            return
        print(f"[event] {msg.get('event')} {msg.get('data')}")
        leds = msg.get("data", {}).get("leds")
        if isinstance(leds, dict):
            apply_leds(leds)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5001)
    args = ap.parse_args()
    print(f"Mock Pi listening on {args.host}:{args.port}")
    HTTPServer((args.host, args.port), Handler).serve_forever()
