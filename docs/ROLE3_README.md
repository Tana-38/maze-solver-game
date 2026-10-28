# Role 3 — Visualization & Animation

**Owner:** Harshali
**Files:** `src/ui/visualizer.py`, `src/ui/animation.py`, `scripts/ui_demo.py`, `tests/test_ui.py`

pygame rendering, path highlighting, search animation, and the BFS-vs-DFS race.

## What each file does

| File | Responsibility |
|------|----------------|
| `src/ui/visualizer.py` | `MazeRenderer` draws a `MazeGraph`: walls, cells, explored cells, paths, start/goal, the player, the HUD and the comparison panel. `cell_to_pixel` / `pixel_to_cell` convert between grid cells and screen pixels. |
| `src/ui/animation.py` | `SearchAnimator` replays one `SearchResult` cell by cell, then reveals the path. `SolverRace` runs BFS and DFS side by side with live counters. |
| `scripts/ui_demo.py` | Standalone race demo on a real generated maze. Uses Role 2's `bfs`/`dfs` once they exist, and small stand-in searches until then. |
| `tests/test_ui.py` | Coordinate conversion, wall count, animation progress, race layout. Runs headless. |

## How walls are drawn

A wall is a grid-graph edge that is **not** in the maze's edge set E. The renderer checks the
right and bottom side of every cell once with `graph.has_edge`, so each interior wall is
found exactly once, and caches the segments. For a perfect maze there are
`(R-1)C + R(C-1) - (|V| - 1)` interior walls (the test checks this). Create a new
`MazeRenderer` whenever you generate a new maze.

## Using it from `main.py` (Role 4)

`step()` only advances an animation; `draw()` draws it. Call `step()` in the update phase and
`draw()` in the render phase, because `render()` clears the screen first.

```python
from src.ui.visualizer import MazeRenderer
from src.ui.animation import SearchAnimator, SolverRace

# new maze
self.renderer = MazeRenderer(self.screen, graph)

# PLAYING — render
self.renderer.draw_grid()
self.renderer.draw_walls()
self.renderer.draw_start_and_goal(start, goal)
self.renderer.draw_player(controller.state.current)
self.renderer.draw_hud([f"Moves: {moves}", f"Time: {elapsed:.1f} s"])   # 2 lines fit above the maze

# hint: self.renderer.draw_cell(hint_cell, COLOR_HINT)

# SOLVING
self.animator = SearchAnimator(self.renderer, bfs(graph, start, goal))   # S key
self.animator.step()                                                     # update
self.animator.draw()                                                     # render

# COMPARING
self.results = compare_algorithms(graph, start, goal)                    # C key
self.race = SolverRace(self.renderer, self.results["bfs"], self.results["dfs"])
self.race.step()                                                         # update
self.race.draw()                                                         # render
if self.race.done:
    self.renderer.draw_comparison_panel(self.results)

# GAME_OVER — overlay both paths
self.renderer.draw_path(player_path, COLOR_PLAYER)
self.renderer.draw_path(bfs_path, COLOR_BFS_PATH)
```

`SolverRace` lays both mazes out inside the existing window with a smaller cell size and leaves
room at the bottom for the comparison panel, so the window does not need resizing. Speed is in
cells per second: `animator.set_speed(n)` / `race.set_speed(n)`. Colors all come from
`src/config.py`.

The comparison panel shows explored cells, path length (in moves) and runtime per algorithm,
plus a verdict line such as "BFS explored fewer cells (161 vs 345); same path length (96)".

## Run the demo

```bash
python scripts/ui_demo.py
```

Keys: `SPACE` pause · `R` restart · `N` new maze · `↑/↓` speed · `ESC` quit

## Note on results

In a perfect maze there is exactly one route between any two cells, so BFS and DFS find
paths of equal length. The interesting difference is **how many cells each explores**,
which is what the race displays. On a braided maze (with loops) BFS's path can be shorter.
