"""Entry point: pygame application tying generation, solving, UI, and game together.

Owner: Role 4 — Game Logic & Integration.

The app is a finite state machine (MENU, PLAYING, SOLVING, COMPARING,
GAME_OVER). Each frame runs handle_events -> update -> render.

Controls (see README): arrow keys move, H hint, S show solution, R new maze,
C comparison view, ESC back to menu. In the menu, 1/2/3 pick the difficulty
and ENTER starts a game.
"""

from __future__ import annotations

import time
from enum import Enum, auto

import pygame

from src.algorithms.solvers import bfs, compare_algorithms
from src.config import (
    CELL_SIZE,
    COLOR_BFS_PATH,
    COLOR_BG,
    COLOR_HINT,
    COLOR_PLAYER,
    COLOR_WALL,
    DIFFICULTY_LEVELS,
    FPS,
    GRID_COLS,
    GRID_ROWS,
    WINDOW_PADDING,
)
from src.game.player import PlayerController
from src.game.scoring import GameResult, compute_score
from src.maze.generator import add_braids, generate_maze_dfs, pick_start_and_goal
from src.maze.graph import Cell, MazeGraph
from src.ui.animation import SearchAnimator, SolverRace
from src.ui.visualizer import MazeRenderer

DIFFICULTY_KEYS: dict[int, str] = {
    pygame.K_1: "easy",
    pygame.K_2: "medium",
    pygame.K_3: "hard",
}

ARROW_KEYS: dict[int, str] = {
    pygame.K_UP: "up",
    pygame.K_DOWN: "down",
    pygame.K_LEFT: "left",
    pygame.K_RIGHT: "right",
}


class GameMode(Enum):
    """Top-level states of the application (a finite state machine)."""

    MENU = auto()
    PLAYING = auto()
    SOLVING = auto()
    COMPARING = auto()
    GAME_OVER = auto()


