"""Maze generation algorithms.

Owner: Role 1 — Graph & Maze Generation.

A *perfect* maze is a spanning tree of the grid graph: it is connected and
acyclic, so there is exactly one simple path between any two cells and
|E| = |V| - 1. "Braiding" removes extra walls, adding cycles.

Every generator takes an optional ``seed`` and uses its own ``random.Random``
instance, so the same seed always gives the same maze and the global random
state is never touched.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Literal

from src.maze.graph import Cell, MazeGraph

Wall = tuple[Cell, Cell]   # a grid-graph edge {a, b} that is not (yet) a passage


def generate_maze_dfs(rows: int, cols: int, seed: int | None = None) -> MazeGraph:
    """Generate a perfect maze with randomized depth-first search (recursive backtracker).

    The search is iterative with an explicit stack instead of recursion, so large
    grids (e.g. 50 x 50 = 2500 cells deep) cannot hit Python's recursion limit.
    It always starts from the top-left cell (0, 0).

    Args:
        rows: Number of grid rows.
        cols: Number of grid columns.
        seed: Optional RNG seed; the same seed must give the same maze.

    Returns:
        A MazeGraph that is a spanning tree of the grid graph.

    Concept: Trees / DFS — randomized DFS with backtracking builds a spanning tree
    (the DFS tree) of the grid graph. Each carved edge joins a visited cell to an
    unvisited one, so no cycle can form and all |V| cells end up connected.
    Complexity: O(|V|) = O(rows * cols).
    """
    rng = random.Random(seed)
    maze = MazeGraph(rows, cols)

    start: Cell = (0, 0)
    visited: set[Cell] = {start}
    stack: list[Cell] = [start]

    while stack:
        current = stack[-1]
        unvisited = [n for n in maze.grid_neighbors(current) if n not in visited]
        if not unvisited:
            stack.pop()          # dead end: backtrack to the previous cell
            continue
        nxt = rng.choice(unvisited)
        maze.add_edge(current, nxt)   # knock down the wall between them
        visited.add(nxt)
        stack.append(nxt)

    return maze


def _closed_walls(graph: MazeGraph) -> list[Wall]:
    """List every interior wall, i.e. every grid-graph edge that is not a passage.

    Each wall is listed once, as (cell, neighbor) with the neighbor below or to
    the right of the cell.

    Args:
        graph: The maze to inspect.

    Returns:
        The closed walls in row-major order.

    Concept: Graph Theory — the complement of E within the grid graph's edge set.
    Complexity: O(|V|) since each cell has at most 4 grid neighbors.
    """
    walls: list[Wall] = []
    for r in range(graph.rows):
        for c in range(graph.cols):
            cell = (r, c)
            for neighbor in [(r + 1, c), (r, c + 1)]:
                if neighbor in graph.grid_neighbors(cell) and not graph.has_edge(cell, neighbor):
                    walls.append((cell, neighbor))
    return walls


def add_braids(graph: MazeGraph, factor: float, seed: int | None = None) -> MazeGraph:
    """Remove a fraction of the remaining walls to introduce cycles (a "braid" maze).

    ``factor`` is the share of currently-closed interior walls to open, rounded
    to the nearest whole wall. Any factor > 0 opens at least one wall (if one
    exists), so a braided perfect maze is never still a tree. factor = 0.0
    leaves the maze untouched.

    Args:
        graph: The maze to modify in place (typically a perfect maze).
        factor: Fraction in [0, 1] of remaining interior walls to remove.
        seed: Optional RNG seed; the same maze and seed open the same walls.

    Returns:
        The same MazeGraph with extra edges added.

    Raises:
        ValueError: If factor is outside [0, 1].

    Concept: Graph Theory — adding any edge to a spanning tree creates exactly one
    cycle, so opening k walls of a perfect maze gives |E| = |V| - 1 + k and
    multiple routes between cells (which is why BFS and DFS can now disagree).
    Complexity: O(|V|) to enumerate candidate walls, plus O(k) to open k of them.
    """
    if not 0.0 <= factor <= 1.0:
        raise ValueError(f"Braid factor must be between 0.0 and 1.0, got {factor}")
    if factor == 0.0:
        return graph

    walls = _closed_walls(graph)
    if not walls:
        return graph

    count = max(1, round(factor * len(walls)))
    rng = random.Random(seed)
    for a, b in rng.sample(walls, count):
        graph.add_edge(a, b)
    return graph


def _farthest_cell(graph: MazeGraph, source: Cell) -> Cell:
    """Return a cell at maximum BFS distance from ``source``.

    If several cells are equally far, the one BFS reaches first is returned,
    so the result is deterministic.

    Args:
        graph: The maze graph.
        source: Cell to measure distances from.

    Returns:
        A farthest reachable cell (``source`` itself on a 1 x 1 grid).

    Concept: BFS — explores in layers of increasing distance, so the last cell
    dequeued is a farthest one.
    Complexity: O(|V| + |E|).
    """
    visited: set[Cell] = {source}
    queue: deque[Cell] = deque([source])
    last = source
    while queue:
        last = queue.popleft()
        for neighbor in graph.neighbors(last):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return last


def pick_start_and_goal(
    graph: MazeGraph,
    mode: Literal["corners", "diameter"] = "corners",
) -> tuple[Cell, Cell]:
    """Choose the start and goal cells for a maze.

    Modes:
      * "corners" (default): top-left (0, 0) and bottom-right (rows-1, cols-1).
      * "diameter": the two endpoints of the tree diameter, found by double BFS,
        so the solution path is as long as possible (a harder maze). BFS from any
        cell to its farthest cell u, then BFS from u to its farthest cell v;
        in a tree, u-v is a longest path. On a braided maze (with cycles) this
        still gives a far-apart pair but is not guaranteed to be the true diameter.

    Args:
        graph: The generated maze.
        mode: "corners" or "diameter".

    Returns:
        A (start, goal) pair of cells.

    Raises:
        ValueError: If mode is not one of the two options.

    Concept: Trees / BFS — diameter endpoints found by two BFS passes.
    Complexity: O(1) for "corners", O(|V| + |E|) for "diameter".
    """
    if mode == "corners":
        return (0, 0), (graph.rows - 1, graph.cols - 1)
    if mode == "diameter":
        u = _farthest_cell(graph, (0, 0))
        v = _farthest_cell(graph, u)
        return u, v
    raise ValueError(f"Unknown mode {mode!r}; expected 'corners' or 'diameter'")


class _DisjointSet:
    """Union-find over grid cells, with path compression and union by rank.

    Concept: Equivalence relations / partitions — each set is one connected
    component (equivalence class) of the forest built so far.
    """

    def __init__(self, cells: list[Cell]) -> None:
        """Put every cell in its own singleton set.

        Args:
            cells: All vertices.

        Returns:
            None.

        Concept: The finest partition of V (|V| components, no edges yet).
        Complexity: O(|V|).
        """
        self.parent: dict[Cell, Cell] = {cell: cell for cell in cells}
        self.rank: dict[Cell, int] = {cell: 0 for cell in cells}

    def find(self, cell: Cell) -> Cell:
        """Return the representative (root) of the set containing ``cell``.

        Path compression: every cell on the way is re-pointed straight at the root.

        Args:
            cell: Any cell.

        Returns:
            The root cell of its set.

        Concept: Rooted trees — each set is stored as a tree; the root names the set.
        Complexity: O(α(|V|)) amortised (inverse Ackermann, effectively constant).
        """
        root = cell
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[cell] != root:          # path compression
            self.parent[cell], cell = root, self.parent[cell]
        return root

    def union(self, a: Cell, b: Cell) -> bool:
        """Merge the sets containing ``a`` and ``b``.

        Union by rank: the shorter tree is hung under the taller one.

        Args:
            a: First cell.
            b: Second cell.

        Returns:
            True if they were in different sets (and are now merged), False if
            they were already in the same set.

        Concept: Partitions — joining two equivalence classes.
        Complexity: O(α(|V|)) amortised.
        """
        root_a, root_b = self.find(a), self.find(b)
        if root_a == root_b:
            return False
        if self.rank[root_a] < self.rank[root_b]:
            root_a, root_b = root_b, root_a
        self.parent[root_b] = root_a
        if self.rank[root_a] == self.rank[root_b]:
            self.rank[root_a] += 1
        return True


def generate_maze_kruskal(rows: int, cols: int, seed: int | None = None) -> MazeGraph:
    """(Extension) Generate a perfect maze with randomized Kruskal's algorithm.

    Every grid edge is shuffled into a random order (equivalent to giving each a
    random weight), then each edge is opened only if its two cells are not yet
    connected. Stops early once |V| - 1 edges have been added.

    Args:
        rows: Number of grid rows.
        cols: Number of grid columns.
        seed: Optional RNG seed.

    Returns:
        A MazeGraph that is a spanning tree of the grid graph.

    Concept: Trees — Kruskal's minimum spanning tree with union-find (disjoint sets)
    on randomly ordered edges; an edge inside one component would close a cycle,
    so it is skipped.
    Complexity: O(|E|) to shuffle, ~O(|E| α(|V|)) for union-find.
    """
    rng = random.Random(seed)
    maze = MazeGraph(rows, cols)

    cells = [(r, c) for r in range(rows) for c in range(cols)]
    edges = _closed_walls(maze)    # on an empty maze this is every grid edge
    rng.shuffle(edges)

    components = _DisjointSet(cells)
    added = 0
    for a, b in edges:
        if components.union(a, b):
            maze.add_edge(a, b)
            added += 1
            if added == len(cells) - 1:   # spanning tree complete
                break
    return maze


def generate_maze_prim(rows: int, cols: int, seed: int | None = None) -> MazeGraph:
    """(Extension) Generate a perfect maze with randomized Prim's algorithm.

    The tree starts at a random cell. The frontier holds every edge from a tree
    cell to a non-tree cell; each step picks a random frontier edge and, if its
    outer cell is still outside the tree, carves it and adds that cell's edges.

    Args:
        rows: Number of grid rows.
        cols: Number of grid columns.
        seed: Optional RNG seed.

    Returns:
        A MazeGraph that is a spanning tree of the grid graph.

    Concept: Trees — Prim's algorithm grows a spanning tree from one vertex by
    repeatedly adding a random frontier edge (a cut edge between the tree and
    the rest of V), which can never create a cycle.
    Complexity: O(|E|) with a random-pick frontier list (O(|E| log |V|) with a heap).
    """
    rng = random.Random(seed)
    maze = MazeGraph(rows, cols)

    start: Cell = (rng.randrange(rows), rng.randrange(cols))
    in_tree: set[Cell] = {start}
    frontier: list[Wall] = [(start, n) for n in maze.grid_neighbors(start)]

    while frontier:
        # Pick a random frontier edge; swap it to the end so removal is O(1).
        i = rng.randrange(len(frontier))
        frontier[i], frontier[-1] = frontier[-1], frontier[i]
        inside, outside = frontier.pop()

        if outside in in_tree:
            continue             # both ends already in the tree: would make a cycle
        maze.add_edge(inside, outside)
        in_tree.add(outside)
        for n in maze.grid_neighbors(outside):
            if n not in in_tree:
                frontier.append((outside, n))

    return maze
