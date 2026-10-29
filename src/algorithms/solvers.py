"""Path-finding algorithms on the maze graph.

Owner: Role 2 — Algorithms & Graph Analysis.

Every solver returns a SearchResult so the UI can animate the exploration
order and the comparison view can report explored-cell counts and path length.
Path reconstruction uses a parent-pointer tree built during the search.
"""

from __future__ import annotations

import heapq
import time
from collections import deque
from dataclasses import dataclass, field

from src.maze.graph import Cell, MazeGraph


@dataclass
class SearchResult:
    """Outcome of a single search run.

    Attributes:
        path: Cells from start to goal inclusive, or None if the goal is unreachable.
        explored_count: Number of distinct cells removed from the frontier / visited.
        explored_order: Cells in the order they were explored (used for animation).
        runtime_ms: Wall-clock runtime of the search in milliseconds.
    """

    path: list[Cell] | None
    explored_count: int
    explored_order: list[Cell] = field(default_factory=list)  # for animation
    runtime_ms: float = 0.0


def bfs(graph: MazeGraph, start: Cell, goal: Cell) -> SearchResult:
    """Find the shortest path from start to goal using breadth-first search.

    Args:
        graph: The maze graph.
        start: Starting cell.
        goal: Destination cell.

    Returns:
        SearchResult whose path has the minimum number of edges (or None).

    Concept: BFS — explores vertices in order of distance, so the first time the
    goal is dequeued its BFS-tree path is a shortest path in an unweighted graph.
    Complexity: O(|V| + |E|).
    """
    began = time.perf_counter()
    parent: dict[Cell, Cell | None] = {start: None}
    explored_order: list[Cell] = []
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        explored_order.append(cell)
        if cell == goal:
            break
        for nb in graph.neighbors(cell):
            if nb not in parent:
                parent[nb] = cell
                queue.append(nb)
    return _finish(parent, goal, explored_order, began)


def dfs(graph: MazeGraph, start: Cell, goal: Cell) -> SearchResult:
    """Find a (not necessarily shortest) path from start to goal using depth-first search.

    Args:
        graph: The maze graph.
        start: Starting cell.
        goal: Destination cell.

    Returns:
        SearchResult with any valid start-goal path (or None).

    Concept: DFS — stack-based traversal with backtracking; builds a DFS tree of parent pointers.
    Complexity: O(|V| + |E|).
    """
    began = time.perf_counter()
    parent: dict[Cell, Cell | None] = {}
    explored_order: list[Cell] = []
    stack: list[tuple[Cell, Cell | None]] = [(start, None)]
    while stack:
        cell, came_from = stack.pop()
        if cell in parent:
            continue
        parent[cell] = came_from
        explored_order.append(cell)
        if cell == goal:
            break
        for nb in graph.neighbors(cell):
            if nb not in parent:
                stack.append((nb, cell))
    return _finish(parent, goal, explored_order, began)


def dijkstra(
    graph: MazeGraph,
    start: Cell,
    goal: Cell,
    weights: dict[tuple[Cell, Cell], float],
) -> SearchResult:
    """(Extension) Find the minimum-weight path using Dijkstra's algorithm.

    Args:
        graph: The maze graph.
        start: Starting cell.
        goal: Destination cell.
        weights: Non-negative weight for each edge (a, b); treat as undirected.
            An edge missing from the map costs 1.

    Returns:
        SearchResult whose path has minimum total weight (or None).

    Raises:
        ValueError: If any weight on an edge reached by the search is negative.

    Concept: Weighted graphs — greedy shortest paths with a priority queue
    (requires non-negative edge weights).
    Complexity: O((|V| + |E|) log |V|) with a binary heap.
    """
    began = time.perf_counter()
    dist: dict[Cell, float] = {start: 0.0}
    parent: dict[Cell, Cell | None] = {start: None}
    explored_order: list[Cell] = []
    settled: set[Cell] = set()
    heap: list[tuple[float, Cell]] = [(0.0, start)]
    while heap:
        d, cell = heapq.heappop(heap)
        if cell in settled:
            continue
        settled.add(cell)
        explored_order.append(cell)
        if cell == goal:
            break
        for nb in graph.neighbors(cell):
            weight = weights.get((cell, nb), weights.get((nb, cell), 1.0))
            if weight < 0:
                raise ValueError(f"Negative weight {weight} on edge {cell}-{nb}")
            candidate = d + weight
            if nb not in dist or candidate < dist[nb]:
                dist[nb] = candidate
                parent[nb] = cell
                heapq.heappush(heap, (candidate, nb))
    return _finish(parent, goal, explored_order, began, reached=goal in settled)


