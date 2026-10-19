"""Local web viewer for the maze generators (standard library only, no pygame).

Owner: Role 1 — Graph & Maze Generation.

Every maze shown is produced by the real functions in src/maze/generator.py,
so this is a visual check of the module before the pygame UI exists.
Run from the project root, then open http://127.0.0.1:8000 :

    python scripts/maze_server.py
    python scripts/maze_server.py --port 8080

Press Ctrl+C to stop the server.
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Allow "python scripts/maze_server.py" from the project root to import src.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo_generator import GENERATORS, count_dead_ends, count_reachable  # noqa: E402
from src.maze.generator import add_braids, pick_start_and_goal  # noqa: E402
from src.maze.graph import MazeGraph  # noqa: E402

MAX_SIZE = 60          # largest rows/cols the viewer will generate
CHECK_SEEDS = 100      # mazes per algorithm in the "Run checks" test


def maze_to_json(maze: MazeGraph, algorithm: str, seed: int, braid: float, mode: str) -> dict:
    """Describe a maze and its statistics as JSON-ready data for the browser.

    Args:
        maze: The generated maze.
        algorithm: Name of the generator used.
        seed: Seed used.
        braid: Braid factor used.
        mode: Start/goal mode used.

    Returns:
        A dict with the grid size, open passages, start/goal, dead ends and stats.

    Concept: Graph Theory — exports E as "open right" / "open down" flags per cell.
    Complexity: O(|V|).
    """
    rows, cols = maze.rows, maze.cols
    start, goal = pick_start_and_goal(maze, mode=mode)
    vertices, edges = maze.vertex_count(), maze.edge_count()
    connected = count_reachable(maze, (0, 0)) == vertices
    return {
        "rows": rows,
        "cols": cols,
        "algorithm": algorithm,
        "seed": seed,
        "braid": braid,
        "mode": mode,
        "open_right": [[maze.has_edge((r, c), (r, c + 1)) for c in range(cols)] for r in range(rows)],
        "open_down": [[maze.has_edge((r, c), (r + 1, c)) for c in range(cols)] for r in range(rows)],
        "start": start,
        "goal": goal,
        "dead_ends": [cell for cell, nbrs in maze.to_dict().items() if len(nbrs) == 1],
        "stats": {
            "vertices": vertices,
            "edges": edges,
            "connected": connected,
            "is_tree": connected and edges == vertices - 1,
            "dead_end_count": count_dead_ends(maze),
        },
    }


def run_checks() -> dict:
    """Generate many mazes with every algorithm and verify the spanning-tree properties.

    Returns:
        Per-algorithm counts of mazes checked and passed, plus seed-reproducibility results.

    Concept: Trees — a maze is a spanning tree iff it is connected and |E| = |V| - 1.
    Complexity: O(k * |V|) for k mazes.
    """
    results = {}
    sizes = [(1, 1), (1, 9), (9, 1), (7, 13), (25, 25)]
    for name, generate in GENERATORS.items():
        checked = passed = 0
        for rows, cols in sizes:
            for seed in range(CHECK_SEEDS // len(sizes)):
                maze = generate(rows, cols, seed)
                checked += 1
                vertices = maze.vertex_count()
                if count_reachable(maze, (0, 0)) == vertices and maze.edge_count() == vertices - 1:
                    passed += 1
        reproducible = generate(15, 15, 123).to_dict() == generate(15, 15, 123).to_dict()
        seeds_differ = generate(15, 15, 1).to_dict() != generate(15, 15, 2).to_dict()
        results[name] = {
            "checked": checked,
            "trees": passed,
            "same_seed_same_maze": reproducible,
            "different_seeds_differ": seeds_differ,
        }
    return results


class MazeHandler(BaseHTTPRequestHandler):
    """Serves the viewer page at "/" and JSON at "/api/maze" and "/api/check"."""

    def do_GET(self) -> None:
        """Route a GET request."""
        url = urlparse(self.path)
        if url.path == "/":
            self.send_body(200, "text/html; charset=utf-8", PAGE.encode("utf-8"))
        elif url.path == "/api/maze":
            self.handle_maze(parse_qs(url.query))
        elif url.path == "/api/check":
            self.send_json(200, run_checks())
        else:
            self.send_json(404, {"error": "not found"})

    def handle_maze(self, query: dict[str, list[str]]) -> None:
        """Generate one maze from the query parameters and send it as JSON."""
        def param(name: str, default: str) -> str:
            return query.get(name, [default])[0]

        try:
            rows = int(param("rows", "15"))
            cols = int(param("cols", "20"))
            seed = int(param("seed", "42"))
            braid = float(param("braid", "0"))
            algorithm = param("algorithm", "dfs")
            mode = param("mode", "corners")
            if not (1 <= rows <= MAX_SIZE and 1 <= cols <= MAX_SIZE):
                raise ValueError(f"rows and cols must be between 1 and {MAX_SIZE}")
            if algorithm not in GENERATORS:
                raise ValueError(f"unknown algorithm {algorithm!r}")
            maze = GENERATORS[algorithm](rows, cols, seed)
            add_braids(maze, braid, seed=seed)
            self.send_json(200, maze_to_json(maze, algorithm, seed, braid, mode))
        except ValueError as error:
            self.send_json(400, {"error": str(error)})

    def send_json(self, status: int, data: dict) -> None:
        """Send ``data`` as a JSON response."""
        self.send_body(status, "application/json", json.dumps(data).encode("utf-8"))

    def send_body(self, status: int, content_type: str, body: bytes) -> None:
        """Send a complete HTTP response."""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Keep the terminal quiet (no line per request)."""


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Maze Generator Viewer</title>
<style>
  :root {
    --bg: #f5f5f0; --panel: #ffffff; --text: #1e1e28; --muted: #6b6b78; --border: #d9d9d2;
    --wall: #1e1e28; --start: #2ecc71; --goal: #e74c3c; --dead: #f6d7a7; --accent: #3498db;
    --ok: #1e8f4e; --bad: #c0392b;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #16161c; --panel: #202029; --text: #ececf1; --muted: #9a9aa8; --border: #33333f;
      --wall: #ececf1; --dead: #6b4f22; --ok: #4cd987; --bad: #ff7a6b;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text);
         font: 15px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
  main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 48px; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .sub { color: var(--muted); margin: 0 0 20px; }
  .layout { display: grid; grid-template-columns: 260px 1fr; gap: 20px; align-items: start; }
  @media (max-width: 760px) { .layout { grid-template-columns: 1fr; } }
  .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
  label { display: block; font-size: 13px; color: var(--muted); margin: 10px 0 4px; }
  label:first-child { margin-top: 0; }
  input, select { width: 100%; padding: 7px 8px; border: 1px solid var(--border); border-radius: 6px;
                  background: var(--bg); color: var(--text); font: inherit; }
  .row { display: flex; gap: 8px; }
  .row > * { flex: 1; }
  button { width: 100%; margin-top: 12px; padding: 9px; border: 0; border-radius: 6px; cursor: pointer;
           background: var(--accent); color: #fff; font: inherit; font-weight: 600; }
  button.secondary { background: transparent; color: var(--text); border: 1px solid var(--border); }
  .check { display: flex; gap: 8px; align-items: center; margin-top: 12px; font-size: 14px; }
  .check input { width: auto; }
  .stage { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
  canvas { display: block; max-width: 100%; height: auto; margin: 0 auto; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin-top: 16px; }
  .stat { border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; }
  .stat b { display: block; font-size: 18px; font-variant-numeric: tabular-nums; }
  .stat span { font-size: 12px; color: var(--muted); }
  .ok { color: var(--ok); } .bad { color: var(--bad); }
  .legend { display: flex; flex-wrap: wrap; gap: 14px; font-size: 13px; color: var(--muted); margin-top: 12px; }
  .sw { display: inline-block; width: 12px; height: 12px; border-radius: 3px; vertical-align: -1px; margin-right: 5px; }
  table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 500; }
  .error { color: var(--bad); margin-top: 10px; font-size: 14px; }
</style>
</head>
<body>
<main>
  <h1>Maze Generator Viewer</h1>
  <p class="sub">Every maze here comes from <code>src/maze/generator.py</code>. Cells are vertices, gaps in the walls are edges.</p>
  <div class="layout">
    <form class="panel" id="controls">
      <div class="row">
        <div><label for="rows">Rows</label><input id="rows" type="number" min="1" max="60" value="15"></div>
        <div><label for="cols">Cols</label><input id="cols" type="number" min="1" max="60" value="20"></div>
      </div>
      <label for="algorithm">Algorithm</label>
      <select id="algorithm">
        <option value="dfs">Randomized DFS</option>
        <option value="kruskal">Kruskal (union-find)</option>
        <option value="prim">Prim</option>
      </select>
      <label for="seed">Seed</label>
      <input id="seed" type="number" value="42">
      <label for="braid">Braid factor: <span id="braidValue">0.00</span></label>
      <input id="braid" type="range" min="0" max="1" step="0.01" value="0">
      <label for="mode">Start / goal</label>
      <select id="mode">
        <option value="corners">Opposite corners</option>
        <option value="diameter">Tree diameter (harder)</option>
      </select>
      <label class="check"><input id="showDead" type="checkbox"> Highlight dead ends</label>
      <button type="submit">Generate</button>
      <button type="button" class="secondary" id="randomSeed">New random seed</button>
      <button type="button" class="secondary" id="runChecks">Run checks (300 mazes)</button>
      <div class="error" id="error"></div>
    </form>
    <section class="stage">
      <canvas id="canvas" aria-label="Generated maze"></canvas>
      <div class="legend">
        <span><i class="sw" style="background:var(--start)"></i>Start</span>
        <span><i class="sw" style="background:var(--goal)"></i>Goal</span>
        <span><i class="sw" style="background:var(--dead)"></i>Dead end (degree 1)</span>
      </div>
      <div class="stats" id="stats"></div>
      <div id="checks"></div>
    </section>
  </div>
</main>
<script>
const $ = (id) => document.getElementById(id);
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
let current = null;

async function generate() {
  $("error").textContent = "";
  const params = new URLSearchParams({
    rows: $("rows").value, cols: $("cols").value, seed: $("seed").value,
    algorithm: $("algorithm").value, braid: $("braid").value, mode: $("mode").value,
  });
  const response = await fetch("/api/maze?" + params);
  const data = await response.json();
  if (!response.ok) { $("error").textContent = data.error; return; }
  current = data;
  draw();
  showStats(data.stats, data);
}

function draw() {
  if (!current) return;
  const { rows, cols, open_right, open_down, start, goal, dead_ends } = current;
  const canvas = $("canvas");
  const maxWidth = canvas.parentElement.clientWidth - 32;
  const cell = Math.max(6, Math.min(36, Math.floor(maxWidth / cols), Math.floor(640 / rows)));
  const pad = 2, ratio = window.devicePixelRatio || 1;
  canvas.width = (cols * cell + pad * 2) * ratio;
  canvas.height = (rows * cell + pad * 2) * ratio;
  canvas.style.width = (cols * cell + pad * 2) + "px";
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  ctx.translate(pad, pad);

  const fill = (r, c, color) => { ctx.fillStyle = color; ctx.fillRect(c * cell, r * cell, cell, cell); };
  if ($("showDead").checked) dead_ends.forEach(([r, c]) => fill(r, c, css("--dead")));
  fill(start[0], start[1], css("--start"));
  fill(goal[0], goal[1], css("--goal"));

  ctx.strokeStyle = css("--wall");
  ctx.lineWidth = Math.max(1.5, cell / 12);
  ctx.lineCap = "square";
  ctx.beginPath();
  ctx.strokeRect(0, 0, cols * cell, rows * cell);           // outer border
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const x = c * cell, y = r * cell;
      if (c < cols - 1 && !open_right[r][c]) { ctx.moveTo(x + cell, y); ctx.lineTo(x + cell, y + cell); }
      if (r < rows - 1 && !open_down[r][c]) { ctx.moveTo(x, y + cell); ctx.lineTo(x + cell, y + cell); }
    }
  }
  ctx.stroke();
}

