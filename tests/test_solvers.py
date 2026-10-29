"""Tests for src/algorithms/solvers.py.

Owner: Role 2 — Algorithms & Graph Analysis.
"""

import pytest

from src.algorithms import solvers
from src.algorithms.solvers import (
    a_star,
    bfs,
    compare_algorithms,
    dfs,
    dijkstra,
    reconstruct_path,
)
from src.maze.generator import (
    add_braids,
    generate_maze_dfs,
    generate_maze_kruskal,
    generate_maze_prim,
)
from src.maze.graph import MazeGraph

RING = [((0, 0), (0, 1)), ((0, 1), (0, 2)), ((0, 2), (1, 2)), ((1, 2), (1, 1)), ((1, 1), (1, 0)), ((1, 0), (0, 0))]


def _graph(rows: int, cols: int, edges: list) -> MazeGraph:
    graph = MazeGraph(rows, cols)
    for a, b in edges:
        graph.add_edge(a, b)
    return graph


def _is_valid_path(graph: MazeGraph, path: list, start: tuple, goal: tuple) -> bool:
    return (
        path[0] == start
        and path[-1] == goal
        and len(set(path)) == len(path)
        and all(graph.has_edge(a, b) for a, b in zip(path, path[1:]))
    )


def test_bfs_path_is_shortest() -> None:
    """On a hand-built graph with a cycle, BFS returns a path with the minimum number of edges."""
    graph = _graph(2, 3, RING)
    result = bfs(graph, (0, 0), (1, 1))
    assert result.path == [(0, 0), (1, 0), (1, 1)]
    assert len(result.path) - 1 == 2


def test_dfs_returns_valid_path() -> None:
    """DFS path starts at start, ends at goal, and every consecutive pair is an edge."""
    graph = _graph(2, 3, RING)
    result = dfs(graph, (0, 0), (1, 1))
    assert result.path is not None and _is_valid_path(graph, result.path, (0, 0), (1, 1))


def test_both_return_none_for_disconnected_graph() -> None:
    """When goal is unreachable, bfs(...).path and dfs(...).path are both None."""
    graph = _graph(2, 2, [((0, 0), (0, 1))])
    for solver in (bfs, dfs, a_star):
        result = solver(graph, (0, 0), (1, 1))
        assert result.path is None
        assert result.explored_count == 2
    assert dijkstra(graph, (0, 0), (1, 1), {}).path is None


def test_perfect_maze_bfs_and_dfs_agree() -> None:
    """In a perfect maze (a tree) the simple path is unique, so BFS and DFS return the same path."""
    for seed in range(10):
        graph = generate_maze_dfs(12, 9, seed=seed)
        goal = (11, 8)
        assert bfs(graph, (0, 0), goal).path == dfs(graph, (0, 0), goal).path


def test_start_equals_goal() -> None:
    """When start == goal, both solvers return the one-cell path [start]."""
    graph = generate_maze_dfs(4, 4, seed=1)
    for solver in (bfs, dfs, a_star):
        result = solver(graph, (2, 2), (2, 2))
        assert result.path == [(2, 2)]
        assert result.explored_order == [(2, 2)]
    assert dijkstra(graph, (2, 2), (2, 2), {}).path == [(2, 2)]


def test_explored_count_matches_explored_order() -> None:
    """explored_count == len(explored_order) and BFS explores no more cells than |V|."""
    graph = generate_maze_dfs(10, 10, seed=4)
    for result in compare_algorithms(graph, (0, 0), (9, 9)).values():
        assert result.explored_count == len(result.explored_order)
        assert len(set(result.explored_order)) == result.explored_count
        assert result.explored_count <= graph.vertex_count()
        assert result.runtime_ms >= 0


def test_bfs_explores_in_layers() -> None:
    """BFS explores cells in non-decreasing distance from the start."""
    graph = generate_maze_dfs(8, 8, seed=2)
    result = bfs(graph, (0, 0), (7, 7))
    dist = {(0, 0): 0}
    frontier = [(0, 0)]
    while frontier:
        nxt = []
        for cell in frontier:
            for nb in graph.neighbors(cell):
                if nb not in dist:
                    dist[nb] = dist[cell] + 1
                    nxt.append(nb)
        frontier = nxt
    layers = [dist[c] for c in result.explored_order]
    assert layers == sorted(layers)


def test_reconstruct_path() -> None:
    """reconstruct_path follows parents to the root and returns the path start -> goal."""
    parent = {(0, 0): None, (0, 1): (0, 0), (1, 1): (0, 1), (5, 5): None}
    assert reconstruct_path(parent, (1, 1)) == [(0, 0), (0, 1), (1, 1)]
    assert reconstruct_path(parent, (0, 0)) == [(0, 0)]
    assert reconstruct_path(parent, (9, 9)) is None


def test_compare_algorithms_keys() -> None:
    """compare_algorithms returns at least the keys "bfs" and "dfs"."""
    graph = generate_maze_dfs(5, 5, seed=0)
    results = compare_algorithms(graph, (0, 0), (4, 4))
    assert {"bfs", "dfs"} <= set(results)


@pytest.mark.parametrize("generator", [generate_maze_dfs, generate_maze_kruskal, generate_maze_prim])
def test_a_star_matches_bfs_length(generator) -> None:
    """(Extension) A* with the Manhattan heuristic returns a path as short as BFS."""
    for seed in range(5):
        graph = add_braids(generator(10, 10, seed=seed), 0.2, seed=seed)
        shortest = bfs(graph, (0, 0), (9, 9))
        informed = a_star(graph, (0, 0), (9, 9))
        assert len(informed.path) == len(shortest.path)
        assert _is_valid_path(graph, informed.path, (0, 0), (9, 9))
        assert informed.explored_count <= graph.vertex_count()


def test_dijkstra_unit_weights_matches_bfs() -> None:
    """(Extension) Dijkstra with all weights = 1 returns a path as short as BFS."""
    graph = add_braids(generate_maze_dfs(10, 10, seed=3), 0.2, seed=3)
    weights = {(a, b): 1.0 for a in graph.to_dict() for b in graph.neighbors(a)}
    result = dijkstra(graph, (0, 0), (9, 9), weights)
    assert len(result.path) == len(bfs(graph, (0, 0), (9, 9)).path)


def test_dijkstra_prefers_cheaper_longer_route() -> None:
    """(Extension) A heavy edge makes Dijkstra avoid a route BFS considers equally short."""
    graph = _graph(2, 3, RING + [((0, 1), (1, 1))])
    weights = {((0, 0), (1, 0)): 10.0}
    assert dijkstra(graph, (0, 0), (1, 1), weights).path == [(0, 0), (0, 1), (1, 1)]
    assert dijkstra(graph, (0, 0), (1, 1), {((0, 0), (0, 1)): 10.0}).path == [(0, 0), (1, 0), (1, 1)]


def test_dijkstra_rejects_negative_weight() -> None:
    """(Extension) Dijkstra is only correct for non-negative weights, so it refuses negative ones."""
    graph = _graph(1, 2, [((0, 0), (0, 1))])
    with pytest.raises(ValueError):
        dijkstra(graph, (0, 0), (0, 1), {((0, 0), (0, 1)): -1.0})


def test_module_exports_search_result() -> None:
    """The shared SearchResult type stays importable from solvers (UI and game modules rely on it)."""
    assert hasattr(solvers, "SearchResult")