class MazeApp:
    """The pygame application: owns the window, clock, current mode, and main loop."""

    def __init__(self, rows: int = GRID_ROWS, cols: int = GRID_COLS) -> None:
        """Initialise pygame, open the window, and start in MENU mode.

        Args:
            rows: Number of maze rows.
            cols: Number of maze columns.

        Returns:
            None.

        Concept: n/a (application setup).
        Complexity: O(1).
        """
        pygame.init()
        pygame.display.set_caption("Intelligent Maze Generator and Solver")
        self.rows = rows
        self.cols = cols
        width = cols * CELL_SIZE + 2 * WINDOW_PADDING
        height = rows * CELL_SIZE + 2 * WINDOW_PADDING
        self.screen: pygame.Surface = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 28)
        self.mode: GameMode = GameMode.MENU
        self.running: bool = True
        self.difficulty: str = "medium"

        # Per-maze state, filled in by new_level().
        self.graph: MazeGraph | None = None
        self.start: Cell = (0, 0)
        self.goal: Cell = (0, 0)
        self.controller: PlayerController | None = None
        self.renderer: MazeRenderer | None = None
        self.optimal_path: list[Cell] = []
        self.hint_cell: Cell | None = None
        self.started_at: float = 0.0
        self.elapsed: float = 0.0
        self.animator: SearchAnimator | None = None
        self.race: SolverRace | None = None
        self.results: dict = {}
        self.game_result: GameResult | None = None

    def run(self) -> None:
        """Run the main loop until the window is closed.

        Args:
            None.

        Returns:
            None.

        Concept: n/a (event loop).
        Complexity: O(frames).
        """
        try:
            while self.running:
                self.handle_events()
                self.update()
                self.render()
                pygame.display.flip()
                self.clock.tick(FPS)
        finally:
            pygame.quit()

    def handle_events(self) -> None:
        """Process the pygame event queue and dispatch key presses.

        Args:
            None.

        Returns:
            None.

        Concept: n/a (input handling).
        Complexity: O(events per frame).
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.mode = GameMode.MENU
                elif event.key in DIFFICULTY_KEYS and self.mode == GameMode.MENU:
                    self.difficulty = DIFFICULTY_KEYS[event.key]
                elif event.key in ARROW_KEYS and self.mode == GameMode.PLAYING:
                    self.on_move(ARROW_KEYS[event.key])
                elif event.key == pygame.K_h and self.mode == GameMode.PLAYING:
                    self.on_hint()
                elif event.key == pygame.K_s and self.graph is not None:
                    self.on_show_solution()
                elif event.key == pygame.K_r and self.mode != GameMode.MENU:
                    self.on_new_maze()
                elif event.key == pygame.K_c and self.graph is not None:
                    self.on_compare()
                elif event.key == pygame.K_RETURN and self.mode == GameMode.MENU:
                    self.on_start_game()

    def update(self) -> None:
        """Advance the state of the current mode by one frame.

        Args:
            None.

        Returns:
            None.

        Concept: n/a (state machine dispatch).
        Complexity: O(1) dispatch + cost of the mode update.
        """
        if self.mode == GameMode.MENU:
            return
        if self.mode == GameMode.PLAYING:
            self.update_playing()
        elif self.mode == GameMode.SOLVING:
            self.update_solving()
        elif self.mode == GameMode.COMPARING:
            self.update_comparing()
        elif self.mode == GameMode.GAME_OVER:
            self.update_game_over()

    def render(self) -> None:
        """Draw the current mode to the screen.

        Args:
            None.

        Returns:
            None.

        Concept: n/a (rendering dispatch).
        Complexity: O(1) dispatch + cost of the mode render.
        """
        self.screen.fill(COLOR_BG)
        if self.mode == GameMode.MENU:
            self.render_menu()
        elif self.mode == GameMode.PLAYING:
            self.render_playing()
        elif self.mode == GameMode.SOLVING:
            self.render_solving()
        elif self.mode == GameMode.COMPARING:
            self.render_comparing()
        elif self.mode == GameMode.GAME_OVER:
            self.render_game_over()

    def render_menu(self) -> None:
        """Draw the menu: title, difficulty choice, and the key reference.

        Args:
            None.

        Returns:
            None.

        Concept: n/a (UI).
        Complexity: O(1).
        """
        rows, cols, _ = DIFFICULTY_LEVELS[self.difficulty]
        lines = [
            "Intelligent Maze Generator and Solver",
            "",
            f"Difficulty: {self.difficulty} ({rows} x {cols})",
            "1 easy   2 medium   3 hard",
            "",
            "ENTER  start game",
            "Arrows  move     H  hint",
            "S  show solution     C  BFS vs DFS",
            "R  new maze     ESC  menu",
            "",
            "Close the window to quit",
        ]
        for i, line in enumerate(lines):
            surface = self.font.render(line, True, COLOR_WALL)
            self.screen.blit(surface, (WINDOW_PADDING, WINDOW_PADDING + i * 36))

    # ------------------------------------------------------------------
    # Level setup
    # ------------------------------------------------------------------
    def new_level(self) -> None:
        """Generate a maze for the current difficulty and reset all per-maze state.

        The cell size shrinks for large grids so the maze always fits the window.

        Args:
            None.

        Returns:
            None.

        Concept: Trees — a random spanning tree, optionally braided into a graph with cycles.
        Complexity: O(|V|).
        """
        rows, cols, braid = DIFFICULTY_LEVELS[self.difficulty]
        seed = time.time_ns() % 1_000_000_007
        graph = generate_maze_dfs(rows, cols, seed=seed)
        if braid > 0:
            add_braids(graph, braid, seed=seed)
        self.graph = graph
        self.start, self.goal = pick_start_and_goal(graph)
        self.controller = PlayerController(graph, self.start, self.goal)
        width, height = self.screen.get_size()
        cell_size = min(CELL_SIZE, (width - 2 * WINDOW_PADDING) // cols, (height - 2 * WINDOW_PADDING) // rows)
        self.renderer = MazeRenderer(self.screen, graph, cell_size)
        self.optimal_path = bfs(graph, self.start, self.goal).path or []
        self.hint_cell = None
        self.started_at = time.perf_counter()
        self.elapsed = 0.0
        self.animator = None
        self.race = None
        self.results = {}
        self.game_result = None

    # ------------------------------------------------------------------
    # Input actions
    # ------------------------------------------------------------------
    def on_start_game(self) -> None:
        """Generate a maze, place the player, and switch to PLAYING.

        Args:
            None.

        Returns:
            None.

        Concept: Trees — generates a spanning-tree maze via generate_maze_dfs.
        Complexity: O(|V|).
        """
        self.new_level()
        self.mode = GameMode.PLAYING

    def on_move(self, direction: str) -> None:
        """Forward an arrow-key move to the PlayerController.

        Args:
            direction: "up", "down", "left" or "right".

        Returns:
            None.

        Concept: Graph Theory — move only along existing edges.
        Complexity: O(1).
        """
        if self.controller is None:
            return
        if self.controller.try_move(direction):
            self.hint_cell = None
            if self.controller.has_reached_goal():
                self.elapsed = time.perf_counter() - self.started_at
                self.mode = GameMode.GAME_OVER

    def on_hint(self) -> None:
        """Show the next optimal step (H key).

        Args:
            None.

        Returns:
            None.

        Concept: BFS — shortest path from the player's current cell to the goal.
        Complexity: O(|V| + |E|).
        """
        if self.controller is None or self.graph is None:
            return
        path = bfs(self.graph, self.controller.state.current, self.goal).path
        if path:
            self.hint_cell = self.controller.request_hint(path)

    def on_show_solution(self) -> None:
        """Reveal the BFS solution with animation (S key).

        Args:
            None.

        Returns:
            None.

        Concept: BFS — shortest path in an unweighted graph.
        Complexity: O(|V| + |E|).
        """
        self.animator = SearchAnimator(self.renderer, bfs(self.graph, self.start, self.goal))
        self.mode = GameMode.SOLVING

    def on_new_maze(self) -> None:
        """Generate a fresh maze (R key).

        Args:
            None.

        Returns:
            None.

        Concept: Trees — new random spanning tree.
        Complexity: O(|V|).
        """
        self.new_level()
        self.mode = GameMode.PLAYING

    def on_compare(self) -> None:
        """Open the BFS-vs-DFS comparison view (C key).

        Args:
            None.

        Returns:
            None.

        Concept: BFS vs DFS — explored cells and path length.
        Complexity: O(|V| + |E|).
        """
        self.results = compare_algorithms(self.graph, self.start, self.goal)
        self.race = SolverRace(self.renderer, self.results["bfs"], self.results["dfs"])
        self.mode = GameMode.COMPARING

    # ------------------------------------------------------------------
    # Mode-specific update / render stubs
    # ------------------------------------------------------------------
    def update_playing(self) -> None:
        """Per-frame update while the player is navigating.

        Args:
            None.

        Returns:
            None.

        Concept: n/a.
        Complexity: O(1).
        """
        self.elapsed = time.perf_counter() - self.started_at

    def update_solving(self) -> None:
        """Per-frame update of the solution animation.

        Args:
            None.

        Returns:
            None.

        Concept: BFS.
        Complexity: O(1) per frame.
        """
        if self.animator is not None:
            self.animator.step()

    def update_comparing(self) -> None:
        """Per-frame update of the BFS-vs-DFS race.

        Args:
            None.

        Returns:
            None.

        Concept: BFS vs DFS.
        Complexity: O(1) per frame.
        """
        if self.race is not None:
            self.race.step()

    def update_game_over(self) -> None:
        """Per-frame update on the results screen.

        Args:
            None.

        Returns:
            None.

        Concept: n/a.
        Complexity: O(1).
        """
        if self.game_result is None and self.controller is not None:
            self.game_result = compute_score(self.controller.state, self.optimal_path, self.elapsed)

    def render_playing(self) -> None:
        """Draw maze, player, and HUD.

        Args:
            None.

        Returns:
            None.

        Concept: n/a.
        Complexity: O(|V|).
        """
        r, state = self.renderer, self.controller.state
        r.draw_grid()
        if self.hint_cell is not None:
            r.draw_cell(self.hint_cell, COLOR_HINT)
        r.draw_start_and_goal(self.start, self.goal)
        r.draw_walls()
        r.draw_player(state.current)
        r.draw_hud([
            f"{self.difficulty.title()}   Moves: {state.moves}   Time: {self.elapsed:.1f} s",
            f"Hints: {state.hints_used}   Backtracks: {state.backtracks}   H hint  S solve  C compare",
        ])

    def render_solving(self) -> None:
        """Draw the animated solution.

        Args:
            None.

        Returns:
            None.

        Concept: BFS.
        Complexity: O(|V|).
        """
        self.animator.draw()
        path = self.animator.path
        self.renderer.draw_hud([
            f"BFS solution   explored {self.animator.explored_count} cells",
            f"Shortest path: {len(path) - 1} moves   R new maze   ESC menu" if path else "No path found",
        ])

    def render_comparing(self) -> None:
        """Draw the race and comparison panel.

        Args:
            None.

        Returns:
            None.

        Concept: BFS vs DFS.
        Complexity: O(|V|).
        """
        self.race.draw()
        self.renderer.draw_hud(["BFS (left) vs DFS (right)", "R new maze   ESC menu"])
        if self.race.done:
            self.renderer.draw_comparison_panel(self.results)

    def render_game_over(self) -> None:
        """Draw the player's path vs the BFS path and the score.

        Args:
            None.

        Returns:
            None.

        Concept: BFS.
        Complexity: O(|V|).
        """
        r, result = self.renderer, self.game_result
        r.draw_grid()
        r.draw_start_and_goal(self.start, self.goal)
        r.draw_walls()
        r.draw_path(self.controller.state.path, COLOR_PLAYER, width=max(2, r.cell_size // 3))
        r.draw_path(self.optimal_path, COLOR_BFS_PATH, width=max(2, r.cell_size // 6))
        if result is not None:
            r.draw_hud([
                f"{result.rating}!  Score {result.score:.2f}   Moves {result.player_moves} / optimal {result.optimal_moves}",
                f"Time {result.elapsed_seconds:.1f} s   Hints {result.hints_used}   Backtracks {result.backtracks}   R next",
            ])


def main() -> None:
    """Create and run the application.

    Args:
        None.

    Returns:
        None.

    Concept: n/a (entry point).
    Complexity: O(frames).
    """
    MazeApp().run()


if __name__ == "__main__":
    main()
