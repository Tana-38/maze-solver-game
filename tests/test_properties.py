"""Tests for src/analysis/properties.py.

Owner: Role 2 — Algorithms & Graph Analysis.
"""

import pytest

from src.algorithms.solvers import bfs
from src.analysis.properties import (
    count_dead_ends,
    count_spanning_trees,
    degree_distribution,
    difficulty_score,
    is_bipartite,
    is_connected,
    is_tree,
    tree_diameter,
)
from src.maze.generator import (
    add_braids,
    generate_maze_dfs,
    generate_maze_kruskal,
    generate_maze_prim,
    pick_start_and_goal,
)
from src.maze.graph import MazeGraph


def _path_graph(n: int) -> MazeGraph:
    graph = MazeGraph(1, n)
    for c in range(n - 1):
        graph.add_edge((0, c), (0, c + 1))
    return graph


def test_count_dead_ends() -> None:
    """On a hand-built 1 x 3 path graph, count_dead_ends == 2 (both endpoints have degree 1)."""
    assert count_dead_ends(_path_graph(3)) == 2


def test_degree_distribution_handshake() -> None:
    """sum(deg * count for deg, count in degree_distribution(g).items()) == 2 * edge_count()."""
    for seed in range(5):
        graph = add_braids(generate_maze_dfs(8, 11, seed=seed), 0.15, seed=seed)
        distribution = degree_distribution(graph)
        assert sum(deg * count for deg, count in distribution.items()) == 2 * graph.edge_count()
        assert sum(distribution.values()) == graph.vertex_count()
        assert set(distribution) == {0, 1, 2, 3, 4}


def test_is_bipartite_on_grid_maze() -> None:
    """Every maze (perfect or braided) is a subgraph of the grid, so is_bipartite is True."""
    for generator in (generate_maze_dfs, generate_maze_kruskal, generate_maze_prim):
        graph = generator(9, 9, seed=1)
        assert is_bipartite(graph)
        assert is_bipartite(add_braids(graph, 0.5, seed=1))


def test_is_bipartite_checks_every_component() -> None:
    """A graph with no edges (many components) is trivially 2-colorable."""
    assert is_bipartite(MazeGraph(3, 3))


def test_tree_diameter() -> None:
    """On a 1 x n path graph, tree_diameter == n - 1."""
    for n in (1, 2, 7):
        assert tree_diameter(_path_graph(n)) == n - 1


def test_tree_diameter_matches_generator_diameter_mode() -> None:
    """The diameter equals the BFS distance between the two endpoints chosen by pick_start_and_goal."""
    for seed in range(5):
        graph = generate_maze_dfs(10, 10, seed=seed)
        start, goal = pick_start_and_goal(graph, mode="diameter")
        assert tree_diameter(graph) == len(bfs(graph, start, goal).path) - 1


def test_is_connected_false_for_empty_edges() -> None:
    """A 2 x 2 MazeGraph with no edges is not connected."""
    assert not is_connected(MazeGraph(2, 2))
    assert is_connected(MazeGraph(1, 1))


def test_is_tree_false_with_cycle() -> None:
    """A 2 x 2 grid with all 4 edges open has a cycle, so is_tree is False."""
    graph = MazeGraph(2, 2)
    for a, b in [((0, 0), (0, 1)), ((0, 1), (1, 1)), ((1, 1), (1, 0)), ((1, 0), (0, 0))]:
        graph.add_edge(a, b)
    assert is_connected(graph) and not is_tree(graph)


def test_is_tree_false_when_disconnected_with_cycle() -> None:
    """|E| = |V| - 1 alone does not make a tree: a 4-cycle plus one edge on a 2 x 3 grid has 5 edges, 6 cells."""
    graph = MazeGraph(2, 3)
    for a, b in [((0, 0), (0, 1)), ((0, 1), (1, 1)), ((1, 1), (1, 0)), ((1, 0), (0, 0)), ((0, 1), (0, 2))]:
        graph.add_edge(a, b)
    assert graph.edge_count() == graph.vertex_count() - 1
    assert not is_connected(graph) and not is_tree(graph)


def test_generated_mazes_are_trees_braids_break_it() -> None:
    """Perfect mazes pass is_tree; braiding adds a cycle, so they stop being trees."""
    for generator in (generate_maze_dfs, generate_maze_kruskal, generate_maze_prim):
        graph = generator(8, 8, seed=3)
        assert is_tree(graph) and is_connected(graph)
        assert not is_tree(add_braids(graph, 0.2, seed=3))


def test_difficulty_score_non_negative() -> None:
    """difficulty_score returns a float >= 0 for a generated maze."""
    graph = generate_maze_dfs(10, 10, seed=1)
    start, goal = pick_start_and_goal(graph)
    score = difficulty_score(graph, start, goal)
    assert isinstance(score, float) and 0 <= score <= 1


def test_difficulty_grows_with_path_length() -> None:
    """On the same maze, the diameter endpoints give a harder score than adjacent cells."""
    graph = generate_maze_dfs(12, 12, seed=5)
    start, goal = pick_start_and_goal(graph, mode="diameter")
    neighbor = graph.neighbors(start)[0]
    assert difficulty_score(graph, start, goal) > difficulty_score(graph, start, neighbor)


def test_difficulty_score_unreachable_goal() -> None:
    """A goal in another component is an error, not a score."""
    with pytest.raises(ValueError):
        difficulty_score(MazeGraph(2, 2), (0, 0), (1, 1))


def test_count_spanning_trees_small_grids() -> None:
    """(Extension) Matrix-Tree Theorem: 2 x 2 grid has 4 spanning trees, 3 x 3 grid has 192."""
    assert count_spanning_trees(2, 2) == 4
    assert count_spanning_trees(3, 3) == 192


def test_count_spanning_trees_known_values() -> None:
    """(Extension) A 1 x n grid is a path (1 tree); 2 x n counts are 1, 4, 15, 56, ... (OEIS A001353)."""
    assert count_spanning_trees(1, 1) == 1
    assert count_spanning_trees(1, 6) == 1
    assert [count_spanning_trees(2, n) for n in range(1, 6)] == [1, 4, 15, 56, 209]
    assert count_spanning_trees(4, 4) == 100352
