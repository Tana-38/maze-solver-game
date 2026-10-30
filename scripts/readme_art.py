"""Build the animated SVGs used in README.md from the project's own code.

Owner: Role 4: Game Logic & Integration.

Each image is a real maze from generate_maze_dfs, searched by the real bfs / dfs
in src/algorithms/solvers.py. The SVGs animate with plain CSS keyframes, which
GitHub renders inside <img> tags. Run from the project root:

    python scripts/readme_art.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.algorithms.solvers import SearchResult, bfs, dfs  # noqa: E402
from src.maze.generator import generate_maze_dfs  # noqa: E402
from src.maze.graph import Cell, MazeGraph  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "assets"
FONT = "Montserrat, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', Consolas, 'Courier New', monospace"
BG = "#151515"
WALL = "#f3f3f1"
STEEL = "#5f819b"
STEEL_LIGHT = "#a9c3d6"


def walls_path(graph: MazeGraph, cell: float, ox: float, oy: float) -> str:
    """One SVG path with every wall segment (grid edges missing from E)."""
    parts = []
    for r in range(graph.rows):
        for c in range(graph.cols):
            x, y = ox + c * cell, oy + r * cell
            if r == 0:
                parts.append(f"M{x:.1f} {y:.1f}h{cell:.1f}")
            if c == 0:
                parts.append(f"M{x:.1f} {y:.1f}v{cell:.1f}")
            if not graph.has_edge((r, c), (r, c + 1)):
                parts.append(f"M{x + cell:.1f} {y:.1f}v{cell:.1f}")
            if not graph.has_edge((r, c), (r + 1, c)):
                parts.append(f"M{x:.1f} {y + cell:.1f}h{cell:.1f}")
    return "".join(parts)


def route(path: list[Cell], cell: float, ox: float, oy: float) -> tuple[str, float]:
    """Polyline through cell centres, and its length (for stroke-dash drawing)."""
    pts = [(ox + (c + 0.5) * cell, oy + (r + 0.5) * cell) for r, c in path]
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    length = sum(abs(x2 - x1) + abs(y2 - y1) for (x1, y1), (x2, y2) in zip(pts, pts[1:]))
    return d, length


def search_layer(result: SearchResult, cell: float, ox: float, oy: float, cls: str,
                 search_time: float, period: float, fill: str, path_color: str) -> str:
    """Explored cells appear in search order, then the path draws itself; the loop repeats.

    Every element shares the same period, so each keeps its offset: the region
    fills in search order, the path is drawn, then everything clears in the
    same order and the search plays again.
    """
    n = len(result.explored_order)
    rects = []
    for i, (r, c) in enumerate(result.explored_order):
        delay = search_time * i / max(1, n - 1)
        rects.append(
            f'<rect class="{cls}" x="{ox + c * cell:.1f}" y="{oy + r * cell:.1f}" '
            f'width="{cell:.1f}" height="{cell:.1f}" style="animation-delay:{delay:.2f}s"/>'
        )
    d, length = route(result.path or [], cell, ox, oy)
    width = max(2.5, cell * 0.3)
    # Keyframe times are relative to the path's own start (search_time). The
    # first explored cell clears at 80% of the period, so the path fades just before.
    hold_end = 0.8 * period - search_time - 0.3
    fade_end = hold_end + 0.5
    return (
        f"<style>.{cls}{{fill:{fill};opacity:0;animation:cellcycle {period}s linear infinite}}"
        f".{cls}-path{{fill:none;stroke:{path_color};stroke-width:{width:.1f};stroke-linejoin:miter;"
        f"stroke-linecap:square;stroke-dasharray:{length:.0f};stroke-dashoffset:{length:.0f};"
        f"animation:{cls}-draw {period}s ease-in-out {search_time:.2f}s infinite}}"
        f"@keyframes {cls}-draw{{0%{{stroke-dashoffset:{length:.0f};opacity:1}}"
        f"{100 * 2.2 / period:.1f}%{{stroke-dashoffset:0;opacity:1}}"
        f"{100 * hold_end / period:.1f}%{{stroke-dashoffset:0;opacity:1}}"
        f"{100 * fade_end / period:.1f}%{{stroke-dashoffset:0;opacity:0}}"
        f"100%{{stroke-dashoffset:{length:.0f};opacity:0}}}}</style>"
        + "".join(rects)
        + f'<path class="{cls}-path" d="{d}"/>'
    )


CELL_CYCLE = (
    "@keyframes cellcycle{0%{opacity:0}2%{opacity:1}80%{opacity:1}84%{opacity:0}100%{opacity:0}}"
)


def corners(x: float, y: float, w: float, h: float, size: float = 14) -> str:
    """Corner brackets around a rectangle, the site's signature frame."""
    s = size
    return (
        f'<path d="M{x} {y + s}V{y}H{x + s}M{x + w - s} {y}H{x + w}V{y + s}'
        f'M{x + w} {y + h - s}V{y + h}H{x + w - s}M{x + s} {y + h}H{x}V{y + h - s}" '
        f'fill="none" stroke="{WALL}" stroke-width="2"/>'
    )


