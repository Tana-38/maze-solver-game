"""Scoring of a completed game against the BFS-optimal solution.

Owner: Role 4 — Game Logic & Integration.

Base score = optimal_moves / player_moves (1.0 means the player walked a
shortest path), reduced by penalties for hints and backtracks.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.game.player import PlayerState
from src.maze.graph import Cell

HINT_PENALTY: float = 0.05       # subtracted per hint used
BACKTRACK_PENALTY: float = 0.01  # subtracted per backtracking move

# (minimum score, label), checked from the top
RATING_THRESHOLDS: list[tuple[float, str]] = [
    (1.0, "Perfect"),
    (0.8, "Great"),
    (0.5, "Good"),
]


@dataclass
class GameResult:
    """Summary of one finished game.

    Attributes:
        player_moves: Moves made by the player.
        optimal_moves: Edges on the BFS shortest path (len(path) - 1).
        backtracks: Number of backtracking moves.
        hints_used: Number of hints requested.
        elapsed_seconds: Time taken to reach the goal.
        score: Final score in [0, 1].
        rating: Human-readable label from rating_label().
    """

    player_moves: int
    optimal_moves: int
    backtracks: int
    hints_used: int
    elapsed_seconds: float
    score: float
    rating: str


def compute_score(player_state: PlayerState, optimal_path: list[Cell], elapsed: float) -> GameResult:
    """Score the player's walk against the optimal (shortest) path.

    Args:
        player_state: Final state of the player.
        optimal_path: BFS shortest path from start to goal, inclusive.
        elapsed: Seconds taken to finish.

    Returns:
        A GameResult with score = optimal_moves / player_moves minus penalties,
        clamped to [0, 1]; perfect play with no hints/backtracks scores 1.0.

    Concept: BFS — the shortest path length is a lower bound on any walk from
    start to goal, so the ratio is at most 1.
    Complexity: O(1).
    """
    optimal_moves = max(0, len(optimal_path) - 1)
    player_moves = player_state.moves
    base = optimal_moves / player_moves if player_moves else 1.0
    penalty = HINT_PENALTY * player_state.hints_used + BACKTRACK_PENALTY * player_state.backtracks
    score = max(0.0, min(1.0, base - penalty))
    return GameResult(
        player_moves=player_moves,
        optimal_moves=optimal_moves,
        backtracks=player_state.backtracks,
        hints_used=player_state.hints_used,
        elapsed_seconds=elapsed,
        score=score,
        rating=rating_label(score),
    )


def rating_label(score: float) -> str:
    """Convert a numeric score to a label.

    Args:
        score: Score in [0, 1].

    Returns:
        One of "Perfect", "Great", "Good", "Keep trying".

    Concept: n/a (presentation) — piecewise threshold function.
    Complexity: O(1).
    """
    for threshold, label in RATING_THRESHOLDS:
        if score >= threshold - 1e-9:
            return label
    return "Keep trying"