function showStats(s, data) {
  const yes = (v) => `<b class="${v ? "ok" : "bad"}">${v ? "Yes" : "No"}</b>`;
  $("stats").innerHTML = `
    <div class="stat"><b>${s.vertices}</b><span>Vertices |V|</span></div>
    <div class="stat"><b>${s.edges}</b><span>Edges |E| (tree: ${s.vertices - 1})</span></div>
    <div class="stat">${yes(s.connected)}<span>Connected</span></div>
    <div class="stat">${yes(s.is_tree)}<span>Spanning tree</span></div>
    <div class="stat"><b>${s.dead_end_count}</b><span>Dead ends</span></div>
    <div class="stat"><b>(${data.start}) → (${data.goal})</b><span>Start → goal</span></div>`;
}

async function runChecks() {
  $("checks").innerHTML = "<p>Running…</p>";
  const results = await (await fetch("/api/check")).json();
  const mark = (v) => `<span class="${v ? "ok" : "bad"}">${v ? "✓" : "✗"}</span>`;
  const rows = Object.entries(results).map(([name, r]) => `
    <tr><td>${name}</td><td>${mark(r.trees === r.checked)} ${r.trees} / ${r.checked}</td>
    <td>${mark(r.same_seed_same_maze)}</td><td>${mark(r.different_seeds_differ)}</td></tr>`).join("");
  $("checks").innerHTML = `<table>
    <tr><th>Algorithm</th><th>Spanning trees</th><th>Same seed → same maze</th><th>Different seeds differ</th></tr>
    ${rows}</table>`;
}

$("controls").addEventListener("submit", (e) => { e.preventDefault(); generate(); });
$("randomSeed").addEventListener("click", () => { $("seed").value = Math.floor(Math.random() * 1e6); generate(); });
$("runChecks").addEventListener("click", runChecks);
$("braid").addEventListener("input", () => { $("braidValue").textContent = Number($("braid").value).toFixed(2); });
$("braid").addEventListener("change", generate);
["algorithm", "mode"].forEach((id) => $(id).addEventListener("change", generate));
$("showDead").addEventListener("change", draw);
window.addEventListener("resize", draw);
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", draw);
generate();
</script>
</body>
</html>
"""


def main() -> None:
    """Start the server on 127.0.0.1 (this computer only) until Ctrl+C."""
    parser = argparse.ArgumentParser(description="Local web viewer for the maze generators.")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (default 8000)")
    port = parser.parse_args().port

    server = ThreadingHTTPServer(("127.0.0.1", port), MazeHandler)
    print(f"Maze viewer running at http://127.0.0.1:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
