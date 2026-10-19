"""Static drawing of the maze, paths, player, and HUD with pygame.

Owner: Role 3 — Visualization & Animation.

Walls are drawn wherever two grid-adjacent cells are NOT joined by an edge,
so the picture is a direct drawing of the complement of E within the grid graph.
"""

from __future__ import annotations

import pygame

from src.algorithms.solvers import SearchResult
from src.config import CELL_SIZE, WINDOW_PADDING
from src.maze.graph import Cell, MazeGraph

Color = tuple[int, int, int]


class MazeRenderer:
    """Draws a MazeGraph and overlays onto a pygame surface."""

    def __init__(self, screen: pygame.Surface, graph: MazeGraph, cell_size: int = CELL_SIZE) -> None:
        """Create a renderer bound to a surface and a maze.

        Args:
            screen: The pygame surface to draw on.
            graph: The maze to draw.
            cell_size: Side length of one cell in pixels.

        Returns:
            None.

        Concept: n/a (rendering setup).
        Complexity: O(1).
        """
        raise NotImplementedError("TODO: Role 3 — store screen, graph, cell_size and create a pygame font for the HUD")

    def draw_grid(self) -> None:
        """Fill the background and draw every cell.

        Args:
            None.

        Returns:
            None.

        Concept: Graph Theory — draws every vertex of V.
        Complexity: O(|V|).
        """
        raise NotImplementedError("TODO: Role 3 — fill COLOR_BG and draw each cell rectangle")

    def draw_walls(self) -> None:
        """Draw a wall segment between grid neighbors that have no passage.

        Args:
            None.

        Returns:
            None.

        Concept: Graph Theory — walls = grid-graph edges not in the maze's edge set E.
        Complexity: O(|V|) (each cell checks at most 4 grid neighbors).
        """
        raise NotImplementedError("TODO: Role 3 — for each cell, draw a line on sides where has_edge(cell, neighbor) is False, plus the outer border")

    def draw_cell(self, cell: Cell, color: Color) -> None:
        """Fill a single cell with a color.

        Args:
            cell: The cell to fill.
            color: RGB fill color.

        Returns:
            None.

        Concept: n/a (rendering a vertex).
        Complexity: O(1).
        """
        raise NotImplementedError("TODO: Role 3 — draw a filled rect at cell_to_pixel(cell)")

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
        raise NotImplementedError("TODO: Role 3 — pygame.draw.lines through the centers of the path cells")

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
        raise NotImplementedError("TODO: Role 3 — draw_cell(start, COLOR_START) and draw_cell(goal, COLOR_GOAL)")

    def draw_player(self, cell: Cell) -> None:
        """Draw the player marker on a cell.

        Args:
            cell: The player's current cell.

        Returns:
            None.

        Concept: n/a (rendering).
        Complexity: O(1).
        """
        raise NotImplementedError("TODO: Role 3 — draw a COLOR_PLAYER circle at the cell center")

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
        raise NotImplementedError("TODO: Role 3 — draw_cell for each explored cell")

    def draw_hud(self, text_lines: list[str]) -> None:
        """Render status text (moves, timer, mode, etc.) in the HUD area.

        Args:
            text_lines: Lines of text to display, top to bottom.

        Returns:
            None.

        Concept: n/a (rendering).
        Complexity: O(len(text_lines)).
        """
        raise NotImplementedError("TODO: Role 3 — blit each line with the HUD font in the padding area")

    def draw_comparison_panel(self, results: dict[str, SearchResult]) -> None:
        """Draw a panel comparing algorithms by explored cells, path length, and runtime.

        Args:
            results: Mapping algorithm name -> SearchResult (from compare_algorithms).

        Returns:
            None.

        Concept: Algorithm analysis — BFS vs DFS explored count and path length.
        Complexity: O(k) for k algorithms.
        """
        raise NotImplementedError("TODO: Role 3 — draw a table/bar chart of explored_count, path length, runtime_ms per algorithm")


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
    raise NotImplementedError("TODO: Role 3 — return (padding + col * cell_size, padding + row * cell_size)")


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
    raise NotImplementedError("TODO: Role 3 — integer-divide the offset by cell_size and bounds-check")
