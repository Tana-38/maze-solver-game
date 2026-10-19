"""Global configuration constants for the maze project.

Owner: shared (Role 4 — Game Logic & Integration maintains this file).

These are real values, not stubs. Every module should read its tunable
parameters from here instead of hard-coding them.
"""

# ---------------------------------------------------------------------------
# Grid and window geometry
# ---------------------------------------------------------------------------
GRID_ROWS: int = 20
GRID_COLS: int = 20
CELL_SIZE: int = 30          # pixels per cell
WALL_THICKNESS: int = 2      # pixels
FPS: int = 60
WINDOW_PADDING: int = 40     # pixels around the maze for the HUD / margins

# ---------------------------------------------------------------------------
# Colors (RGB)
# ---------------------------------------------------------------------------
COLOR_BG: tuple[int, int, int] = (245, 245, 240)
COLOR_WALL: tuple[int, int, int] = (30, 30, 40)
COLOR_START: tuple[int, int, int] = (46, 204, 113)
COLOR_GOAL: tuple[int, int, int] = (231, 76, 60)
COLOR_PLAYER: tuple[int, int, int] = (52, 152, 219)
COLOR_BFS_PATH: tuple[int, int, int] = (241, 196, 15)
COLOR_DFS_PATH: tuple[int, int, int] = (155, 89, 182)
COLOR_EXPLORED: tuple[int, int, int] = (200, 225, 255)
COLOR_HINT: tuple[int, int, int] = (255, 159, 67)

# ---------------------------------------------------------------------------
# Maze generation
# ---------------------------------------------------------------------------
BRAID_FACTOR: float = 0.0    # fraction of walls removed to create loops (0.0 = perfect maze)

# level name -> (rows, cols, braid_factor)
DIFFICULTY_LEVELS: dict[str, tuple[int, int, float]] = {
    "easy": (10, 10, 0.10),
    "medium": (20, 20, 0.05),
    "hard": (30, 30, 0.0),
}
