"""Tests for src/algorithms/solvers.py.

Owner: Role 2 — Algorithms & Graph Analysis.
"""

import pytest

from src.algorithms import solvers  # noqa: F401  (import verifies the scaffold loads)


def test_bfs_path_is_shortest() -> None:
    """On a hand-built graph with a cycle, BFS returns a path with the minimum number of edges."""
    pytest.skip("not implemented yet")


def test_dfs_returns_valid_path() -> None:
    """DFS path starts at start, ends at goal, and every consecutive pair is an edge."""
    pytest.skip("not implemented yet")


def test_both_return_none_for_disconnected_graph() -> None:
    """When goal is unreachable, bfs(...).path and dfs(...).path are both None."""
    pytest.skip("not implemented yet")


def test_perfect_maze_bfs_and_dfs_agree() -> None:
    """In a perfect maze (a tree) the simple path is unique, so BFS and DFS return the same path."""
    pytest.skip("not implemented yet")


def test_start_equals_goal() -> None:
    """When start == goal, both solvers return the one-cell path [start]."""
    pytest.skip("not implemented yet")


def test_explored_count_matches_explored_order() -> None:
    """explored_count == len(explored_order) and BFS explores no more cells than |V|."""
    pytest.skip("not implemented yet")


def test_reconstruct_path() -> None:
    """reconstruct_path follows parents to the root and returns the path start -> goal."""
    pytest.skip("not implemented yet")


def test_compare_algorithms_keys() -> None:
    """compare_algorithms returns at least the keys "bfs" and "dfs"."""
    pytest.skip("not implemented yet")


def test_a_star_matches_bfs_length() -> None:
    """(Extension) A* with the Manhattan heuristic returns a path as short as BFS."""
    pytest.skip("not implemented yet")


def test_dijkstra_unit_weights_matches_bfs() -> None:
    """(Extension) Dijkstra with all weights = 1 returns a path as short as BFS."""
    pytest.skip("not implemented yet")
