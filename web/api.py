"""JSON API behind the web frontend (standard library only, no pygame).

Owner: Role 4: Game Logic & Integration.

Every response is built from the real project modules: the generators in
src/maze, the solvers and graph checks in src/algorithms and src/analysis, and
PlayerController / compute_score from src/game. The browser never decides
whether a move is legal or what the score is; the server does.

Games are stateless so the API also runs on serverless hosts (Vercel), where
two requests may reach different processes. The game id is a signed token that
holds the maze settings (the seed makes the maze reproducible), the moves made
so far, the hint count and the clock. Each request checks the signature,
rebuilds the maze, replays the moves through PlayerController, applies the new
action and returns a fresh token.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from src.algorithms.solvers import SearchResult, a_star, bfs, compare_algorithms, dfs
from src.analysis.properties import (
    count_dead_ends,
    count_spanning_trees,
    degree_distribution,
    difficulty_score,
    is_bipartite,
    is_connected,
    is_tree,
    tree_diameter,
)
from src.config import DIFFICULTY_LEVELS
from src.game.player import PlayerController
from src.game.scoring import compute_score
from src.maze.generator import (
    add_braids,
    generate_maze_dfs,
    generate_maze_kruskal,
    generate_maze_prim,
    pick_start_and_goal,
)
from src.maze.graph import Cell, MazeGraph

GENERATORS: dict[str, Callable[[int, int, int | None], MazeGraph]] = {
    "dfs": generate_maze_dfs,
    "kruskal": generate_maze_kruskal,
    "prim": generate_maze_prim,
}
SOLVERS: dict[str, Callable[[MazeGraph, Cell, Cell], SearchResult]] = {
    "bfs": bfs,
    "dfs": dfs,
    "a_star": a_star,
}
START_MODES = ("corners", "diameter")
MAX_SIZE = 40              # largest rows/cols a game may use
MAX_SPANNING_SIZE = 6      # Matrix-Tree determinant is O(|V|^3), keep it small
MAX_MOVES = 4000           # keeps the token (and the URL it travels in) small
MAX_BATCH = 400            # most moves accepted in one request
MOVE_CODES = {"up": "u", "down": "d", "left": "l", "right": "r"}
CODE_MOVES = {code: name for name, code in MOVE_CODES.items()}
DEV_SECRET = "maze-solver-dev-secret"  # used when MAZE_SECRET is not set


class ApiError(Exception):
    """A client error; the server answers it with the given HTTP status."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


@dataclass
class GameSession:
    """One maze being played in the browser.

    Attributes:
        graph: The maze.
        start: Start cell.
        goal: Goal cell.
        controller: Validates moves and tracks the player's walk.
        optimal_path: BFS shortest path from start to goal.
        settings: The options the maze was generated with.
        moves: Directions of the successful moves, in order.
        first_move_at: Unix time of the first move (the clock starts there).
        finished_at: Unix time the goal was reached, or None.
        solution_revealed: True once the browser asked for a solver's path.
    """

    graph: MazeGraph
    start: Cell
    goal: Cell
    controller: PlayerController
    optimal_path: list[Cell]
    settings: dict[str, Any] = field(default_factory=dict)
    moves: list[str] = field(default_factory=list)
    first_move_at: float | None = None
    finished_at: float | None = None
    solution_revealed: bool = False

    def elapsed(self) -> float:
        """Seconds from the first move to the goal (or to now if still playing)."""
        if self.first_move_at is None:
            return 0.0
        end = self.finished_at if self.finished_at is not None else time.time()
        return end - self.first_move_at


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class TokenStore:
    """Encodes a GameSession as a signed token and rebuilds it from one.

    The token is base64(JSON state) + "." + base64(HMAC-SHA256), so the browser
    can carry it but cannot change the moves, hints or clock without the server
    noticing.
    """

    def __init__(self, secret: str | None = None) -> None:
        self._key = (secret or DEV_SECRET).encode("utf-8")

    def _sign(self, payload: str) -> str:
        return _b64(hmac.new(self._key, payload.encode("ascii"), hashlib.sha256).digest()[:18])

    def save(self, session: GameSession) -> str:
        """Return the token describing the session's current state."""
        state = {
            "s": session.settings,
            "m": "".join(MOVE_CODES[d] for d in session.moves),
            "h": session.controller.state.hints_used,
            "r": session.solution_revealed,
            "t0": session.first_move_at,
            "t1": session.finished_at,
        }
        payload = _b64(json.dumps(state, separators=(",", ":")).encode("utf-8"))
        return f"{payload}.{self._sign(payload)}"

    def get(self, token: str) -> GameSession:
        """Verify a token and replay it into a GameSession, or raise a 404 ApiError."""
        payload, _, signature = token.partition(".")
        if not signature or not hmac.compare_digest(signature, self._sign(payload)):
            raise ApiError("game not found; start a new maze", 404)
        try:
            state = json.loads(_unb64(payload))
            session = new_session(state["s"])
            for code in state["m"]:
                if not session.controller.try_move(CODE_MOVES[code]):
                    raise ValueError("move through a wall")
                session.moves.append(CODE_MOVES[code])
        except (ValueError, KeyError, TypeError):
            raise ApiError("game not found; start a new maze", 404) from None
        session.controller.state.hints_used = int(state["h"])
        session.solution_revealed = bool(state["r"])
        session.first_move_at = state["t0"]
        session.finished_at = state["t1"]
        return session


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------
def maze_to_json(graph: MazeGraph, start: Cell, goal: Cell) -> dict[str, Any]:
    """Describe the maze's passages as two boolean grids the browser can draw.

    Concept: Graph Theory: E is exported as "open right" / "open down" flags per cell.
    Complexity: O(|V|).
    """
    rows, cols = graph.rows, graph.cols
    return {
        "rows": rows,
        "cols": cols,
        "open_right": [[graph.has_edge((r, c), (r, c + 1)) for c in range(cols)] for r in range(rows)],
        "open_down": [[graph.has_edge((r, c), (r + 1, c)) for c in range(cols)] for r in range(rows)],
        "start": list(start),
        "goal": list(goal),
    }


