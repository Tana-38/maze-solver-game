"""Tests for src/maze/graph.py and src/maze/generator.py.

Owner: Role 1 — Graph & Maze Generation.

These tests use their own small BFS helper instead of src/analysis/properties.py
so that the maze module can be tested on its own. They rely on the theorem:
a graph on n vertices is a tree  <=>  it is connected and has n - 1 edges.
"""

from collections import deque
from typing import Callable

import pytest

from src.maze.generator import (
    add_braids,
    generate_maze_dfs,
    generate_maze_kruskal,
    generate_maze_prim,
    pick_start_and_goal,
)
from src.maze.graph import Cell, MazeGraph

Generator = Callable[[int, int, int | None], MazeGraph]

ALL_GENERATORS: list[Generator] = [generate_maze_dfs, generate_maze_kruskal, generate_maze_prim]
GRID_SIZES: list[tuple[int, int]] = [(1, 1), (1, 6), (6, 1), (5, 8), (20, 20)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def bfs_distances(maze: MazeGraph, source: Cell) -> dict[Cell, int]:
    """Return the BFS distance from ``source`` to every reachable cell."""
    distance = {source: 0}
    queue = deque([source])
    while queue:
        cell = queue.popleft()
        for neighbor in maze.neighbors(cell):
            if neighbor not in distance:
                distance[neighbor] = distance[cell] + 1
                queue.append(neighbor)
    return distance


def is_connected(maze: MazeGraph) -> bool:
    """True if BFS from (0, 0) reaches all rows * cols cells."""
    return len(bfs_distances(maze, (0, 0))) == maze.vertex_count()


def is_tree(maze: MazeGraph) -> bool:
    """True if the maze is connected and |E| = |V| - 1 (so it is also acyclic)."""
    return is_connected(maze) and maze.edge_count() == maze.vertex_count() - 1


# ---------------------------------------------------------------------------
# MazeGraph
# ---------------------------------------------------------------------------
def test_new_graph_has_all_vertices_and_no_edges() -> None:
    """MazeGraph(r, c) has r * c vertices, each with an empty neighbor list."""
    maze = MazeGraph(3, 4)
    assert maze.vertex_count() == 12
    assert maze.edge_count() == 0
    assert all(neighbors == [] for neighbors in maze.to_dict().values())


def test_grid_neighbors_bounds_checked() -> None:
    """grid_neighbors returns 2 cells for a corner, 3 for an edge cell, 4 for an interior cell."""
    maze = MazeGraph(3, 3)
    assert sorted(maze.grid_neighbors((0, 0))) == [(0, 1), (1, 0)]
    assert sorted(maze.grid_neighbors((0, 1))) == [(0, 0), (0, 2), (1, 1)]
    assert sorted(maze.grid_neighbors((1, 1))) == [(0, 1), (1, 0), (1, 2), (2, 1)]


def test_add_and_remove_edge_symmetric() -> None:
    """add_edge(a, b) makes has_edge(a, b) and has_edge(b, a) True; remove_edge undoes both."""
    maze = MazeGraph(2, 2)
    maze.add_edge((0, 0), (0, 1))
    assert maze.has_edge((0, 0), (0, 1))
    assert maze.has_edge((0, 1), (0, 0))
    assert maze.edge_count() == 1

    maze.remove_edge((0, 1), (0, 0))
    assert not maze.has_edge((0, 0), (0, 1))
    assert not maze.has_edge((0, 1), (0, 0))
    assert maze.edge_count() == 0


def test_duplicate_edge_counted_once() -> None:
    """Adding the same edge twice (in either direction) still counts as one edge."""
    maze = MazeGraph(2, 2)
    maze.add_edge((0, 0), (1, 0))
    maze.add_edge((1, 0), (0, 0))
    assert maze.edge_count() == 1
    assert maze.neighbors((0, 0)) == [(1, 0)]


@pytest.mark.parametrize(
    "a, b",
    [
        ((0, 0), (1, 1)),   # diagonal
        ((0, 0), (0, 2)),   # two apart
        ((0, 0), (0, 0)),   # self-loop
        ((0, 2), (0, 3)),   # b is out of bounds
        ((-1, 0), (0, 0)),  # a is out of bounds
    ],
)
def test_add_edge_rejects_non_adjacent(a: Cell, b: Cell) -> None:
    """add_edge raises ValueError unless both cells are in-bounds grid neighbors."""
    maze = MazeGraph(3, 3)
    with pytest.raises(ValueError):
        maze.add_edge(a, b)


def test_remove_edge_rejects_non_adjacent() -> None:
    """remove_edge raises ValueError for cells that are not grid neighbors."""
    with pytest.raises(ValueError):
        MazeGraph(3, 3).remove_edge((0, 0), (2, 2))


def test_has_edge_outside_grid_is_false() -> None:
    """has_edge never raises: a move off the grid is simply not an edge."""
    maze = MazeGraph(2, 2)
    assert maze.has_edge((0, 0), (-1, 0)) is False


def test_to_dict_and_neighbors_return_copies() -> None:
    """Mutating the result of to_dict() or neighbors() does not change the maze."""
    maze = MazeGraph(2, 2)
    maze.add_edge((0, 0), (0, 1))
    maze.to_dict()[(0, 0)].append((1, 0))
    maze.neighbors((0, 0)).clear()
    assert maze.neighbors((0, 0)) == [(0, 1)]
    assert maze.edge_count() == 1


def test_repr_shows_sizes() -> None:
    """repr includes rows, cols, |V| and |E|."""
    assert repr(MazeGraph(3, 4)) == "MazeGraph(rows=3, cols=4, V=12, E=0)"


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("generate", ALL_GENERATORS)
@pytest.mark.parametrize("rows, cols", GRID_SIZES)
def test_maze_is_connected(generate: Generator, rows: int, cols: int) -> None:
    """Every generated maze is connected: BFS from (0, 0) reaches all rows * cols cells."""
    for seed in range(5):
        assert is_connected(generate(rows, cols, seed))


@pytest.mark.parametrize("rows, cols", GRID_SIZES)
def test_edge_count_is_vertices_minus_one(rows: int, cols: int) -> None:
    """For a DFS (perfect) maze, edge_count() == vertex_count() - 1."""
    for seed in range(5):
        maze = generate_maze_dfs(rows, cols, seed)
        assert maze.edge_count() == maze.vertex_count() - 1


def test_maze_is_tree() -> None:
    """A DFS-generated maze is a spanning tree (connected with |V| - 1 edges)."""
    assert is_tree(generate_maze_dfs(15, 15, seed=0))


def test_large_dfs_maze_does_not_hit_recursion_limit() -> None:
    """The iterative DFS handles a 50 x 50 grid (2500 cells) without recursion errors."""
    assert is_tree(generate_maze_dfs(50, 50, seed=1))


@pytest.mark.parametrize("generate", ALL_GENERATORS)
def test_same_seed_gives_same_maze(generate: Generator) -> None:
    """The same seed twice yields identical to_dict() adjacency lists."""
    assert generate(10, 10, 42).to_dict() == generate(10, 10, 42).to_dict()


@pytest.mark.parametrize("generate", ALL_GENERATORS)
def test_different_seeds_usually_differ(generate: Generator) -> None:
    """Two different seeds on a 10 x 10 grid produce different mazes."""
    assert generate(10, 10, 1).to_dict() != generate(10, 10, 2).to_dict()


@pytest.mark.parametrize("generate", [generate_maze_kruskal, generate_maze_prim])
@pytest.mark.parametrize("rows, cols", GRID_SIZES)
def test_kruskal_and_prim_produce_trees(generate: Generator, rows: int, cols: int) -> None:
    """(Extension) generate_maze_kruskal and generate_maze_prim both return spanning trees."""
    for seed in range(5):
        assert is_tree(generate(rows, cols, seed))


# ---------------------------------------------------------------------------
# Braiding
# ---------------------------------------------------------------------------
def test_braid_factor_zero_changes_nothing() -> None:
    """add_braids(maze, 0.0) leaves the adjacency lists exactly as they were."""
    maze = generate_maze_dfs(10, 10, seed=7)
    before = maze.to_dict()
    add_braids(maze, 0.0)
    assert maze.to_dict() == before
    assert is_tree(maze)


def test_braids_create_cycles() -> None:
    """After add_braids(maze, 0.2), edge_count() > vertex_count() - 1 and it is no longer a tree."""
    maze = generate_maze_dfs(10, 10, seed=7)
    add_braids(maze, 0.2, seed=3)
    assert maze.edge_count() > maze.vertex_count() - 1
    assert is_connected(maze)        # opening walls can never disconnect the maze
    assert not is_tree(maze)


def test_tiny_braid_factor_still_opens_a_wall() -> None:
    """Any factor > 0 opens at least one wall, even when factor * walls rounds to 0."""
    maze = generate_maze_dfs(3, 3, seed=0)
    add_braids(maze, 0.01)
    assert maze.edge_count() == maze.vertex_count()


def test_braid_factor_one_opens_every_wall() -> None:
    """add_braids(maze, 1.0) turns the maze into the full grid graph: 2*r*c - r - c edges."""
    rows, cols = 6, 7
    maze = add_braids(generate_maze_dfs(rows, cols, seed=0), 1.0)
    assert maze.edge_count() == 2 * rows * cols - rows - cols


def test_braids_are_reproducible() -> None:
    """The same maze and braid seed open the same walls."""
    a = add_braids(generate_maze_dfs(10, 10, seed=5), 0.3, seed=9)
    b = add_braids(generate_maze_dfs(10, 10, seed=5), 0.3, seed=9)
    assert a.to_dict() == b.to_dict()


@pytest.mark.parametrize("factor", [-0.1, 1.5])
def test_braid_factor_out_of_range_rejected(factor: float) -> None:
    """add_braids raises ValueError for a factor outside [0, 1]."""
    with pytest.raises(ValueError):
        add_braids(generate_maze_dfs(3, 3, seed=0), factor)


# ---------------------------------------------------------------------------
# Start and goal
# ---------------------------------------------------------------------------
def test_start_and_goal_default_corners() -> None:
    """By default start is the top-left corner and goal the bottom-right."""
    maze = generate_maze_dfs(8, 12, seed=0)
    assert pick_start_and_goal(maze) == ((0, 0), (7, 11))


def test_diameter_mode_gives_the_longest_path() -> None:
    """In a tree, the diameter endpoints are at least as far apart as any other pair."""
    maze = generate_maze_dfs(8, 8, seed=4)
    start, goal = pick_start_and_goal(maze, mode="diameter")
    diameter = bfs_distances(maze, start)[goal]

    longest = max(max(bfs_distances(maze, cell).values()) for cell in maze.to_dict())
    assert diameter == longest
    corner_start, corner_goal = pick_start_and_goal(maze)
    assert diameter >= bfs_distances(maze, corner_start)[corner_goal]


def test_unknown_mode_rejected() -> None:
    """pick_start_and_goal raises ValueError for an unknown mode."""
    with pytest.raises(ValueError):
        pick_start_and_goal(generate_maze_dfs(3, 3, seed=0), mode="random")  # type: ignore[arg-type]
