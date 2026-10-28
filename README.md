# Intelligent Maze Generator and Solver

This project generates random mazes, solves them automatically, and lets you play them yourself. It models every maze as a graph, solves it with Breadth-First Search (BFS) and Depth-First Search (DFS), and animates both searches side by side with pygame. You can also play a game mode where you find the exit with the arrow keys, after which the computer shows the optimal path and scores your run.

## The Idea

Each cell of a rectangular grid is a **vertex**, and each open passage between two neighboring cells is an **edge**. A maze with no loops (a "perfect" maze) is therefore a **spanning tree** of the grid graph: it reaches every cell and has exactly one route between any two cells, so it has |E| = |V| − 1 edges. We **generate** the maze with randomized DFS, which walks to random unvisited neighbors and backtracks at dead ends. The edges it carves form the DFS tree. We **solve** it with BFS, which explores the maze in layers of increasing distance and so always finds a shortest path. We also run DFS and compare how many cells each algorithm explores. In **game mode** the player walks through the maze by hand. Each move is allowed only along an existing edge. When the player reaches the goal, the program reveals the BFS-optimal path and scores the player's moves against it.

## Discrete Mathematics Concepts

| Concept | Where It's Used |
|---|---|
| Graph theory: adjacency-list representation (vertices = cells, edges = passages) | `MazeGraph` in `src/maze/graph.py`; shared `Cell` / `Graph` type aliases |
| Handshake Lemma (Σ deg(v) = 2\|E\|) | `MazeGraph.edge_count()`, `degree_distribution()` |
| Trees: a perfect maze is a spanning tree, \|E\| = \|V\| − 1 | `is_tree()` in `src/analysis/properties.py`; generator tests |
| BFS: shortest path in an unweighted graph | `bfs()` in `src/algorithms/solvers.py`; hints and scoring in game mode |
| BFS: connectivity checking | `is_connected()` in `src/analysis/properties.py` |
| Randomized DFS with backtracking (maze generation) | `generate_maze_dfs()` in `src/maze/generator.py` |
| DFS for solving | `dfs()` in `src/algorithms/solvers.py` |
| Parent-pointer trees for path reconstruction | `reconstruct_path()` in `src/algorithms/solvers.py` |
| Bipartite graphs: the grid is 2-colorable (checkerboard) | `is_bipartite()` in `src/analysis/properties.py` |
| Degree analysis: degree-1 vertices are dead ends | `count_dead_ends()`, `degree_distribution()`, `difficulty_score()` |
| Tree diameter via double BFS | `tree_diameter()`, `pick_start_and_goal()` |
| Cycles: adding an edge to a tree creates exactly one cycle | `add_braids()` in `src/maze/generator.py` |
| *(Extension)* Dijkstra's algorithm (weighted edges) | `dijkstra()` in `src/algorithms/solvers.py` |
| *(Extension)* A* search with the Manhattan heuristic | `a_star()` in `src/algorithms/solvers.py` |
| *(Extension)* Kruskal's algorithm with union-find | `generate_maze_kruskal()` in `src/maze/generator.py` |
| *(Extension)* Prim's algorithm | `generate_maze_prim()` in `src/maze/generator.py` |
| *(Extension)* Matrix-Tree Theorem (counting spanning trees) | `count_spanning_trees()` in `src/analysis/properties.py` |

## Features

- **Random maze generation:** perfect mazes from randomized DFS, with reproducible seeds
- **BFS and DFS solving** from a start cell to a goal cell
- **Algorithm comparison:** explored cells, path length, and runtime for each algorithm
- **Animated search:** watch BFS spread in layers while DFS dives deep, including a side-by-side race
- **Interactive player mode:** move with the arrow keys; walls block illegal moves
- **Scoring:** compares your moves with the BFS-optimal path, with penalties for hints and backtracking
- **Difficulty levels:** easy, medium, and hard settings for grid size and braid (loop) factor
- **Graph property checks:** connectivity, tree property, bipartiteness, dead ends, and diameter

## Team Members and Roles

| Role | Member | Responsibilities | Files Owned |
|---|---|---|---|
| Role 1 — Graph & Maze Generation | [MEMBER 1 NAME] | Graph structure, randomized DFS generator, braid option, Kruskal/Prim | `src/maze/graph.py`, `src/maze/generator.py` |
| Role 2 — Algorithms & Graph Analysis | [MEMBER 2 NAME] | BFS, DFS, path reconstruction, explored counts, Dijkstra/A*, graph property checks | `src/algorithms/solvers.py`, `src/analysis/properties.py` |
| Role 3 — Visualization & Animation | Harshali | pygame rendering, path highlighting, search animation, BFS-vs-DFS race | `src/ui/visualizer.py`, `src/ui/animation.py` |
| Role 4 — Game Logic & Integration | [MEMBER 4 NAME] | Player movement validation, scoring, hints, levels, `main.py` integration | `src/game/player.py`, `src/game/scoring.py`, `main.py` |

## Project Structure

