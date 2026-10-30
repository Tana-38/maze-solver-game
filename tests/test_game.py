"""Tests for src/game/player.py and src/game/scoring.py.

Owner: Role 4 — Game Logic & Integration.
"""

import pytest

from src.algorithms.solvers import bfs
from src.game.player import PlayerController, PlayerState
from src.game.scoring import compute_score, rating_label
from src.maze.generator import generate_maze_dfs
from src.maze.graph import MazeGraph


def _corridor() -> MazeGraph:
    """2 x 3 maze: (0,0)-(0,1)-(0,2)-(1,2)-(1,1)-(1,0), a single snake corridor."""
    graph = MazeGraph(2, 3)
    for a, b in [((0, 0), (0, 1)), ((0, 1), (0, 2)), ((0, 2), (1, 2)), ((1, 2), (1, 1)), ((1, 1), (1, 0))]:
        graph.add_edge(a, b)
    return graph


def test_invalid_move_through_wall_rejected() -> None:
    """try_move into a wall returns False and leaves current cell and move count unchanged."""
    controller = PlayerController(_corridor(), (0, 0), (1, 0))
    assert controller.try_move("down") is False  # wall between (0,0) and (1,0)
    assert controller.state.current == (0, 0)
    assert controller.state.moves == 0
    assert controller.state.path == [(0, 0)]


def test_valid_move_updates_state() -> None:
    """try_move along an open passage returns True, updates current, path, and moves."""
    controller = PlayerController(_corridor(), (0, 0), (1, 0))
    assert controller.try_move("right") is True
    assert controller.state.current == (0, 1)
    assert controller.state.path == [(0, 0), (0, 1)]
    assert controller.state.moves == 1


def test_move_off_grid_rejected() -> None:
    """Moving "up" from row 0 or "left" from column 0 returns False."""
    controller = PlayerController(_corridor(), (0, 0), (1, 0))
    assert controller.try_move("up") is False
    assert controller.try_move("left") is False
    assert controller.state.moves == 0


def test_unknown_direction_raises() -> None:
    """A direction other than up/down/left/right is a programming error."""
    controller = PlayerController(_corridor(), (0, 0), (1, 0))
    with pytest.raises(ValueError):
        controller.try_move("north")


def test_backtracks_counted() -> None:
    """Moving A -> B -> A increments backtracks by exactly 1."""
    controller = PlayerController(_corridor(), (0, 0), (1, 0))
    controller.try_move("right")
    controller.try_move("left")
    assert controller.state.backtracks == 1
    assert controller.state.moves == 2
    controller.try_move("right")
    controller.try_move("right")
    assert controller.state.backtracks == 2  # (0,1) -> (0,0) -> (0,1) is also a step back


def test_has_reached_goal() -> None:
    """has_reached_goal is True only after the player steps onto the goal cell."""
    controller = PlayerController(_corridor(), (0, 0), (1, 0))
    for direction in ["right", "right", "down", "left"]:
        controller.try_move(direction)
        assert not controller.has_reached_goal()
    controller.try_move("left")
    assert controller.has_reached_goal()


def test_request_hint_returns_next_cell() -> None:
    """request_hint(bfs_path) returns bfs_path[1] and increments hints_used."""
    graph = _corridor()
    controller = PlayerController(graph, (0, 0), (1, 0))
    path = bfs(graph, (0, 0), (1, 0)).path
    assert controller.request_hint(path) == (0, 1)
    assert controller.state.hints_used == 1
    assert controller.request_hint([(1, 0)]) is None
    assert controller.state.hints_used == 2


def test_reset_returns_to_start() -> None:
    """reset() puts the player back on the start cell with all counters at zero."""
    controller = PlayerController(_corridor(), (0, 0), (1, 0))
    controller.try_move("right")
    controller.request_hint([(0, 1), (0, 2)])
    controller.reset()
    assert controller.state == PlayerState(current=(0, 0), path=[(0, 0)])


def test_perfect_play_scores_one() -> None:
    """Following the BFS path exactly with no hints or backtracks gives score == 1.0 and rating "Perfect"."""
    graph = generate_maze_dfs(8, 8, seed=3)
    start, goal = (0, 0), (7, 7)
    path = bfs(graph, start, goal).path
    controller = PlayerController(graph, start, goal)
    for a, b in zip(path, path[1:]):
        controller.state.current = a
        direction = {(-1, 0): "up", (1, 0): "down", (0, -1): "left", (0, 1): "right"}[(b[0] - a[0], b[1] - a[1])]
        assert controller.try_move(direction)
    assert controller.has_reached_goal()
    result = compute_score(controller.state, path, 12.5)
    assert result.score == 1.0
    assert result.rating == "Perfect"
    assert result.player_moves == result.optimal_moves == len(path) - 1
    assert result.elapsed_seconds == 12.5


def test_hints_and_backtracks_reduce_score() -> None:
    """Using hints or backtracking gives a strictly lower score than perfect play."""
    path = [(0, 0), (0, 1), (0, 2)]
    perfect = compute_score(PlayerState(current=(0, 2), path=path, moves=2), path, 1.0)
    hinted = compute_score(PlayerState(current=(0, 2), path=path, moves=2, hints_used=1), path, 1.0)
    wandering = compute_score(PlayerState(current=(0, 2), path=path, moves=4, backtracks=1), path, 1.0)
    assert perfect.score == 1.0
    assert hinted.score < perfect.score
    assert wandering.score < perfect.score
    assert 0.0 <= wandering.score <= 1.0


def test_score_is_clamped_to_zero() -> None:
    """Many hints cannot push the score below 0."""
    path = [(0, 0), (0, 1)]
    result = compute_score(PlayerState(current=(0, 1), path=path, moves=1, hints_used=100), path, 1.0)
    assert result.score == 0.0
    assert result.rating == "Keep trying"


def test_rating_label_thresholds() -> None:
    """rating_label maps 1.0 -> "Perfect" and very low scores -> "Keep trying"."""
    assert rating_label(1.0) == "Perfect"
    assert rating_label(0.9) == "Great"
    assert rating_label(0.6) == "Good"
    assert rating_label(0.1) == "Keep trying"