def search_to_json(name: str, result: SearchResult) -> dict[str, Any]:
    """Convert a SearchResult to JSON, adding the path length in moves."""
    return {
        "algorithm": name,
        "path": [list(c) for c in result.path] if result.path else None,
        "path_length": len(result.path) - 1 if result.path else None,
        "explored_count": result.explored_count,
        "explored_order": [list(c) for c in result.explored_order],
        "runtime_ms": round(result.runtime_ms, 3),
    }


def analyse(graph: MazeGraph, start: Cell, goal: Cell) -> dict[str, Any]:
    """Run every graph-property check on a maze.

    Concept: Handshake Lemma, trees, bipartite graphs, degree analysis, diameter.
    Complexity: O(|V| + |E|).
    """
    vertices, edges = graph.vertex_count(), graph.edge_count()
    connected = is_connected(graph)
    degrees = degree_distribution(graph)
    return {
        "vertices": vertices,
        "edges": edges,
        "degree_sum": sum(d * n for d, n in degrees.items()),
        "connected": connected,
        "is_tree": is_tree(graph),
        "is_bipartite": is_bipartite(graph),
        # Cyclomatic number |E| - |V| + 1: independent cycles a braid added.
        "cycles": edges - vertices + 1 if connected else None,
        "dead_ends": count_dead_ends(graph),
        "degree_distribution": {str(d): n for d, n in degrees.items()},
        "diameter": tree_diameter(graph) if connected else None,
        "difficulty": round(difficulty_score(graph, start, goal), 4) if connected else None,
    }


def _player_json(session: GameSession) -> dict[str, Any]:
    state = session.controller.state
    return {
        "current": list(state.current),
        "moves": state.moves,
        "backtracks": state.backtracks,
        "hints_used": state.hints_used,
        "elapsed": round(session.elapsed(), 2),
        "finished": session.finished_at is not None,
    }