```
maze-solver-game/
├── README.md                 # This file
├── requirements.txt          # pygame, pytest
├── .gitignore                # Python / IDE ignores
├── main.py                   # pygame app: event loop, game modes (Role 4)
├── src/
│   ├── __init__.py
│   ├── config.py             # Grid size, colors, FPS, difficulty levels
│   ├── maze/
│   │   ├── __init__.py
│   │   ├── graph.py          # MazeGraph + Cell/Graph type aliases (Role 1)
│   │   └── generator.py      # DFS / Kruskal / Prim generators, braiding (Role 1)
│   ├── algorithms/
│   │   ├── __init__.py
│   │   └── solvers.py        # BFS, DFS, Dijkstra, A*, path reconstruction (Role 2)
│   ├── analysis/
│   │   ├── __init__.py
│   │   └── properties.py     # Connectivity, tree, bipartite, dead ends, diameter (Role 2)
│   ├── game/
│   │   ├── __init__.py
│   │   ├── player.py         # PlayerState, move validation, hints (Role 4)
│   │   └── scoring.py        # Score vs optimal path, rating labels (Role 4)
│   └── ui/
│       ├── __init__.py
│       ├── visualizer.py     # MazeRenderer: walls, paths, HUD (Role 3)
│       └── animation.py      # SearchAnimator, SolverRace (Role 3)
├── tests/
│   ├── __init__.py
│   ├── test_generator.py     # Maze is a connected tree, seeds, braids
│   ├── test_solvers.py       # BFS shortest, DFS valid, disconnected graphs
│   ├── test_properties.py    # Dead ends, bipartite, diameter
│   ├── test_game.py          # Wall collisions, backtracks, scoring
│   └── test_ui.py            # Pixel mapping, wall count, animation, race layout
├── scripts/
│   ├── demo_generator.py     # ASCII maze + graph stats in the terminal (Role 1)
│   ├── maze_server.py        # Browser maze viewer on localhost (Role 1)
│   └── ui_demo.py            # BFS-vs-DFS race demo in pygame (Role 3)
└── docs/
    ├── report_notes.md       # Skeleton for the written report
    └── ROLE3_README.md       # How to use the UI module from main.py (Role 3)
```

## Installation and Running

Requires **Python 3.10 – 3.13**. pygame has no prebuilt package for Python 3.14 yet, so `pip install` fails there; on Windows, `py -3.11 -m venv .venv` creates the venv with a specific version.

```bash
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate it
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Windows (cmd)
.venv\Scripts\activate.bat
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python main.py

# 5. Run the tests (from the project root)
pytest
```

If `pip install` or `git pull` fails with `CERTIFICATE_VERIFY_FAILED` / `unable to get local issuer certificate` (common on Windows with antivirus or a campus network), use the Windows certificate store; certificates are still checked:

```bash
pip install --use-feature=truststore -r requirements.txt
git -c http.sslBackend=schannel pull
```

## Notes for Teammates: Using the Maze Module (Role 1)

`src/maze/graph.py` and `src/maze/generator.py` are finished and tested (`pytest tests/test_generator.py`). Things to know when you call them:

- **Grid size:** use `graph.rows` and `graph.cols`. To loop over every cell, use `for r in range(graph.rows): for c in range(graph.cols)` or `graph.to_dict().keys()`.
- **`graph.has_edge(a, b)` never raises.** It returns `False` for cells outside the grid, so `is_valid_move` can call it directly for a move into the outer wall.
- **`graph.neighbors(cell)` raises `ValueError`** for a cell outside the grid. It returns a copy, as does `to_dict()`, so changing the result does not change the maze.
- **`add_edge` / `remove_edge` raise `ValueError`** unless the two cells are in-bounds and orthogonally adjacent. Adding an existing edge or removing a missing one does nothing.
- **`add_braids(graph, factor, seed=None)`** changes the maze in place and also returns it. Pass the same `seed` as the generator to make a whole level reproducible. Any `factor > 0` opens at least one wall; `DIFFICULTY_LEVELS` braid values can be passed straight in.
- **`pick_start_and_goal(graph, mode="corners")`** returns `(0, 0)` and `(rows-1, cols-1)`. `mode="diameter"` returns the two ends of the longest path instead, for a harder maze. These are usually not corners.
- **Generators:** `generate_maze_dfs`, `generate_maze_kruskal` and `generate_maze_prim` all take `(rows, cols, seed=None)` and return a spanning tree. The same seed always gives the same maze.
- **See it without pygame:** `python scripts/demo_generator.py` prints a maze as ASCII art; `python scripts/maze_server.py` opens a browser viewer at http://127.0.0.1:8000 with a "Run checks" button.

## Notes for Teammates: Using the UI Module (Role 3)

`src/ui/visualizer.py` and `src/ui/animation.py` are finished and tested (`pytest tests/test_ui.py`). See [docs/ROLE3_README.md](docs/ROLE3_README.md) for the calls `main.py` needs in each mode. The key rule: `step()` advances an animation and `draw()` renders it, so call `step()` in `update_*` and `draw()` in `render_*`. Try it with `python scripts/ui_demo.py`.

## Controls

| Key | Action |
|---|---|
| Arrow keys | Move the player |
| `H` | Show a hint (next step on the optimal path) |
| `S` | Show the solution (animated BFS) |
| `R` | Generate a new maze |
| `C` | Open the comparison view (BFS vs DFS) |
| `ESC` | Return to the menu |

## Course Information

Discrete Mathematics Course Project.
