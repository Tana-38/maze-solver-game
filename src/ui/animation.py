"""Frame-by-frame animation of search algorithms.

Owner: Role 3 — Visualization & Animation.

Animations replay SearchResult.explored_order one cell per step, then draw
the final path, so viewers can see how BFS spreads in layers while DFS dives deep.

Each animator separates advancing from drawing: call step() from the update
phase and draw() from the render phase, because the main loop clears the
screen in between.
"""

from __future__ import annotations

import pygame

from src.algorithms.solvers import SearchResult
from src.config import COLOR_BFS_PATH, COLOR_DFS_PATH, COLOR_EXPLORED, COLOR_START, FPS, WINDOW_PADDING
from src.ui.visualizer import Color, MazeRenderer

MIN_SPEED = 1
MAX_SPEED = 2000
PANEL_RESERVE = 100  # pixels kept free below the race for the comparison panel


class SearchAnimator:
    """Replays a single search's exploration order on the renderer."""

    def __init__(
        self,
        renderer: MazeRenderer,
        search_result: SearchResult,
        speed: int = 30,
        color: Color = COLOR_BFS_PATH,
    ) -> None:
        """Create an animator for one search result.

        Args:
            renderer: Renderer used for drawing.
            search_result: The search to replay.
            speed: Cells revealed per second.
            color: Color of the current frontier cell and the final path.

        Returns:
            None.

        Concept: BFS/DFS — replays the order in which vertices were visited.
        Complexity: O(1).
        """
        self.renderer = renderer
        self.result = search_result
        self.order = search_result.explored_order
        self.path = search_result.path or []
        self.color = color
        self.set_speed(speed)
        self.reset()

    @property
    def explored_count(self) -> int:
        """Number of explored cells revealed so far."""
        return self.index

    @property
    def search_finished(self) -> bool:
        """True once every explored cell has been revealed."""
        return self.index >= len(self.order)

    @property
    def done(self) -> bool:
        """True once the explored cells and the whole path have been revealed."""
        return self.search_finished and self.path_progress >= len(self.path)

    def step(self) -> bool:
        """Advance the animation by one frame (call draw() to render it).

        The animation reveals ``speed / FPS`` cells per frame on average; the
        fractional part carries over, so slow speeds still progress smoothly.
        Explored cells are revealed first, then the path cells.

        Args:
            None.

        Returns:
            True while the animation is still running, False once finished
            (explored cells and final path fully drawn).

        Concept: BFS/DFS — visualises the growing visited set.
        Complexity: O(1) per frame.
        """
        if self.done:
            return False
        self._budget += self.speed / FPS
        cells = int(self._budget)
        self._budget -= cells
        searched = min(cells, len(self.order) - self.index)
        self.index += searched
        self.path_progress = min(len(self.path), self.path_progress + cells - searched)
        return not self.done

    def draw(self) -> None:
        """Draw the current frame: maze, explored cells, frontier, start/goal, and revealed path.

        Start and goal are read from the search result (the path's ends, or the
        first explored cell when no path was found).

        Args:
            None.

        Returns:
            None.

        Concept: BFS/DFS — the shaded region is the visited set so far.
        Complexity: O(k) for k cells drawn so far (O(|V|) worst case).
        """
        r = self.renderer
        r.draw_grid()
        explored = self.order[: self.index]
        r.draw_explored(explored, COLOR_EXPLORED)
        if explored and not self.search_finished:
            r.draw_cell(explored[-1], self.color)
        if self.path:
            r.draw_start_and_goal(self.path[0], self.path[-1])
        elif self.order:
            r.draw_cell(self.order[0], COLOR_START)
        r.draw_walls()
        r.draw_path(self.path[: self.path_progress], self.color, width=max(2, r.cell_size // 4))

    def reset(self) -> None:
        """Restart the animation from the first explored cell.

        Args:
            None.

        Returns:
            None.

        Concept: n/a (state management).
        Complexity: O(1).
        """
        self.index = 0
        self.path_progress = 0
        self._budget = 0.0

    def set_speed(self, fps: int) -> None:
        """Change how many cells are revealed per second.

        Args:
            fps: New animation speed in cells per second, clamped to [MIN_SPEED, MAX_SPEED].

        Returns:
            None.

        Concept: n/a (state management).
        Complexity: O(1).
        """
        self.speed = max(MIN_SPEED, min(MAX_SPEED, fps))


class SolverRace:
    """Animates BFS and DFS side by side so their exploration can be compared."""

    def __init__(
        self,
        renderer: MazeRenderer,
        bfs_result: SearchResult,
        dfs_result: SearchResult,
        speed: int = 30,
    ) -> None:
        """Create a race between two search results on the same maze.

        The race builds its own two renderers (BFS on the left, DFS on the
        right) on the given renderer's screen and graph, with a smaller cell
        size so both mazes fit in the existing window, leaving room at the
        bottom for draw_comparison_panel.

        Args:
            renderer: Renderer used for drawing.
            bfs_result: Result of bfs().
            dfs_result: Result of dfs().
            speed: Cells revealed per second, for both animations.

        Returns:
            None.

        Concept: BFS vs DFS — layer-by-layer vs depth-first exploration.
        Complexity: O(|V|) to build the two renderers.
        """
        screen, graph = renderer.screen, renderer.graph
        width, height = screen.get_size()
        pad = WINDOW_PADDING
        half_width = (width - 3 * pad) // 2
        usable_height = height - 2 * pad - PANEL_RESERVE
        cell_size = max(2, min(half_width // graph.cols, usable_height // graph.rows))
        maze_width = cell_size * graph.cols

        left_x = pad + (half_width - maze_width) // 2
        right_x = 2 * pad + half_width + (half_width - maze_width) // 2
        top_y = pad + (usable_height - cell_size * graph.rows) // 2
        left = MazeRenderer(screen, graph, cell_size, origin=(left_x, top_y))
        right = MazeRenderer(screen, graph, cell_size, origin=(right_x, top_y))

        self.bfs = SearchAnimator(left, bfs_result, speed, COLOR_BFS_PATH)
        self.dfs = SearchAnimator(right, dfs_result, speed, COLOR_DFS_PATH)

    @property
    def done(self) -> bool:
        """True once both animations have finished."""
        return self.bfs.done and self.dfs.done

    def step(self) -> bool:
        """Advance both animations by one frame (call draw() to render them).

        Args:
            None.

        Returns:
            True while either animation is still running, False when both are finished.

        Concept: BFS vs DFS — compares explored-cell counts visually.
        Complexity: O(1) per frame.
        """
        bfs_running = self.bfs.step()
        dfs_running = self.dfs.step()
        return bfs_running or dfs_running

    def draw(self) -> None:
        """Draw both mazes with a label and live counters above each.

        Args:
            None.

        Returns:
            None.

        Concept: BFS vs DFS — explored-cell counts update as each search spreads.
        Complexity: O(|V|) per frame worst case.
        """
        for name, anim in (("BFS", self.bfs), ("DFS", self.dfs)):
            anim.draw()
            renderer = anim.renderer
            label = f"{name}  explored {anim.explored_count}"
            if anim.search_finished:
                label += f"  path {len(anim.path) - 1 if anim.path else '-'}"
            x, y = renderer.maze_rect.topleft
            text_y = y - renderer.font.get_linesize() - 6
            swatch = pygame.Rect(x, text_y + 3, 12, 12)
            pygame.draw.rect(renderer.screen, anim.color, swatch)
            renderer.draw_text(label, (x + 18, text_y))

    def reset(self) -> None:
        """Restart both animations."""
        self.bfs.reset()
        self.dfs.reset()

    def set_speed(self, fps: int) -> None:
        """Change the speed of both animations, in cells per second."""
        self.bfs.set_speed(fps)
        self.dfs.set_speed(fps)
