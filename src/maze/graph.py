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

    Attributes:
        rows: Number of grid rows (read-only by convention).
        cols: Number of grid columns (read-only by convention).

    Concept: Graph Theory — adjacency-list representation,
    vertices = cells, edges = passages.
    """

    def __init__(self, rows: int, cols: int) -> None:
        """Create a graph with rows * cols vertices and no edges (all walls up).

        Args:
            rows: Number of grid rows (must be >= 1).
            cols: Number of grid columns (must be >= 1).

        Returns:
            None.

        Raises:
            ValueError: If rows or cols is less than 1.

        Concept: Graph Theory — empty graph on |V| = rows * cols vertices.
        Complexity: O(rows * cols).
        """
        if rows < 1 or cols < 1:
            raise ValueError(f"Grid must be at least 1 x 1, got {rows} x {cols}")
        self.rows: int = rows
        self.cols: int = cols
        # Every cell is a vertex; an empty list means "walls on all four sides".
        self._adj: Graph = {(r, c): [] for r in range(rows) for c in range(cols)}

    def _in_bounds(self, cell: Cell) -> bool:
        """Return True if ``cell`` lies inside the rows x cols grid.

        Args:
            cell: The cell to check.

        Returns:
            True if 0 <= row < rows and 0 <= col < cols.

        Concept: Graph Theory — vertex membership test v in V.
        Complexity: O(1).
        """
        r, c = cell
        return 0 <= r < self.rows and 0 <= c < self.cols

    def _check_adjacent(self, a: Cell, b: Cell) -> None:
        """Raise ValueError unless a and b are in-bounds, orthogonally adjacent cells.

        Two cells are grid neighbors exactly when their Manhattan distance is 1.

        Args:
            a: First cell.
            b: Second cell.

        Returns:
            None.

        Raises:
            ValueError: If either cell is outside the grid or they are not adjacent.

        Concept: Graph Theory — {a, b} must be an edge of the grid graph P_m x P_n.
        Complexity: O(1).
        """
        if not self._in_bounds(a) or not self._in_bounds(b):
            raise ValueError(f"Cell out of bounds for {self.rows} x {self.cols} grid: {a}, {b}")
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            raise ValueError(f"Cells {a} and {b} are not orthogonally adjacent")

    def add_edge(self, a: Cell, b: Cell) -> None:
        """Open a passage between two adjacent cells (undirected edge).

        Adding an edge that already exists does nothing, so the adjacency lists
        never contain duplicates.

        Args:
            a: First cell.
            b: Second cell; must be a grid neighbor of ``a``.

        Returns:
            None.

        Raises:
            ValueError: If the cells are out of bounds or not orthogonally adjacent.

        Concept: Graph Theory — adding edge {a, b} to E (both adjacency lists).
        Complexity: O(deg(a)) duplicate check = O(1) since deg <= 4.
        """
        self._check_adjacent(a, b)
        if b in self._adj[a]:
            return
        self._adj[a].append(b)
        self._adj[b].append(a)

    def remove_edge(self, a: Cell, b: Cell) -> None:
        """Close the passage between two cells (put the wall back).

        Removing an edge that does not exist does nothing.

        Args:
            a: First cell.
            b: Second cell; must be a grid neighbor of ``a``.

        Returns:
            None.

        Raises:
            ValueError: If the cells are out of bounds or not orthogonally adjacent.

        Concept: Graph Theory — removing edge {a, b} from E.
        Complexity: O(deg(a) + deg(b)) = O(1) since deg <= 4.
        """
        self._check_adjacent(a, b)
        if b not in self._adj[a]:
            return
        self._adj[a].remove(b)
        self._adj[b].remove(a)

    def neighbors(self, cell: Cell) -> list[Cell]:
        """Return the cells reachable from ``cell`` through an open passage.

        Args:
            cell: The vertex whose neighborhood is requested.

        Returns:
            A new list of adjacent cells N(cell) in the maze graph; changing it
            does not change the maze.

        Raises:
            ValueError: If the cell is outside the grid.

        Concept: Graph Theory — open neighborhood N(v) in an adjacency list.
        Complexity: O(deg(v)) to copy = O(1) since deg <= 4.
        """
        if not self._in_bounds(cell):
            raise ValueError(f"Cell {cell} out of bounds for {self.rows} x {self.cols} grid")
        return list(self._adj[cell])

    def has_edge(self, a: Cell, b: Cell) -> bool:
        """Check whether a passage exists between two cells.

        Never raises: cells outside the grid simply have no edges, so the player
        module can test a move into the outer wall safely.

        Args:
            a: First cell.
            b: Second cell.

        Returns:
            True if {a, b} is in E, otherwise False.

        Concept: Graph Theory — edge membership test.
        Complexity: O(deg(a)) = O(1) since deg <= 4.
        """
        return b in self._adj.get(a, [])

    def vertex_count(self) -> int:
        """Return |V|, the number of cells.

        Args:
            None.

        Returns:
            Number of vertices.

        Concept: Graph Theory — order of the graph |V|.
        Complexity: O(1).
        """
        return len(self._adj)

    def edge_count(self) -> int:
        """Return |E|, the number of open passages.

        Args:
            None.

        Returns:
            Number of undirected edges (each edge counted once).

        Concept: Graph Theory — Handshake Lemma: |E| = (sum of degrees) / 2,
        because every edge {a, b} appears in both adj[a] and adj[b].
        Complexity: O(|V|).
        """
        degree_sum = sum(len(adjacent) for adjacent in self._adj.values())
        return degree_sum // 2

    def grid_neighbors(self, cell: Cell) -> list[Cell]:
        """Return the up-to-4 orthogonal grid neighbors of ``cell``, bounds-checked.

        Passages are ignored: this describes the underlying grid graph, not the maze.

        Args:
            cell: The cell whose grid neighbors are requested.

        Returns:
            List of in-bounds cells at (r-1,c), (r+1,c), (r,c-1), (r,c+1), in that order.

        Concept: Graph Theory — neighborhood in the rows x cols grid graph P_m x P_n.
        Complexity: O(1).
        """
        r, c = cell
        candidates = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
        return [n for n in candidates if self._in_bounds(n)]

    def to_dict(self) -> Graph:
        """Export the maze as a plain adjacency-list dictionary.

        Both the dict and every neighbor list are copies, so callers cannot
        mutate the maze through the result.

        Args:
            None.

        Returns:
            A ``Graph`` (dict[Cell, list[Cell]]) copy of the adjacency list.

        Concept: Graph Theory — adjacency-list representation.
        Complexity: O(|V| + |E|).
        """
        return {cell: list(adjacent) for cell, adjacent in self._adj.items()}

    def __repr__(self) -> str:
        """Return a short summary such as ``MazeGraph(rows=3, cols=4, V=12, E=11)``.

        Args:
            None.

        Returns:
            A string with the grid size and the vertex and edge counts.

        Concept: Graph Theory — order |V| and size |E| of the graph.
        Complexity: O(|V|) (because of edge_count).
        """
        return (
            f"MazeGraph(rows={self.rows}, cols={self.cols}, "
            f"V={self.vertex_count()}, E={self.edge_count()})"
        )
