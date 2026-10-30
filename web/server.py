"""Web server for the browser version of the game (standard library only).

Owner: Role 4: Game Logic & Integration.

Serves the frontend in web/static and the JSON API in web/api.py.
Run from the project root, then open http://127.0.0.1:8000 :

    python web/server.py
    python web/server.py --port 8080 --open

Press Ctrl+C to stop the server.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

# Allow "python web/server.py" from the project root to import src and web.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from web import api  # noqa: E402

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_BODY = 16 * 1024
GAME_ROUTE = re.compile(r"^/api/games/([A-Za-z0-9_-]+)/(move|hint|restart|solve|compare)$")

STORE = api.GameStore()


class Handler(BaseHTTPRequestHandler):
    """Routes static files and /api/* requests."""

    server_version = "MazeSolver/1.0"

    def do_GET(self) -> None:
        """Route a GET request."""
        url = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        if url.path.startswith("/api/"):
            self.dispatch("GET", url.path, query)
        else:
            self.send_static(url.path)

    def do_POST(self) -> None:
        """Route a POST request with an optional JSON body."""
        url = urlparse(self.path)
        try:
            body = self.read_json()
        except api.ApiError as err:
            self.send_json(err.status, {"error": str(err)})
            return
        self.dispatch("POST", url.path, body)

    def dispatch(self, method: str, path: str, params: dict[str, Any]) -> None:
        """Call the matching api function and send its result or error as JSON."""
        try:
            self.send_json(200, self.route(method, path, params))
        except api.ApiError as err:
            self.send_json(err.status, {"error": str(err)})
        except Exception as err:  # noqa: BLE001  (report, keep serving)
            self.log_error("internal error: %r", err)
            self.send_json(500, {"error": "internal server error"})

    def route(self, method: str, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """Map (method, path) to an api function."""
        if path == "/api/games" and method == "POST":
            return api.create_game(STORE, params)
        if path == "/api/demo" and method == "GET":
            return api.demo(params)
        if path == "/api/spanning-trees" and method == "GET":
            return api.spanning_trees(params)
        match = GAME_ROUTE.match(path)
        if match:
            game_id, action = match.groups()
            if method == "POST" and action == "move":
                return api.move(STORE, game_id, params)
            if method == "POST" and action == "hint":
                return api.hint(STORE, game_id)
            if method == "POST" and action == "restart":
                return api.restart(STORE, game_id)
            if method == "GET" and action == "solve":
                return api.solve(STORE, game_id, params.get("algorithm", "bfs"))
            if method == "GET" and action == "compare":
                return api.compare(STORE, game_id)
        raise api.ApiError("not found", 404)

    def read_json(self) -> dict[str, Any]:
        """Read and decode the request body (empty body means {})."""
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise api.ApiError("request body too large", 413)
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise api.ApiError("body must be JSON") from None
        if not isinstance(data, dict):
            raise api.ApiError("body must be a JSON object")
        return data

    def send_static(self, path: str) -> None:
        """Serve a file from web/static, refusing anything outside it."""
        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (STATIC_DIR / relative).resolve()
        if not target.is_relative_to(STATIC_DIR) or not target.is_file():
            self.send_json(404, {"error": "not found"})
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type.endswith("javascript"):
            content_type += "; charset=utf-8"
        self.send_body(200, content_type, target.read_bytes())

    def send_json(self, status: int, data: dict[str, Any]) -> None:
        """Send a JSON response."""
        self.send_body(status, "application/json", json.dumps(data).encode("utf-8"))

    def send_body(self, status: int, content_type: str, body: bytes) -> None:
        """Send a complete response with no caching (the files change during development)."""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Log API calls only, to keep the console readable."""
        if self.path.startswith("/api/"):
            super().log_message(format, *args)


def main() -> None:
    """Parse arguments and serve until Ctrl+C."""
    parser = argparse.ArgumentParser(description="Serve the maze game in the browser.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--open", action="store_true", help="open the page in the default browser")
    args = parser.parse_args()
    mimetypes.add_type("text/javascript", ".js")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    print(f"Maze Solver running at {url}  (Ctrl+C to stop)")
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