def banner() -> str:
    """Wide header: title letters rise in, then a maze is solved below it."""
    rows, cols, cell = 7, 34, 22
    graph = generate_maze_dfs(rows, cols, seed=2024)
    start, goal = (rows // 2, 0), (rows // 2, cols - 1)
    result = bfs(graph, start, goal)
    width, height = 900, 330
    ox, oy = (width - cols * cell) / 2, 150
    letters = "MAZE SOLVER"
    spacing = 46
    x0 = width / 2 - (len(letters) - 1) * spacing / 2
    title = "".join(
        f'<text class="ch" x="{x0 + i * spacing:.1f}" y="92" style="animation-delay:{0.15 + i * 0.07:.2f}s">{ch}</text>'
        for i, ch in enumerate(letters) if ch != " "
    )
    search_time, period = 5.5, 14
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Maze Solver: a maze being solved by breadth first search">
<style>
.ch{{font-family:{FONT};font-weight:800;font-size:46px;fill:{WALL};text-anchor:middle;opacity:0;animation:rise .9s cubic-bezier(.22,1,.36,1) forwards}}
@keyframes rise{{from{{opacity:0;transform:translateY(26px)}}to{{opacity:1;transform:translateY(0)}}}}
.sub{{font-family:{FONT};font-style:italic;font-size:15px;fill:#c9c9c6;text-anchor:middle;opacity:0;animation:fade 1s ease 1s forwards}}
.status{{font-family:{FONT};font-style:italic;font-size:12px;fill:#c9c9c6;text-anchor:middle}}
@keyframes fade{{to{{opacity:1}}}}
.walls{{fill:none;stroke:{WALL};stroke-width:2;stroke-linecap:square}}
{CELL_CYCLE}
</style>
<rect width="100%" height="100%" rx="18" fill="{BG}"/>
{title}
<text class="sub" x="{width / 2}" y="124">Every maze is a spanning tree. Watch a graph find its own way out.</text>
{search_layer(result, cell, ox, oy, "bfs", search_time, period, "rgba(169,195,214,0.22)", WALL)}
<path class="walls" d="{walls_path(graph, cell, ox, oy)}"/>
{corners(ox - 16, oy - 14, cols * cell + 32, rows * cell + 28)}
<text class="status" x="{width / 2}" y="{oy + rows * cell + 36}">breadth first search : {result.explored_count} cells explored, shortest path {len(result.path) - 1} moves</text>
</svg>
'''


def race() -> str:
    """BFS and DFS on the same maze, side by side, looping."""
    rows, cols, cell = 15, 15, 17
    graph = generate_maze_dfs(rows, cols, seed=77)
    start, goal = (0, 0), (rows - 1, cols - 1)
    results = {"BFS": bfs(graph, start, goal), "DFS": dfs(graph, start, goal)}
    width, height = 900, 400
    maze_w = cols * cell
    gap = 120
    left = (width - 2 * maze_w - gap) / 2
    oy = 74
    longest = max(r.explored_count for r in results.values())
    body = []
    for i, (name, res) in enumerate(results.items()):
        ox = left + i * (maze_w + gap)
        # explored counts scale the replay time so faster searches finish sooner
        search_time = 6.0 * res.explored_count / longest
        fill = "rgba(169,195,214,0.24)" if name == "BFS" else "rgba(95,129,155,0.42)"
        body.append(f'<text class="name" x="{ox}" y="{oy - 26}">{name}</text>')
        body.append(f'<text class="kind" x="{ox + maze_w}" y="{oy - 26}">{"breadth first" if name == "BFS" else "depth first"}</text>')
        body.append(search_layer(res, cell, ox, oy, name.lower(), search_time, 15, fill, WALL if name == "BFS" else STEEL_LIGHT))
        body.append(f'<path class="walls" d="{walls_path(graph, cell, ox, oy)}"/>')
        body.append(corners(ox - 12, oy - 10, maze_w + 24, rows * cell + 20, 12))
        body.append(
            f'<text class="stat" x="{ox}" y="{oy + rows * cell + 38}">explored {res.explored_count}'
            f'   path {len(res.path) - 1}</text>'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="BFS and DFS solving the same maze side by side">
<style>
.walls{{fill:none;stroke:{WALL};stroke-width:1.8;stroke-linecap:square}}
.name{{font-family:{FONT};font-weight:800;font-size:20px;letter-spacing:6px;fill:{WALL}}}
.kind{{font-family:{FONT};font-style:italic;font-size:12px;fill:#8c8c89;text-anchor:end}}
.stat{{font-family:{MONO};font-size:13px;fill:#c9c9c6}}
{CELL_CYCLE}
</style>
<rect width="100%" height="100%" rx="18" fill="{BG}"/>
{"".join(body)}
</svg>
'''


def divider() -> str:
    """A thin animated corridor used between README sections."""
    width, height = 900, 28
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" aria-hidden="true">
<style>
.w{{fill:none;stroke:#8c8c89;stroke-width:2;stroke-dasharray:120 30 60 24;animation:slide 6s linear infinite}}
.r{{fill:none;stroke:{STEEL_LIGHT};stroke-width:4;stroke-dasharray:70 830;animation:run 4s cubic-bezier(.45,0,.55,1) infinite}}
@keyframes slide{{to{{stroke-dashoffset:-234}}}}
@keyframes run{{from{{stroke-dashoffset:70}}to{{stroke-dashoffset:-830}}}}
</style>
<path class="w" d="M0 3H{width}"/><path class="w" d="M0 25H{width}" style="animation-direction:reverse"/>
<path class="r" d="M0 14H{width}"/>
</svg>
'''


def main() -> None:
    """Write every SVG into docs/assets."""
    OUT.mkdir(parents=True, exist_ok=True)
    for name, svg in {"banner.svg": banner(), "race.svg": race(), "divider.svg": divider()}.items():
        (OUT / name).write_text(svg, encoding="utf-8")
        print(f"wrote docs/assets/{name} ({len(svg) // 1024} KB)")


if __name__ == "__main__":
    main()
