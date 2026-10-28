"""Static drawing of the maze, paths, player, and HUD with pygame.

Owner: Role 3 — Visualization & Animation.

Walls are drawn wherever two grid-adjacent cells are NOT joined by an edge,
so the picture is a direct drawing of the complement of E within the grid graph.
"""

from __future__ import annotations

import pygame

from src.algorithms.solvers import SearchResult
from src.config import (
    CELL_SIZE,
    COLOR_BG,
    COLOR_GOAL,
    COLOR_PLAYER,
    COLOR_START,
    COLOR_WALL,
    WALL_THICKNESS,
    WINDOW_PADDING,
)
from src.maze.graph import Cell, MazeGraph

Color = tuple[int, int, int]

HUD_FONT_SIZE = 18
HUD_FONT_NAMES = "consolas,menlo,dejavusansmono"  # monospace keeps table columns aligned


class MazeRenderer:
    """Draws a MazeGraph and overlays onto a pygame surface."""

    def __init__(
        self,
        screen: pygame.Surface,
        graph: MazeGraph,
        cell_size: int = CELL_SIZE,
        origin: tuple[int, int] = (WINDOW_PADDING, WINDOW_PADDING),
    ) -> None:
        """Create a renderer bound to a surface and a maze.

        Wall segments are computed once here, so create a new renderer if the
        graph's edges change afterwards.

        Args:
            screen: The pygame surface to draw on.
            graph: The maze to draw.
            cell_size: Side length of one cell in pixels.
            origin: Pixel position of the maze's top-left corner. The default
                matches cell_to_pixel; SolverRace passes other origins to draw
                two mazes side by side.

        Returns:
            None.

        Concept: Graph Theory — walls are the grid-graph edges missing from E.
        Complexity: O(|V|) to precompute the wall segments.
        """
        self.screen = screen
        self.graph = graph
        self.cell_size = cell_size
        self.origin = origin
        self.font = pygame.font.SysFont(HUD_FONT_NAMES, HUD_FONT_SIZE)
        self._walls = self._build_walls()

    @property
    def maze_rect(self) -> pygame.Rect:
        """Pixel rectangle covered by the maze."""
        x, y = self.origin
        return pygame.Rect(x, y, self.graph.cols * self.cell_size, self.graph.rows * self.cell_size)

    def cell_rect(self, cell: Cell) -> pygame.Rect:
        """Pixel rectangle of one cell."""
        x, y = self.origin
        r, c = cell
        return pygame.Rect(x + c * self.cell_size, y + r * self.cell_size, self.cell_size, self.cell_size)

    def cell_center(self, cell: Cell) -> tuple[int, int]:
        """Pixel center of one cell."""
        return self.cell_rect(cell).center

    def _build_walls(self) -> list[tuple[tuple[int, int], tuple[int, int]]]:
        """Return line segments for every interior wall (the outer border is drawn separately).

        Only the right and bottom side of each cell is checked, so each interior
        wall is produced exactly once.
        """
        segments = []
        for r in range(self.graph.rows):
            for c in range(self.graph.cols):
                rect = self.cell_rect((r, c))
                if c + 1 < self.graph.cols and not self.graph.has_edge((r, c), (r, c + 1)):
                    segments.append((rect.topright, rect.bottomright))
                if r + 1 < self.graph.rows and not self.graph.has_edge((r, c), (r + 1, c)):
                    segments.append((rect.bottomleft, rect.bottomright))
        return segments

    def draw_grid(self) -> None:
        """Fill the background and draw every cell.

        Only the maze's own rectangle is filled, so two renderers can share one
        screen (the main loop clears the whole window each frame).

        Args:
            None.

        Returns:
            None.

        Concept: Graph Theory — draws every vertex of V.
        Complexity: O(|V|).
        """
        pygame.draw.rect(self.screen, COLOR_BG, self.maze_rect)

    def draw_walls(self) -> None:
        """Draw a wall segment between grid neighbors that have no passage.

        Args:
            None.

        Returns:
            None.

        Concept: Graph Theory — walls = grid-graph edges not in the maze's edge set E.
        Complexity: O(|V|) (each cell checks at most 4 grid neighbors).
        """
        for start, end in self._walls:
            pygame.draw.line(self.screen, COLOR_WALL, start, end, WALL_THICKNESS)
        box = self.maze_rect
        corners = [box.topleft, box.topright, box.bottomright, box.bottomleft]
        pygame.draw.lines(self.screen, COLOR_WALL, True, corners, WALL_THICKNESS)

    def draw_cell(self, cell: Cell, color: Color) -> None:
        """Fill a single cell with a color.

        The fill is inset by the wall thickness so walls stay visible whichever
        is drawn first.

        Args:
            cell: The cell to fill.
            color: RGB fill color.

        Returns:
            None.

        Concept: n/a (rendering a vertex).
        Complexity: O(1).
        """
        inset = 2 * WALL_THICKNESS
        pygame.draw.rect(self.screen, color, self.cell_rect(cell).inflate(-inset, -inset))

    def draw_path(self, path: list[Cell], color: Color, width: int = 4) -> None:
        """Draw a path as a polyline through cell centers.

        Args:
            path: Sequence of cells (consecutive cells must be adjacent).
            color: RGB line color.
            width: Line width in pixels.

        Returns:
            None.

        Concept: Graph Theory — visualises a path (sequence of edges) in G.
        Complexity: O(len(path)).
        """
        if len(path) < 2:
            return
        pygame.draw.lines(self.screen, color, False, [self.cell_center(c) for c in path], width)

    def draw_start_and_goal(self, start: Cell, goal: Cell) -> None:
        """Highlight the start and goal cells.

        Args:
            start: Starting cell.
            goal: Destination cell.

        Returns:
            None.

        Concept: n/a (rendering).
        Complexity: O(1).
        """
        self.draw_cell(start, COLOR_START)
        self.draw_cell(goal, COLOR_GOAL)

    def draw_player(self, cell: Cell) -> None:
        """Draw the player marker on a cell.

        Args:
            cell: The player's current cell.

        Returns:
            None.

        Concept: n/a (rendering).
        Complexity: O(1).
        """
        radius = max(2, int(self.cell_size * 0.35))
        pygame.draw.circle(self.screen, COLOR_PLAYER, self.cell_center(cell), radius)

    def draw_explored(self, cells: list[Cell], color: Color) -> None:
        """Shade every cell a search algorithm has explored.

        Args:
            cells: Explored cells (e.g. a prefix of SearchResult.explored_order).
            color: RGB shade color.

        Returns:
            None.

        Concept: BFS/DFS — visualises the visited set / search frontier.
        Complexity: O(len(cells)).
        """
        for cell in cells:
            self.draw_cell(cell, color)

    def draw_hud(self, text_lines: list[str]) -> None:
        """Render status text (moves, timer, mode, etc.) in the HUD area.

        Lines start at the top-left of the window; the default 40 px padding
        fits two lines above the maze.

        Args:
            text_lines: Lines of text to display, top to bottom.

        Returns:
            None.

        Concept: n/a (rendering).
        Complexity: O(len(text_lines)).
        """
        line_height = self.font.get_linesize()
        for i, line in enumerate(text_lines):
            self.draw_text(line, (8, 2 + i * line_height))

    def draw_text(self, text: str, pos: tuple[int, int], color: Color = COLOR_WALL) -> pygame.Rect:
        """Blit one line of text with its top-left corner at ``pos`` and return its rectangle."""
        image = self.font.render(text, True, color)
        return self.screen.blit(image, pos)

    def draw_comparison_panel(self, results: dict[str, SearchResult]) -> None:
        """Draw a panel comparing algorithms by explored cells, path length, and runtime.

        The panel sits at the bottom of the window. When both "bfs" and "dfs"
        are present, a final line states which explored fewer cells and whether
        their paths have the same length.

        Args:
            results: Mapping algorithm name -> SearchResult (from compare_algorithms).

        Returns:
            None.

        Concept: Algorithm analysis — BFS vs DFS explored count and path length.
        Complexity: O(k) for k algorithms.
        """
        lines = [f"{'algorithm':<10}{'explored':>9}{'path':>7}{'time':>11}"]
        for name, result in results.items():
            lines.append(
                f"{name.upper():<10}{result.explored_count:>9}"
                f"{_path_length_text(result):>7}{result.runtime_ms:>8.2f} ms"
            )
        if "bfs" in results and "dfs" in results:
            lines.append(_verdict(results["bfs"], results["dfs"]))

        line_height = self.font.get_linesize()
        width = max(self.font.size(line)[0] for line in lines) + 16
        height = len(lines) * line_height + 12
        screen_w, screen_h = self.screen.get_size()
        panel = pygame.Rect(0, 0, width, height)
        panel.midbottom = (screen_w // 2, screen_h - 4)

        background = pygame.Surface(panel.size, pygame.SRCALPHA)
        background.fill((*COLOR_BG, 235))
        self.screen.blit(background, panel.topleft)
        pygame.draw.rect(self.screen, COLOR_WALL, panel, 1)
        for i, line in enumerate(lines):
            self.draw_text(line, (panel.x + 8, panel.y + 6 + i * line_height))


def _path_length_text(result: SearchResult) -> str:
    """Path length in moves (edges), or '-' when no path was found."""
    return "-" if result.path is None else str(len(result.path) - 1)


def _verdict(bfs_result: SearchResult, dfs_result: SearchResult) -> str:
    """One-line summary of the BFS-vs-DFS comparison."""
    bfs_n, dfs_n = bfs_result.explored_count, dfs_result.explored_count
    if bfs_n < dfs_n:
        msg = f"BFS explored fewer cells ({bfs_n} vs {dfs_n})"
    elif dfs_n < bfs_n:
        msg = f"DFS explored fewer cells ({dfs_n} vs {bfs_n})"
    else:
        msg = f"Both explored {bfs_n} cells"
    if bfs_result.path is None or dfs_result.path is None:
        return msg
    bfs_len, dfs_len = len(bfs_result.path) - 1, len(dfs_result.path) - 1
    if bfs_len == dfs_len:
        return f"{msg}; same path length ({bfs_len})"
    return f"{msg}; BFS path is shorter ({bfs_len} vs {dfs_len})"


def cell_to_pixel(cell: Cell, cell_size: int = CELL_SIZE, padding: int = WINDOW_PADDING) -> tuple[int, int]:
    """Convert a grid cell to the pixel coordinates of its top-left corner.

    Args:
        cell: (row, col) cell.
        cell_size: Side length of one cell in pixels.
        padding: Window padding in pixels.

    Returns:
        (x, y) pixel coordinates.

    Concept: n/a (coordinate mapping) — row maps to y, col maps to x.
    Complexity: O(1).
    """
    row, col = cell
    return padding + col * cell_size, padding + row * cell_size


def pixel_to_cell(
    pos: tuple[int, int],
    rows: int,
    cols: int,
    cell_size: int = CELL_SIZE,
    padding: int = WINDOW_PADDING,
) -> Cell | None:
    """Convert a pixel position (e.g. a mouse click) to the grid cell under it.

    Args:
        pos: (x, y) pixel position.
        rows: Number of grid rows (for bounds checking).
        cols: Number of grid columns (for bounds checking).
        cell_size: Side length of one cell in pixels.
        padding: Window padding in pixels.

    Returns:
        The (row, col) cell, or None if the position is outside the maze.

    Concept: n/a (inverse coordinate mapping).
    Complexity: O(1).
    """
    x, y = pos[0] - padding, pos[1] - padding
    if x < 0 or y < 0:
        return None
    row, col = y // cell_size, x // cell_size
    if row >= rows or col >= cols:
        return None
    return row, col
