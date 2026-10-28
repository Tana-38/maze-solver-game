"""Standalone BFS-vs-DFS race demo for Role 3 (visualizer + animation).

Uses the real maze generator (Role 1). Role 2's bfs/dfs are used once they are
implemented; until then small stand-in searches below produce the same
SearchResult so the UI can be tried on its own.

Run:  python scripts/ui_demo.py
Keys: SPACE pause | R restart | N new maze | UP/DOWN speed | ESC quit

DEMO_HEADLESS_FRAMES=N runs N frames, prints the comparison and saves a
screenshot to DEMO_SHOT (default demo.png); combine with SDL_VIDEODRIVER=dummy
to run without a window.
"""

from __future__ import annotations

import os
import sys
import time
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame

from src.algorithms import solvers
from src.algorithms.solvers import SearchResult
from src.config import COLOR_BG, FPS, GRID_COLS, GRID_ROWS
from src.maze.generator import generate_maze_dfs, pick_start_and_goal
from src.maze.graph import Cell, MazeGraph
from src.ui.animation import SolverRace
from src.ui.visualizer import MazeRenderer


def _stand_in_bfs(graph: MazeGraph, start: Cell, goal: Cell) -> tuple[list[Cell], dict[Cell, Cell | None]]:
    parent: dict[Cell, Cell | None] = {start: None}
    order: list[Cell] = []
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        order.append(cell)
        if cell == goal:
            break
        for nb in graph.neighbors(cell):
            if nb not in parent:
                parent[nb] = cell
                queue.append(nb)
    return order, parent


def _stand_in_dfs(graph: MazeGraph, start: Cell, goal: Cell) -> tuple[list[Cell], dict[Cell, Cell | None]]:
    parent: dict[Cell, Cell | None] = {start: None}
    order: list[Cell] = []
    visited: set[Cell] = set()
    stack = [start]
    while stack:
        cell = stack.pop()
        if cell in visited:
            continue
        visited.add(cell)
        order.append(cell)
        if cell == goal:
            break
        for nb in graph.neighbors(cell):
            if nb not in visited:
                parent[nb] = cell
                stack.append(nb)
    return order, parent


def _stand_in_search(name: str, graph: MazeGraph, start: Cell, goal: Cell) -> SearchResult:
    began = time.perf_counter()
    search = _stand_in_bfs if name == "bfs" else _stand_in_dfs
    order, parent = search(graph, start, goal)
    path = None
    if order and order[-1] == goal:
        path, cell = [], goal
        while cell is not None:
            path.append(cell)
            cell = parent[cell]
        path.reverse()
    return SearchResult(path, len(order), order, (time.perf_counter() - began) * 1000)


def run_search(name: str, graph: MazeGraph, start: Cell, goal: Cell) -> SearchResult:
    """Role 2's solver if implemented, otherwise the stand-in."""
    try:
        return getattr(solvers, name)(graph, start, goal)
    except NotImplementedError:
        return _stand_in_search(name, graph, start, goal)


def main(headless_frames: int = 0) -> None:
    pygame.init()
    pygame.display.set_caption("Maze Solver - BFS vs DFS race")
    screen = pygame.display.set_mode((1200, 680))
    clock = pygame.time.Clock()

    def new_race(seed: int | None = None) -> tuple[SolverRace, MazeRenderer, dict[str, SearchResult]]:
        graph = generate_maze_dfs(GRID_ROWS, GRID_COLS, seed=seed)
        start, goal = pick_start_and_goal(graph)
        renderer = MazeRenderer(screen, graph)
        results = {name: run_search(name, graph, start, goal) for name in ("bfs", "dfs")}
        return SolverRace(renderer, results["bfs"], results["dfs"]), renderer, results

    race, renderer, results = new_race(seed=7 if headless_frames else None)
    speed, paused, frames = 30, False, 0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    race.reset()
                elif event.key == pygame.K_n:
                    race, renderer, results = new_race()
                    race.set_speed(speed)
                elif event.key == pygame.K_UP:
                    speed = min(600, speed * 2)
                    race.set_speed(speed)
                elif event.key == pygame.K_DOWN:
                    speed = max(1, speed // 2)
                    race.set_speed(speed)
        if not paused:
            race.step()
        screen.fill(COLOR_BG)
        race.draw()
        if race.done:
            renderer.draw_comparison_panel(results)
        pygame.display.flip()
        clock.tick(FPS)
        frames += 1
        if headless_frames and frames >= headless_frames:
            break
    if headless_frames:
        for name, result in results.items():
            print(name, result.explored_count, len(result.path or []) - 1)
        pygame.image.save(screen, os.environ.get("DEMO_SHOT", "demo.png"))
    pygame.quit()


if __name__ == "__main__":
    main(int(os.environ.get("DEMO_HEADLESS_FRAMES", "0")))
