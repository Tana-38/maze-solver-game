"""Structural properties of maze graphs.

Owner: Role 2 — Algorithms & Graph Analysis.

These functions verify the discrete-math claims made about the maze
(connectivity, tree property, bipartiteness) and compute metrics used for
difficulty rating (dead ends, degree distribution, diameter).
"""

from __future__ import annotations

from collections import deque
from fractions import Fraction

from src.maze.graph import Cell, MazeGraph


def _bfs_distances(graph: MazeGraph, source: Cell) -> dict[Cell, int]:
    """Return the BFS distance (in edges) from ``source`` to every cell it can reach."""
    dist = {source: 0}
    queue = deque([source])
    while queue:
        cell = queue.popleft()
        for nb in graph.neighbors(cell):
            if nb not in dist:
                dist[nb] = dist[cell] + 1
                queue.append(nb)
    return dist


def is_connected(graph: MazeGraph) -> bool:
    """Check whether every cell is reachable from every other cell.

    Args:
        graph: The maze graph.

    Returns:
        True if the graph has exactly one connected component.

    Concept: BFS — connectivity check: BFS from any vertex visits all |V| vertices.
    Complexity: O(|V| + |E|).
    """
    return len(_bfs_distances(graph, (0, 0))) == graph.vertex_count()


def is_tree(graph: MazeGraph) -> bool:
    """Check whether the maze is a tree (i.e. a perfect maze).

    Args:
        graph: The maze graph.

    Returns:
        True if the graph is connected and |E| = |V| - 1.

    Concept: Trees — a connected graph with |E| = |V| - 1 is acyclic, hence a tree.
    Complexity: O(|V| + |E|).
    """
    return graph.edge_count() == graph.vertex_count() - 1 and is_connected(graph)


def count_dead_ends(graph: MazeGraph) -> int:
    """Count dead-end cells.

    Args:
        graph: The maze graph.

    Returns:
        Number of vertices with degree exactly 1 (leaves of the tree).

    Concept: Degree analysis — leaves / pendant vertices have deg(v) = 1.
    Complexity: O(|V|).
    """
    return degree_distribution(graph)[1]


def degree_distribution(graph: MazeGraph) -> dict[int, int]:
    """Compute how many cells have each degree.

    Args:
        graph: The maze graph.

    Returns:
        Mapping degree -> number of vertices with that degree. All of the
        degrees 0..4 are present as keys, with a count of 0 when unused.

    Concept: Degree analysis — degree sequence; sum of degrees = 2|E| (Handshake Lemma).
    Complexity: O(|V|).
    """
    counts = {degree: 0 for degree in range(5)}
    for adjacent in graph.to_dict().values():
        counts[len(adjacent)] += 1
    return counts


def is_bipartite(graph: MazeGraph) -> bool:
    """Check whether the maze graph is 2-colorable.

    Args:
        graph: The maze graph.

    Returns:
        True if vertices can be 2-colored with no edge joining same-colored vertices.
        (Always True for a grid subgraph: the checkerboard coloring (r + c) mod 2 works.)

    Concept: Bipartite graphs — BFS 2-coloring; equivalently, no odd cycles.
    Complexity: O(|V| + |E|).
    """
    color: dict[Cell, int] = {}
    for root in graph.to_dict():
        if root in color:
            continue
        color[root] = 0
        queue = deque([root])
        while queue:
            cell = queue.popleft()
            for nb in graph.neighbors(cell):
                if nb not in color:
                    color[nb] = 1 - color[cell]
                    queue.append(nb)
                elif color[nb] == color[cell]:
                    return False
    return True


def tree_diameter(graph: MazeGraph) -> int:
    """Compute the diameter (longest shortest path, in edges) of a tree maze.

    Args:
        graph: The maze graph; assumed to be a tree.

    Returns:
        Number of edges on the longest path between any two cells.

    Concept: Trees / BFS — double BFS: BFS from any vertex to the farthest vertex u,
    then BFS from u; the farthest distance found is the diameter.
    Complexity: O(|V| + |E|).
    """
    first = _bfs_distances(graph, (0, 0))
    far_end = max(first, key=first.get)
    return max(_bfs_distances(graph, far_end).values())


