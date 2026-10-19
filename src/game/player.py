"""Player state and movement validation for the interactive game mode.

Owner: Role 4 — Game Logic & Integration.

A move is legal only if the corresponding edge exists in the maze graph, i.e.
the player walks along edges of G and cannot pass through walls.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.maze.graph import Cell, MazeGraph


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
        raise NotImplementedError("TODO: Role 4 — store graph/start/goal and create a PlayerState at start")

    def try_move(self, direction: str) -> bool:
        """Attempt to move one cell in the given direction.

        Args:
            direction: One of "up", "down", "left", "right".

        Returns:
            True if the move was legal and applied, False if blocked by a wall.

        Concept: Graph Theory — traversing edge {current, target} only if it exists in E.
        Complexity: O(1).
        """
        raise NotImplementedError("TODO: Role 4 — map direction to target cell, validate, update state and backtrack counter")

    def is_valid_move(self, target: Cell) -> bool:
        """Check whether the player may step onto ``target``.

        Args:
            target: The cell the player wants to move to.

        Returns:
            True if an edge (passage) exists between the current cell and target.

        Concept: Graph Theory — adjacency test in the maze graph.
        Complexity: O(1) (degree <= 4).
        """
        raise NotImplementedError("TODO: Role 4 — return graph.has_edge(current, target)")

    def is_backtrack(self, target: Cell) -> bool:
        """Check whether moving to ``target`` returns to the previously visited cell.

        Args:
            target: The cell the player wants to move to.

        Returns:
            True if target equals the second-to-last cell of the player's path.

        Concept: Graph Theory / DFS — backtracking along the last traversed edge.
        Complexity: O(1).
        """
        raise NotImplementedError("TODO: Role 4 — compare target with path[-2]")

    def has_reached_goal(self) -> bool:
        """Check whether the player is standing on the goal cell.

        Args:
            None.

        Returns:
            True if current == goal.

        Concept: Graph Theory — the walk has reached the target vertex.
        Complexity: O(1).
        """
        raise NotImplementedError("TODO: Role 4 — return state.current == goal")

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
        raise NotImplementedError("TODO: Role 4 — increment hints_used and return bfs_path[1] if it exists")

    def reset(self) -> None:
        """Put the player back on the start cell and clear all counters.

        Args:
            None.

        Returns:
            None.

        Concept: n/a (state management).
        Complexity: O(1).
        """
        raise NotImplementedError("TODO: Role 4 — replace state with a fresh PlayerState at start")
