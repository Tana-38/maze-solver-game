"""Graph representation of a maze.

Owner: Role 1 — Graph & Maze Generation.

The maze is an undirected graph G = (V, E):
  * V = every cell (row, col) of the rows x cols grid
  * E = every open passage between two orthogonally adjacent cells

The underlying *grid graph* contains all 4-neighbor adjacencies; a maze is a
spanning subgraph of it (a spanning tree when the maze is "perfect").
"""

from __future__ import annotations

# Shared type aliases — import these everywhere else in the codebase.
Cell = tuple[int, int]           # (row, col)
Graph = dict[Cell, list[Cell]]   # adjacency list


class MazeGraph:
    """Undirected graph of maze cells stored as an adjacency list.

    Discrete math concept: Graph Theory — adjacency-list representation,
    vertices = cells, edges = passages.
    """

    def __init__(self, rows: int, cols: int) -> None:
        """Create a graph with rows * cols vertices and no edges (all walls up).

        Args:
            rows: Number of grid rows.
            cols: Number of grid columns.

        Returns:
            None.

        Concept: Graph Theory — empty graph on |V| = rows * cols vertices.
        Complexity: O(rows * cols).
        """
        raise NotImplementedError("TODO: Role 1 — store rows/cols and initialise an empty adjacency list for every cell")

    def add_edge(self, a: Cell, b: Cell) -> None:
        """Open a passage between two adjacent cells (undirected edge).

        Args:
            a: First cell.
            b: Second cell; must be a grid neighbor of ``a``.

        Returns:
            None.

        Concept: Graph Theory — adding edge {a, b} to E (both adjacency lists).
        Complexity: O(1) amortised (plus O(deg) if checking for duplicates).
        """
        raise NotImplementedError("TODO: Role 1 — append b to adj[a] and a to adj[b], rejecting non-adjacent or duplicate edges")

    def remove_edge(self, a: Cell, b: Cell) -> None:
        """Close the passage between two cells (put the wall back).

        Args:
            a: First cell.
            b: Second cell.

        Returns:
            None.

        Concept: Graph Theory — removing edge {a, b} from E.
        Complexity: O(deg(a) + deg(b)) = O(1) since deg <= 4.
        """
        raise NotImplementedError("TODO: Role 1 — remove b from adj[a] and a from adj[b]")

    def neighbors(self, cell: Cell) -> list[Cell]:
        """Return the cells reachable from ``cell`` through an open passage.

        Args:
            cell: The vertex whose neighborhood is requested.

        Returns:
            List of adjacent cells N(cell) in the maze graph.

        Concept: Graph Theory — open neighborhood N(v) in an adjacency list.
        Complexity: O(1) to fetch (O(deg(v)) to copy).
        """
        raise NotImplementedError("TODO: Role 1 — return the adjacency list of cell")

    def has_edge(self, a: Cell, b: Cell) -> bool:
        """Check whether a passage exists between two cells.

        Args:
            a: First cell.
            b: Second cell.

        Returns:
            True if {a, b} is in E, otherwise False.

        Concept: Graph Theory — edge membership test.
        Complexity: O(deg(a)) = O(1) since deg <= 4.
        """
        raise NotImplementedError("TODO: Role 1 — return whether b is in adj[a]")

    def vertex_count(self) -> int:
        """Return |V|, the number of cells.

        Args:
            None.

        Returns:
            Number of vertices.

        Concept: Graph Theory — order of the graph |V|.
        Complexity: O(1).
        """
        raise NotImplementedError("TODO: Role 1 — return the number of vertices")

    def edge_count(self) -> int:
        """Return |E|, the number of open passages.

        Args:
            None.

        Returns:
            Number of undirected edges.

        Concept: Graph Theory — Handshake Lemma: |E| = (sum of degrees) / 2.
        Complexity: O(|V|).
        """
        raise NotImplementedError("TODO: Role 1 — sum all degrees and divide by 2 (Handshake Lemma)")

    def grid_neighbors(self, cell: Cell) -> list[Cell]:
        """Return the up-to-4 orthogonal grid neighbors of ``cell``, bounds-checked.

        Passages are ignored: this describes the underlying grid graph, not the maze.

        Args:
            cell: The cell whose grid neighbors are requested.

        Returns:
            List of in-bounds cells at (r-1,c), (r+1,c), (r,c-1), (r,c+1).

        Concept: Graph Theory — neighborhood in the rows x cols grid graph P_m x P_n.
        Complexity: O(1).
        """
        raise NotImplementedError("TODO: Role 1 — return the in-bounds up/down/left/right cells")

    def to_dict(self) -> Graph:
        """Export the maze as a plain adjacency-list dictionary.

        Args:
            None.

        Returns:
            A ``Graph`` (dict[Cell, list[Cell]]) copy of the adjacency list.

        Concept: Graph Theory — adjacency-list representation.
        Complexity: O(|V| + |E|).
        """
        raise NotImplementedError("TODO: Role 1 — return a copy of the adjacency list as a dict")
