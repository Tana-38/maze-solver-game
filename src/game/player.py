"""Player state and movement validation for the interactive game mode.

Owner: Role 4 — Game Logic & Integration.

A move is legal only if the corresponding edge exists in the maze graph, i.e.
the player walks along edges of G and cannot pass through walls.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.maze.graph import Cell, MazeGraph

# direction name -> (row delta, column delta)
DIRECTIONS: dict[str, tuple[int, int]] = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}


@dataclass
class PlayerState:
    """Mutable state of the human player.

    Attributes:
        current: The cell the player is standing on.
        path: Every cell visited, in order (the player's walk in the graph).
        moves: Number of successful moves made.
        backtracks: Number of moves that returned to the previously visited cell.
        hints_used: Number of hints requested.
    """

    current: Cell
    path: list[Cell] = field(default_factory=list)
    moves: int = 0
    backtracks: int = 0
    hints_used: int = 0


class PlayerController:
    """Applies keyboard input to the player while enforcing the maze's walls."""

    def __init__(self, graph: MazeGraph, start: Cell, goal: Cell) -> None:
        """Create a controller with the player placed on the start cell.

        Args:
            graph: The maze graph the player moves in.
            start: Starting cell.
            goal: Destination cell.

        Returns:
            None.

        Concept: Graph Theory — the player performs a walk on G starting at `start`.
        Complexity: O(1).
        """
        self.graph = graph
        self.start = start
        self.goal = goal
        self.state = PlayerState(current=start, path=[start])

    def try_move(self, direction: str) -> bool:
        """Attempt to move one cell in the given direction.

        Args:
            direction: One of "up", "down", "left", "right".

        Returns:
            True if the move was legal and applied, False if blocked by a wall.

        Concept: Graph Theory — traversing edge {current, target} only if it exists in E.
        Complexity: O(1).
        """
        if direction not in DIRECTIONS:
            raise ValueError(f"Unknown direction {direction!r}")
        dr, dc = DIRECTIONS[direction]
        row, col = self.state.current
        target = (row + dr, col + dc)
        if not self.is_valid_move(target):
            return False
        if self.is_backtrack(target):
            self.state.backtracks += 1
        self.state.current = target
        self.state.path.append(target)
        self.state.moves += 1
        return True

    def is_valid_move(self, target: Cell) -> bool:
        """Check whether the player may step onto ``target``.

        Args:
            target: The cell the player wants to move to.

        Returns:
            True if an edge (passage) exists between the current cell and target.

        Concept: Graph Theory — adjacency test in the maze graph.
        Complexity: O(1) (degree <= 4).
        """
        return self.graph.has_edge(self.state.current, target)

    def is_backtrack(self, target: Cell) -> bool:
        """Check whether moving to ``target`` returns to the previously visited cell.

        Args:
            target: The cell the player wants to move to.

        Returns:
            True if target equals the second-to-last cell of the player's path.

        Concept: Graph Theory / DFS — backtracking along the last traversed edge.
        Complexity: O(1).
        """
        return len(self.state.path) >= 2 and self.state.path[-2] == target

    def has_reached_goal(self) -> bool:
        """Check whether the player is standing on the goal cell.

        Args:
            None.

        Returns:
            True if current == goal.

        Concept: Graph Theory — the walk has reached the target vertex.
        Complexity: O(1).
        """
        return self.state.current == self.goal

    def request_hint(self, bfs_path: list[Cell]) -> Cell | None:
        """Suggest the next cell to move to and count the hint.

        Args:
            bfs_path: Shortest path from the player's current cell to the goal
                (computed by BFS), including the current cell.

        Returns:
            The next cell on the optimal path, or None if already at the goal.

        Concept: BFS — the shortest path gives the optimal next step.
        Complexity: O(1) given the path.
        """
        self.state.hints_used += 1
        return bfs_path[1] if len(bfs_path) > 1 else None

    def reset(self) -> None:
        """Put the player back on the start cell and clear all counters.

        Args:
            None.

        Returns:
            None.

        Concept: n/a (state management).
        Complexity: O(1).
        """
        self.state = PlayerState(current=self.start, path=[self.start])
