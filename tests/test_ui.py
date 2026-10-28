"""Tests for src/ui/visualizer.py and src/ui/animation.py.

Owner: Role 3 — Visualization & Animation.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from src.algorithms.solvers import SearchResult
from src.config import CELL_SIZE, WINDOW_PADDING
from src.maze.generator import generate_maze_dfs
from src.ui.animation import SearchAnimator, SolverRace
from src.ui.visualizer import MazeRenderer, cell_to_pixel, pixel_to_cell


@pytest.fixture
def renderer() -> MazeRenderer:
    pygame.init()
    screen = pygame.display.set_mode((400, 300))
    yield MazeRenderer(screen, generate_maze_dfs(5, 6, seed=1))
    pygame.quit()


def _result(order, path) -> SearchResult:
    return SearchResult(path=path, explored_count=len(order), explored_order=order)


def test_cell_to_pixel_and_back() -> None:
    """pixel_to_cell inverts cell_to_pixel anywhere inside the cell."""
    assert cell_to_pixel((2, 3)) == (WINDOW_PADDING + 3 * CELL_SIZE, WINDOW_PADDING + 2 * CELL_SIZE)
    x, y = cell_to_pixel((2, 3))
    assert pixel_to_cell((x, y), 5, 6) == (2, 3)
    assert pixel_to_cell((x + CELL_SIZE - 1, y + CELL_SIZE - 1), 5, 6) == (2, 3)


def test_pixel_to_cell_outside_maze_is_none() -> None:
    """Clicks in the padding or past the last row/column map to no cell."""
    assert pixel_to_cell((0, 0), 5, 6) is None
    assert pixel_to_cell((WINDOW_PADDING - 1, WINDOW_PADDING), 5, 6) is None
    assert pixel_to_cell(cell_to_pixel((5, 0)), 5, 6) is None
    assert pixel_to_cell(cell_to_pixel((0, 6)), 5, 6) is None


def test_walls_match_missing_edges(renderer: MazeRenderer) -> None:
    """A spanning tree on R x C cells has (R-1)C + R(C-1) grid edges, |V|-1 of them open."""
    g = renderer.graph
    grid_edges = (g.rows - 1) * g.cols + g.rows * (g.cols - 1)
    assert len(renderer._walls) == grid_edges - g.edge_count()


def test_animator_reveals_search_then_path(renderer: MazeRenderer) -> None:
    """At 1 cell per frame the explored cells come first, then the path, then step() returns False."""
    order = [(0, 0), (0, 1), (1, 1)]
    anim = SearchAnimator(renderer, _result(order, [(0, 0), (0, 1)]))
    anim.set_speed(60)  # FPS = 60, so one cell per frame
    frames = 0
    while anim.step():
        frames += 1
        anim.draw()
    assert frames + 1 == len(order) + 2
    assert anim.explored_count == 3 and anim.path_progress == 2 and anim.done


def test_animator_handles_no_path(renderer: MazeRenderer) -> None:
    """A search that never reached the goal (path None) still animates and finishes."""
    anim = SearchAnimator(renderer, _result([(0, 0), (1, 0)], None), speed=600)
    while anim.step():
        pass
    anim.draw()
    assert anim.done and anim.path == []


def test_reset_and_speed_clamp(renderer: MazeRenderer) -> None:
    """reset() rewinds to the start; set_speed clamps nonsense values."""
    anim = SearchAnimator(renderer, _result([(0, 0), (0, 1)], [(0, 0), (0, 1)]), speed=600)
    anim.step()
    anim.reset()
    assert anim.explored_count == 0 and anim.path_progress == 0
    anim.set_speed(-5)
    assert anim.speed >= 1


def test_race_finishes_and_fits_on_screen(renderer: MazeRenderer) -> None:
    """Both mazes fit inside the window and the race ends when both animations do."""
    long_order = [(r, c) for r in range(5) for c in range(6)]
    race = SolverRace(renderer, _result([(0, 0)], [(0, 0)]), _result(long_order, [(0, 0)]), speed=600)
    screen_rect = renderer.screen.get_rect()
    for anim in (race.bfs, race.dfs):
        assert screen_rect.contains(anim.renderer.maze_rect)
    assert not race.bfs.renderer.maze_rect.colliderect(race.dfs.renderer.maze_rect)
    while race.step():
        race.draw()
    assert race.done
    renderer.draw_comparison_panel({"bfs": race.bfs.result, "dfs": race.dfs.result})
