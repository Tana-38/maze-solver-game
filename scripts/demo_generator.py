"""Print a generated maze as ASCII art plus its graph statistics.

Owner: Role 1 — Graph & Maze Generation.

A terminal-only check of src/maze (no pygame), so the generator can be verified
before the UI exists. Run from the project root:

    python scripts/demo_generator.py
    python scripts/demo_generator.py --rows 6 --cols 10 --seed 3 --algorithm prim
    python scripts/demo_generator.py --braid 0.2 --mode diameter

Legend: S = start, G = goal, "|" and "---" are walls, gaps are open passages (edges).
"""

from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path
from typing import Callable

# Allow "python scripts/demo_generator.py" from the project root to import src.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.maze.generator import (  # noqa: E402  (import after the sys.path tweak)
    add_braids,
    generate_maze_dfs,
    generate_maze_kruskal,
    generate_maze_prim,
    pick_start_and_goal,
)
from src.maze.graph import Cell, MazeGraph  # noqa: E402

GENERATORS: dict[str, Callable[[int, int, int | None], MazeGraph]] = {
    "dfs": generate_maze_dfs,
    "kruskal": generate_maze_kruskal,
    "prim": generate_maze_prim,
}


def render_ascii(maze: MazeGraph, start: Cell, goal: Cell) -> str:
    """Draw the maze with "+", "---" and "|", one 3-character-wide box per cell.

    Args:
        maze: The maze to draw.
        start: Cell to mark with "S".
        goal: Cell to mark with "G".

    Returns:
        The multi-line ASCII picture.

    Concept: Graph Theory — a wall is drawn exactly where a grid-graph edge is missing from E.
    Complexity: O(|V|).
    """
    lines = ["+" + "---+" * maze.cols]          # top border
    for r in range(maze.rows):
        cells_line = "|"                        # left border
        floor_line = "+"
        for c in range(maze.cols):
            cell = (r, c)
            label = "S" if cell == start else "G" if cell == goal else " "
            cells_line += f" {label} "
            # Right side: wall unless there is a passage to the right (or it's the border).
            cells_line += " " if maze.has_edge(cell, (r, c + 1)) else "|"
            # Bottom side: wall unless there is a passage downward (or it's the border).
            floor_line += "   +" if maze.has_edge(cell, (r + 1, c)) else "---+"
        lines.append(cells_line)
        lines.append(floor_line)
    return "\n".join(lines)


def count_reachable(maze: MazeGraph, source: Cell) -> int:
    """Count the cells reachable from ``source`` with BFS.

    Args:
        maze: The maze graph.
        source: Starting cell.

    Returns:
        Size of source's connected component.

    Concept: BFS — connectivity check.
    Complexity: O(|V| + |E|).
    """
    visited = {source}
    queue = deque([source])
    while queue:
        for neighbor in maze.neighbors(queue.popleft()):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return len(visited)


def count_dead_ends(maze: MazeGraph) -> int:
    """Count the dead ends, i.e. cells with exactly one open passage.

    Args:
        maze: The maze graph.

    Returns:
        Number of vertices of degree 1 (the leaves of the tree, for a perfect maze).

    Concept: Degree analysis — deg(v) = 1 means a dead end.
    Complexity: O(|V|).
    """
    return sum(1 for neighbors in maze.to_dict().values() if len(neighbors) == 1)


def parse_args() -> argparse.Namespace:
    """Read the command-line options.

    Returns:
        The parsed options.
    """
    parser = argparse.ArgumentParser(description="Print a generated maze and its graph statistics.")
    parser.add_argument("--rows", type=int, default=8, help="number of rows (default 8)")
    parser.add_argument("--cols", type=int, default=12, help="number of columns (default 12)")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default 42)")
    parser.add_argument("--algorithm", choices=GENERATORS, default="dfs", help="generator (default dfs)")
    parser.add_argument("--braid", type=float, default=0.0, help="braid factor 0.0-1.0 (default 0.0)")
    parser.add_argument("--mode", choices=["corners", "diameter"], default="corners",
                        help="how to pick start and goal (default corners)")
    return parser.parse_args()


def main() -> None:
    """Generate one maze, print it, and print its statistics.

    Returns:
        None.
    """
    args = parse_args()
    maze = GENERATORS[args.algorithm](args.rows, args.cols, args.seed)
    add_braids(maze, args.braid, seed=args.seed)
    start, goal = pick_start_and_goal(maze, mode=args.mode)

    vertices = maze.vertex_count()
    edges = maze.edge_count()
    connected = count_reachable(maze, (0, 0)) == vertices
    is_tree = connected and edges == vertices - 1

    print(f"{args.algorithm.upper()} maze, {args.rows} x {args.cols}, seed={args.seed}, braid={args.braid}")
    print(render_ascii(maze, start, goal))
    print()
    print(f"Start / goal     : {start} -> {goal}  (mode: {args.mode})")
    print(f"Vertices |V|     : {vertices}")
    print(f"Edges |E|        : {edges}  (a tree needs |V| - 1 = {vertices - 1})")
    print(f"Connected        : {connected}")
    print(f"Is a tree        : {is_tree}")
    print(f"Dead ends (deg 1): {count_dead_ends(maze)}")


if __name__ == "__main__":
    main()