def a_star(graph: MazeGraph, start: Cell, goal: Cell) -> SearchResult:
    """(Extension) Find the shortest path using A* with the Manhattan-distance heuristic.

    Args:
        graph: The maze graph.
        start: Starting cell.
        goal: Destination cell.

    Returns:
        SearchResult with a shortest path (or None).

    Concept: Heuristic search — Manhattan distance |dr| + |dc| is admissible on a
    4-connected grid, so A* returns an optimal path.
    Complexity: O(|E| log |V|) worst case; usually explores far fewer cells than BFS.
    """
    began = time.perf_counter()
    g_cost: dict[Cell, int] = {start: 0}
    parent: dict[Cell, Cell | None] = {start: None}
    explored_order: list[Cell] = []
    closed: set[Cell] = set()
    heap: list[tuple[int, Cell]] = [(_manhattan(start, goal), start)]
    while heap:
        _, cell = heapq.heappop(heap)
        if cell in closed:
            continue
        closed.add(cell)
        explored_order.append(cell)
        if cell == goal:
            break
        for nb in graph.neighbors(cell):
            candidate = g_cost[cell] + 1
            if nb not in g_cost or candidate < g_cost[nb]:
                g_cost[nb] = candidate
                parent[nb] = cell
                heapq.heappush(heap, (candidate + _manhattan(nb, goal), nb))
    return _finish(parent, goal, explored_order, began, reached=goal in closed)


def reconstruct_path(parent: dict[Cell, Cell | None], goal: Cell) -> list[Cell] | None:
    """Rebuild the start-to-goal path by following parent pointers back from the goal.

    Args:
        parent: Parent-pointer map produced by a search (start maps to None).
        goal: Destination cell.

    Returns:
        Path from start to goal inclusive, or None if goal was never reached.

    Concept: Trees — the parent map is a rooted tree; walking goal -> root gives
    the unique tree path.
    Complexity: O(path length) <= O(|V|).
    """
    if goal not in parent:
        return None
    path: list[Cell] = []
    cell: Cell | None = goal
    while cell is not None:
        path.append(cell)
        cell = parent[cell]
    path.reverse()
    return path


def _manhattan(a: Cell, b: Cell) -> int:
    """Manhattan distance |dr| + |dc| between two cells (admissible on a 4-connected grid)."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _finish(
    parent: dict[Cell, Cell | None],
    goal: Cell,
    explored_order: list[Cell],
    began: float,
    reached: bool = True,
) -> SearchResult:
    """Build the SearchResult for a finished search.

    ``reached`` is False for searches (Dijkstra, A*) whose parent map can hold a
    goal that was discovered but never settled, so its path is not final yet.
    """
    path = reconstruct_path(parent, goal) if reached else None
    runtime_ms = (time.perf_counter() - began) * 1000
    return SearchResult(path, len(explored_order), explored_order, runtime_ms)


def compare_algorithms(graph: MazeGraph, start: Cell, goal: Cell) -> dict[str, SearchResult]:
    """Run every available solver on the same maze for side-by-side comparison.

    Args:
        graph: The maze graph.
        start: Starting cell.
        goal: Destination cell.

    Returns:
        Mapping of algorithm name ("bfs", "dfs", optionally "a_star") to its SearchResult.

    Concept: Algorithm analysis — compares explored-cell counts and path lengths.
    Complexity: O(k * (|V| + |E|)) for k algorithms.
    """
    return {
        "bfs": bfs(graph, start, goal),
        "dfs": dfs(graph, start, goal),
        "a_star": a_star(graph, start, goal),
    }
