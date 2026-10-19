# Report Notes — Intelligent Maze Generator and Solver

> Skeleton for the written report. Replace each prompt with your own text.

## Problem Statement
_What problem are we solving? Define maze generation, solving, and the player-vs-computer game in one paragraph._

## Graph Model
_Define G = (V, E): vertices are cells, edges are open passages; explain the grid graph and the adjacency-list representation._

## Maze Generation Algorithm
_Explain randomized DFS with backtracking and why its output is a spanning tree; mention braiding and the Kruskal/Prim extensions._

## BFS vs DFS
_Compare how each explores the graph, which one guarantees shortest paths, and why they agree in a perfect maze._

## Complexity Analysis
_State and justify the time and space complexity of generation, BFS, DFS, and the property checks (O(|V| + |E|), etc.)._

## Game Mode and Scoring
_Describe move validation (edges only), hints from BFS, backtrack counting, and the score formula optimal_moves / player_moves minus penalties._

## Experimental Results
_Tables/plots of explored-cell counts, path lengths, and runtimes for BFS and DFS across maze sizes and braid factors._

## Proofs and Observations
_Prove |E| = |V| - 1 for the generated maze, that the grid graph is bipartite, and that BFS finds shortest paths; note dead-end statistics._

## Limitations
_What the project does not handle (e.g. very large grids, weighted terrain in the base version, UI constraints)._

## Future Work
_Possible extensions: Dijkstra with weighted cells, A*, Kruskal/Prim generators, Matrix-Tree spanning-tree counts, multiplayer, 3D mazes._
