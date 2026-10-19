"""Frame-by-frame animation of search algorithms.

Owner: Role 3 — Visualization & Animation.

Animations replay SearchResult.explored_order one cell per step, then draw
the final path, so viewers can see how BFS spreads in layers while DFS dives deep.
"""

from __future__ import annotations

from src.algorithms.solvers import SearchResult
from src.ui.visualizer import MazeRenderer


class SearchAnimator:
    """Replays a single search's exploration order on the renderer."""

    def __init__(self, renderer: MazeRenderer, search_result: SearchResult, speed: int = 30) -> None:
        """Create an animator for one search result.

        Args:
            renderer: Renderer used for drawing.
            search_result: The search to replay.
            speed: Cells revealed per second.

        Returns:
            None.

        Concept: BFS/DFS — replays the order in which vertices were visited.
        Complexity: O(1).
        """
        raise NotImplementedError("TODO: Role 3 — store renderer, result, speed and set the frame index to 0")

    def step(self) -> bool:
        """Advance the animation by one frame and draw it.

        Args:
            None.

        Returns:
            True while the animation is still running, False once finished
            (explored cells and final path fully drawn).

        Concept: BFS/DFS — visualises the growing visited set.
        Complexity: O(k) per frame for k cells drawn so far (O(|V|) worst case).
        """
        raise NotImplementedError("TODO: Role 3 — increment index, draw explored_order[:index], draw path when done")

    def reset(self) -> None:
        """Restart the animation from the first explored cell.

        Args:
            None.

        Returns:
            None.

        Concept: n/a (state management).
        Complexity: O(1).
        """
        raise NotImplementedError("TODO: Role 3 — set the frame index back to 0")

    def set_speed(self, fps: int) -> None:
        """Change how many cells are revealed per second.

        Args:
            fps: New animation speed in cells per second.

        Returns:
            None.

        Concept: n/a (state management).
        Complexity: O(1).
        """
        raise NotImplementedError("TODO: Role 3 — update speed (clamp to a sensible range)")


class SolverRace:
    """Animates BFS and DFS side by side so their exploration can be compared."""

    def __init__(self, renderer: MazeRenderer, bfs_result: SearchResult, dfs_result: SearchResult) -> None:
        """Create a race between two search results on the same maze.

        Args:
            renderer: Renderer used for drawing.
            bfs_result: Result of bfs().
            dfs_result: Result of dfs().

        Returns:
            None.

        Concept: BFS vs DFS — layer-by-layer vs depth-first exploration.
        Complexity: O(1).
        """
        raise NotImplementedError("TODO: Role 3 — create one SearchAnimator per result (or a split-screen layout)")

    def step(self) -> bool:
        """Advance both animations by one frame.

        Args:
            None.

        Returns:
            True while either animation is still running, False when both are finished.

        Concept: BFS vs DFS — compares explored-cell counts visually.
        Complexity: O(|V|) per frame worst case.
        """
        raise NotImplementedError("TODO: Role 3 — step both animators (BFS_PATH / DFS_PATH colors) and return whether any is running")
