"""Bridge between the game and a Raspberry Pi (or any device) over a local HTTP API.

Outbound: game events are POSTed as JSON to  <pi_url>/event  (no-op when pi_url is None).
Inbound : the game hosts a small API so a Pi can read state or send commands:
    GET  /state                      -> current game state
    POST /command {"cmd": "hint"}    -> cmd is one of COMMANDS
"""
import json
import queue
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import URLError
from urllib.parse import urlparse

COMMANDS = {"hint", "skip", "start"}  # commands a Pi is allowed to send to the game


class HardwareBridge:
    """Two-way link between the game and a Pi: queued outbound events plus a small inbound HTTP API."""

    def __init__(self, pi_url=None, host="127.0.0.1", port=5000):
        if pi_url and urlparse(pi_url).scheme not in ("http", "https"):
            raise ValueError("pi_url must start with http:// or https://")
        self.pi_url = pi_url.rstrip("/") if pi_url else None
        self.commands = queue.Queue()
        self.state = {}
        self.status = f"Pi: {self.pi_url}" if self.pi_url else "simulated (no Pi connected)"
        self._out = queue.Queue()
        threading.Thread(target=self._sender, daemon=True).start()
        self.server = None
        self._start_server(host, port)

    # ---------- Outbound: game -> Pi ----------
    def send(self, event, **data):
        """Queue an event for the Pi; never blocks the GUI."""
        self._out.put({"event": event, "data": data, "ts": time.time()})

    def _sender(self):
        """Background thread: POST queued events to the Pi, recording whether it is reachable."""
        while True:
            payload = self._out.get()
            if not self.pi_url:
                continue
            req = urllib.request.Request(
                self.pi_url + "/event",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=2):
                    self.status = f"Pi connected: {self.pi_url}"
            except (URLError, OSError):
                self.status = f"Pi unreachable: {self.pi_url}"

    # ---------- Inbound: Pi -> game (GET /state, POST /command) ----------
    def _start_server(self, host, port):
        """Start the local API server in a background thread; commands land in self.commands."""
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def _reply(self, code, body):
                raw = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                if self.path == "/state":
                    self._reply(200, bridge.state)
                else:
                    self._reply(404, {"error": "not found"})

            def do_POST(self):
                if self.path != "/command":
                    return self._reply(404, {"error": "not found"})
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    if not 0 < length <= 1024:
                        raise ValueError
                    cmd = json.loads(self.rfile.read(length)).get("cmd")
                except (ValueError, AttributeError):
                    return self._reply(400, {"error": "invalid JSON"})
                if cmd not in COMMANDS:
                    return self._reply(400, {"error": f"cmd must be one of {sorted(COMMANDS)}"})
                bridge.commands.put(cmd)
                self._reply(200, {"ok": True})

            def log_message(self, *args):
                pass

        try:
            self.server = ThreadingHTTPServer((host, port), Handler)
        except OSError:
            self.status += f" | API port {port} busy"
            return
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.status += f" | API on {host}:{port}"

    def close(self):
        """Stop the API server."""
        if self.server:
            self.server.shutdown()
