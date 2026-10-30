"""Tests for web/api.py (the JSON API behind the browser frontend).

Owner: Role 4 — Game Logic & Integration.
"""

import pytest

from web import api

DIRS = {(-1, 0): "up", (1, 0): "down", (0, -1): "left", (0, 1): "right"}


def _new(store: api.GameStore, **body) -> dict:
    return api.create_game(store, {"difficulty": "easy", "seed": 7, **body})


def _walk(store: api.GameStore, game_id: str, path: list) -> dict:
    response = {}
    for a, b in zip(path, path[1:]):
        response = api.move(store, game_id, {"direction": DIRS[(b[0] - a[0], b[1] - a[1])]})
        assert response["moved"]
    return response


def test_create_game_returns_maze_and_analysis() -> None:
    """A new easy game is 10 x 10, reproducible from its seed, and connected."""
    store = api.GameStore()
    game = _new(store)
    maze = game["maze"]
    assert (maze["rows"], maze["cols"]) == (10, 10)
    assert len(maze["open_right"]) == 10 and len(maze["open_right"][0]) == 10
    assert game["analysis"]["connected"]
    assert game["analysis"]["degree_sum"] == 2 * game["analysis"]["edges"]  # Handshake Lemma
    assert _new(api.GameStore())["maze"] == maze


def test_perfect_custom_maze_is_tree() -> None:
    """With braid 0 the maze is a spanning tree: |E| = |V| - 1 and no cycles."""
    game = api.create_game(api.GameStore(), {"difficulty": "custom", "rows": 6, "cols": 9, "braid": 0, "algorithm": "kruskal"})
    stats = game["analysis"]
    assert stats["is_tree"] and stats["edges"] == stats["vertices"] - 1 and stats["cycles"] == 0


def test_bad_settings_rejected() -> None:
    """Invalid options raise ApiError with status 400."""
    store = api.GameStore()
    for body in [{"difficulty": "extreme"}, {"algorithm": "magic"}, {"difficulty": "custom", "rows": 999}, {"mode": "middle"}]:
        with pytest.raises(api.ApiError) as err:
            api.create_game(store, body)
        assert err.value.status == 400


def test_unknown_game_is_404() -> None:
    """Moves on a game id the server does not know give a 404."""
    with pytest.raises(api.ApiError) as err:
        api.move(api.GameStore(), "nope", {"direction": "up"})
    assert err.value.status == 404


def test_wall_blocks_move() -> None:
    """Moving off the grid from the start corner is rejected and not counted."""
    store = api.GameStore()
    game = _new(store)
    response = api.move(store, game["id"], {"direction": "up"})
    assert response["moved"] is False
    assert response["player"]["moves"] == 0


def test_optimal_walk_scores_perfect() -> None:
    """Walking the BFS path finishes the game with score 1 and both paths returned."""
    store = api.GameStore()
    game = _new(store)
    session = store.get(game["id"])
    response = _walk(store, game["id"], session.optimal_path)
    result = response["result"]
    assert response["player"]["finished"]
    assert result["score"] == 1.0 and result["rating"] == "Perfect"
    assert result["player_moves"] == result["optimal_moves"] == game["optimal_moves"]
    assert result["solution_revealed"] is False
    assert api.move(store, game["id"], {"direction": "left"})["moved"] is False  # game over


def test_hint_and_restart() -> None:
    """A hint is the next BFS cell and is counted; restart resets the player."""
    store = api.GameStore()
    game = _new(store)
    session = store.get(game["id"])
    response = api.hint(store, game["id"])
    assert response["hint"] == list(session.optimal_path[1])
    assert response["player"]["hints_used"] == 1
    _walk(store, game["id"], session.optimal_path[:3])
    player = api.restart(store, game["id"])["player"]
    assert player["current"] == game["maze"]["start"] and player["moves"] == 0 and player["hints_used"] == 0


def test_solve_marks_solution_revealed() -> None:
    """Asking for a solver's path is recorded and returned with the final result."""
    store = api.GameStore()
    game = _new(store)
    solved = api.solve(store, game["id"], "a_star")
    assert solved["path_length"] == game["optimal_moves"]
    assert solved["explored_count"] == len(solved["explored_order"])
    session = store.get(game["id"])
    assert _walk(store, game["id"], session.optimal_path)["result"]["solution_revealed"] is True


def test_compare_runs_three_solvers() -> None:
    """compare returns BFS, DFS and A* results and a verdict sentence."""
    store = api.GameStore()
    game = _new(store)
    data = api.compare(store, game["id"])
    assert set(data["results"]) == {"bfs", "dfs", "a_star"}
    assert data["results"]["bfs"]["path_length"] == game["optimal_moves"]
    assert data["verdict"].endswith(".")


def test_store_drops_oldest_games() -> None:
    """The store never holds more than its limit."""
    store = api.GameStore(limit=3)
    ids = [_new(store)["id"] for _ in range(5)]
    assert len(store) == 3
    with pytest.raises(api.ApiError):
        store.get(ids[0])


def test_demo_and_spanning_trees() -> None:
    """The demo maze has a BFS path across it; a 3 x 3 grid has 192 spanning trees."""
    demo = api.demo({"rows": 5, "cols": 20, "seed": 1})
    assert demo["search"]["path"][0] == demo["maze"]["start"]
    assert api.spanning_trees({"rows": 3, "cols": 3})["count"] == "192"
    with pytest.raises(api.ApiError):
        api.spanning_trees({"rows": 30, "cols": 30})