def difficulty_score(graph: MazeGraph, start: Cell, goal: Cell) -> float:
    """Rate how hard a maze is to solve.

    Combines solution path length, dead-end count, and average branching factor
    (mean degree of vertices with degree >= 3) into a single score.

    Args:
        graph: The maze graph.
        start: Starting cell.
        goal: Destination cell.

    Returns:
        A score in [0, 1] (higher = harder), the weighted sum of three terms in [0, 1]:
          * 0.5 * path term: shortest path length / (|V| - 1), the longest a path can be;
          * 0.3 * dead-end term: dead-end fraction of all cells, times 4, capped at 1
            (a typical perfect maze has about 10-15% dead ends);
          * 0.2 * branching term: (mean degree of the cells with degree >= 3) - 3,
            which is 0 when no cell branches and 1 when every branch cell has degree 4.

    Raises:
        ValueError: If goal cannot be reached from start.

    Concept: Degree analysis + BFS — shortest path length, leaf count, and branching.
    Complexity: O(|V| + |E|).
    """
    distances = _bfs_distances(graph, start)
    if goal not in distances:
        raise ValueError(f"Goal {goal} is not reachable from {start}")
    cells = graph.vertex_count()
    path_term = distances[goal] / (cells - 1) if cells > 1 else 0.0
    dead_end_term = min(1.0, 4 * count_dead_ends(graph) / cells)

    degrees = degree_distribution(graph)
    branch_cells = degrees[3] + degrees[4]
    branch_term = (3 * degrees[3] + 4 * degrees[4]) / branch_cells - 3 if branch_cells else 0.0
    return 0.5 * path_term + 0.3 * dead_end_term + 0.2 * branch_term


def count_spanning_trees(rows: int, cols: int) -> int:
    """(Extension) Count the spanning trees of the rows x cols grid graph.

    Intended for small grids only (e.g. up to ~6 x 6).

    Args:
        rows: Number of grid rows.
        cols: Number of grid columns.

    Returns:
        The number of distinct perfect mazes on this grid.

    Raises:
        ValueError: If rows or cols is less than 1.

    Concept: Kirchhoff's Matrix-Tree Theorem — the count equals any cofactor of the
    Laplacian matrix L = D - A.
    Complexity: O(|V|^3) for the determinant (use exact Fraction arithmetic).
    """
    if rows < 1 or cols < 1:
        raise ValueError(f"Grid must be at least 1 x 1, got {rows} x {cols}")
    index = {(r, c): r * cols + c for r in range(rows) for c in range(cols)}
    size = rows * cols
    laplacian = [[Fraction(0)] * size for _ in range(size)]
    for (r, c), i in index.items():
        for neighbor in ((r + 1, c), (r, c + 1)):
            if neighbor in index:
                j = index[neighbor]
                laplacian[i][i] += 1
                laplacian[j][j] += 1
                laplacian[i][j] -= 1
                laplacian[j][i] -= 1
    minor = [row[1:] for row in laplacian[1:]]
    return int(_determinant(minor))


def _determinant(matrix: list[list[Fraction]]) -> Fraction:
    """Exact determinant by Gaussian elimination (the empty matrix has determinant 1)."""
    n = len(matrix)
    det = Fraction(1)
    for col in range(n):
        pivot = next((r for r in range(col, n) if matrix[r][col] != 0), None)
        if pivot is None:
            return Fraction(0)
        if pivot != col:
            matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
            det = -det
        det *= matrix[col][col]
        for r in range(col + 1, n):
            factor = matrix[r][col] / matrix[col][col]
            if factor:
                for k in range(col, n):
                    matrix[r][k] -= factor * matrix[col][k]
    return det