# ---------------------------------------------------------------------------
# Parameter parsing
# ---------------------------------------------------------------------------
def _int(value: Any, name: str, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ApiError(f"{name} must be an integer") from None
    if not low <= number <= high:
        raise ApiError(f"{name} must be between {low} and {high}")
    return number


def _choice(value: Any, name: str, options: tuple[str, ...] | list[str]) -> str:
    if value not in options:
        raise ApiError(f"{name} must be one of {', '.join(options)}")
    return value


def parse_settings(body: dict[str, Any]) -> dict[str, Any]:
    """Validate the options for a new maze, filling in defaults.

    A named difficulty supplies rows, cols and braid; "custom" reads them from the body.
    """
    difficulty = _choice(body.get("difficulty", "medium"), "difficulty", [*DIFFICULTY_LEVELS, "custom"])
    if difficulty == "custom":
        rows = _int(body.get("rows", 15), "rows", 2, MAX_SIZE)
        cols = _int(body.get("cols", 15), "cols", 2, MAX_SIZE)
        try:
            braid = float(body.get("braid", 0.0))
        except (TypeError, ValueError):
            raise ApiError("braid must be a number") from None
        if not 0.0 <= braid <= 1.0:
            raise ApiError("braid must be between 0 and 1")
    else:
        rows, cols, braid = DIFFICULTY_LEVELS[difficulty]
    seed = body.get("seed")
    seed = secrets.randbelow(1_000_000_000) if seed in (None, "") else _int(seed, "seed", 0, 2**31 - 1)
    return {
        "difficulty": difficulty,
        "rows": rows,
        "cols": cols,
        "braid": braid,
        "algorithm": _choice(body.get("algorithm", "dfs"), "algorithm", tuple(GENERATORS)),
        "mode": _choice(body.get("mode", "corners"), "mode", START_MODES),
        "seed": seed,
    }


def build_maze(settings: dict[str, Any]) -> tuple[MazeGraph, Cell, Cell]:
    """Generate (and optionally braid) a maze and pick its start and goal.

    Concept: Trees: a random spanning tree; braiding adds edges, each closing one cycle.
    Complexity: O(|V| log |V|) at worst (Kruskal), O(|V|) for DFS.
    """
    graph = GENERATORS[settings["algorithm"]](settings["rows"], settings["cols"], settings["seed"])
    if settings["braid"] > 0:
        add_braids(graph, settings["braid"], seed=settings["seed"])
    start, goal = pick_start_and_goal(graph, mode=settings["mode"])
    return graph, start, goal


# ---------------------------------------------------------------------------
# Endpoints (called by web/server.py)
# ---------------------------------------------------------------------------
def new_session(settings: dict[str, Any]) -> GameSession:
    """Build the maze for some settings and a fresh game on it (the seed makes it repeatable)."""
    graph, start, goal = build_maze(settings)
    return GameSession(
        graph=graph,
        start=start,
        goal=goal,
        controller=PlayerController(graph, start, goal),
        optimal_path=bfs(graph, start, goal).path or [start],
        settings=settings,
    )


def create_game(store: TokenStore, body: dict[str, Any]) -> dict[str, Any]:
    """POST /api/games: generate a maze and start a game on it."""
    session = new_session(parse_settings(body))
    graph, start, goal = session.graph, session.start, session.goal
    return {
        "id": store.save(session),
        "settings": session.settings,
        "maze": maze_to_json(graph, start, goal),
        "optimal_moves": len(session.optimal_path) - 1,
        "analysis": analyse(graph, start, goal),
        "player": _player_json(session),
    }


def move(store: TokenStore, game_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """POST /api/games/<id>/move: apply one step, or a batch of steps, in order.

    The body holds "direction" or "directions" (a list, so a browser that moves
    faster than the network can send everything queued in one request). Steps
    stop at the first one blocked by a wall or at the goal. "applied" says how
    many were taken.

    Concept: Graph Theory: the player may only traverse edges of G.
    """
    session = store.get(game_id)
    directions = body.get("directions", [body.get("direction")])
    if not isinstance(directions, list) or not 1 <= len(directions) <= MAX_BATCH:
        raise ApiError(f"directions must be a list of 1 to {MAX_BATCH} moves")
    for direction in directions:
        _choice(direction, "direction", ("up", "down", "left", "right"))
    if session.finished_at is not None:
        return {"id": game_id, "moved": False, "applied": 0, "player": _player_json(session)}
    if len(session.moves) + len(directions) > MAX_MOVES:
        raise ApiError("too many moves; start a new maze")
    applied = 0
    response: dict[str, Any] = {}
    for direction in directions:
        if not session.controller.try_move(direction):
            break
        applied += 1
        session.moves.append(direction)
        if session.first_move_at is None:
            session.first_move_at = time.time()
        if session.controller.has_reached_goal():
            session.finished_at = time.time()
            response["result"] = result_json(session)
            break
    response["moved"] = applied > 0
    response["applied"] = applied
    response["player"] = _player_json(session)
    response["id"] = store.save(session)
    return response


def result_json(session: GameSession) -> dict[str, Any]:
    """Score a finished game against the BFS-optimal path."""
    result = compute_score(session.controller.state, session.optimal_path, session.elapsed())
    return {
        "score": round(result.score, 4),
        "rating": result.rating,
        "player_moves": result.player_moves,
        "optimal_moves": result.optimal_moves,
        "backtracks": result.backtracks,
        "hints_used": result.hints_used,
        "elapsed_seconds": round(result.elapsed_seconds, 2),
        "solution_revealed": session.solution_revealed,
        "player_path": [list(c) for c in session.controller.state.path],
        "optimal_path": [list(c) for c in session.optimal_path],
    }


def hint(store: TokenStore, game_id: str) -> dict[str, Any]:
    """POST /api/games/<id>/hint: next cell on the BFS path from the player to the goal."""
    session = store.get(game_id)
    if session.finished_at is not None:
        return {"id": game_id, "hint": None, "player": _player_json(session)}
    path = bfs(session.graph, session.controller.state.current, session.goal).path
    cell = session.controller.request_hint(path) if path else None
    return {"id": store.save(session), "hint": list(cell) if cell else None, "player": _player_json(session)}


def restart(store: TokenStore, game_id: str) -> dict[str, Any]:
    """POST /api/games/<id>/restart: same maze, player back on the start cell."""
    session = store.get(game_id)
    session.controller.reset()
    session.moves = []
    session.first_move_at = None
    session.finished_at = None
    session.solution_revealed = False
    return {"id": store.save(session), "player": _player_json(session)}


def solve(store: TokenStore, game_id: str, algorithm: str) -> dict[str, Any]:
    """GET /api/games/<id>/solve?algorithm=: run one solver from start to goal."""
    session = store.get(game_id)
    name = _choice(algorithm, "algorithm", tuple(SOLVERS))
    session.solution_revealed = True
    response = search_to_json(name, SOLVERS[name](session.graph, session.start, session.goal))
    response["id"] = store.save(session)
    return response


def compare(store: TokenStore, game_id: str) -> dict[str, Any]:
    """GET /api/games/<id>/compare: BFS, DFS and A* on the same maze, plus a verdict."""
    session = store.get(game_id)
    results = compare_algorithms(session.graph, session.start, session.goal)
    return {
        "results": {name: search_to_json(name, r) for name, r in results.items()},
        "verdict": verdict(results),
    }


def verdict(results: dict[str, SearchResult]) -> str:
    """One sentence comparing how much each solver explored and the path lengths."""
    names = {"bfs": "BFS", "dfs": "DFS", "a_star": "A*"}
    fewest = min(results, key=lambda n: results[n].explored_count)
    counts = ", ".join(f"{names.get(n, n)} {r.explored_count}" for n, r in results.items())
    lengths = {len(r.path) - 1 for r in results.values() if r.path}
    if len(lengths) == 1:
        paths = f"every path has the same length ({lengths.pop()} moves)"
    else:
        bfs_len = len(results["bfs"].path) - 1 if results.get("bfs") and results["bfs"].path else None
        paths = f"the shortest path is {bfs_len} moves, longer routes exist because of loops"
    return f"{names.get(fewest, fewest)} explored the fewest cells ({counts}); {paths}."


def demo(query: dict[str, Any]) -> dict[str, Any]:
    """GET /api/demo: a wide maze with its BFS search, for the landing animation."""
    rows = _int(query.get("rows", 5), "rows", 2, 20)
    cols = _int(query.get("cols", 20), "cols", 2, 60)
    seed = query.get("seed")
    seed = secrets.randbelow(1_000_000_000) if seed in (None, "") else _int(seed, "seed", 0, 2**31 - 1)
    graph = generate_maze_dfs(rows, cols, seed)
    start, goal = (rows // 2, 0), (rows // 2, cols - 1)
    return {
        "maze": maze_to_json(graph, start, goal),
        "search": search_to_json("bfs", bfs(graph, start, goal)),
    }


def spanning_trees(query: dict[str, Any]) -> dict[str, Any]:
    """GET /api/spanning-trees: how many different perfect mazes fit a small grid.

    Concept: Kirchhoff's Matrix-Tree Theorem.
    """
    rows = _int(query.get("rows", 3), "rows", 1, MAX_SPANNING_SIZE)
    cols = _int(query.get("cols", 3), "cols", 1, MAX_SPANNING_SIZE)
    return {"rows": rows, "cols": cols, "count": str(count_spanning_trees(rows, cols))}
