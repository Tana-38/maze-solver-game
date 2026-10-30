"""Tests for web/api.py (the JSON API behind the browser frontend).

Owner: Role 4: Game Logic & Integration.
"""

import pytest

from web import api

DIRS = {(-1, 0): "up", (1, 0): "down", (0, -1): "left", (0, 1): "right"}


def _new(store: api.TokenStore, **body) -> dict:
    return api.create_game(store, {"difficulty": "easy", "seed": 7, **body})


def _walk(store: api.TokenStore, token: str, path: list) -> dict:
    """Move along path; each response carries the next token."""
    response = {"id": token}
    for a, b in zip(path, path[1:]):
        response = api.move(store, response["id"], {"direction": DIRS[(b[0] - a[0], b[1] - a[1])]})
        assert response["moved"]
    return response


def test_create_game_returns_maze_and_analysis() -> None:
    """A new easy game is 10 x 10, reproducible from its seed, and connected."""
    store = api.TokenStore()
    game = _new(store)
    maze = game["maze"]
    assert (maze["rows"], maze["cols"]) == (10, 10)
    assert len(maze["open_right"]) == 10 and len(maze["open_right"][0]) == 10
    assert game["analysis"]["connected"]
    assert game["analysis"]["degree_sum"] == 2 * game["analysis"]["edges"]  # Handshake Lemma
    assert _new(api.TokenStore())["maze"] == maze


def test_perfect_custom_maze_is_tree() -> None:
    """With braid 0 the maze is a spanning tree: |E| = |V| - 1 and no cycles."""
    game = api.create_game(api.TokenStore(), {"difficulty": "custom", "rows": 6, "cols": 9, "braid": 0, "algorithm": "kruskal"})
    stats = game["analysis"]
    assert stats["is_tree"] and stats["edges"] == stats["vertices"] - 1 and stats["cycles"] == 0


def test_bad_settings_rejected() -> None:
    """Invalid options raise ApiError with status 400."""
    store = api.TokenStore()
    for body in [{"difficulty": "extreme"}, {"algorithm": "magic"}, {"difficulty": "custom", "rows": 999}, {"mode": "middle"}]:
        with pytest.raises(api.ApiError) as err:
            api.create_game(store, body)
        assert err.value.status == 400


def test_unknown_game_is_404() -> None:
    """A token that is not a valid signed game gives a 404."""
    with pytest.raises(api.ApiError) as err:
        api.move(api.TokenStore(), "nope", {"direction": "up"})
    assert err.value.status == 404


def test_tampered_or_foreign_token_rejected() -> None:
    """Editing the token, or using one signed with another secret, is refused."""
    game = _new(api.TokenStore("secret-a"))
    payload, _, signature = game["id"].partition(".")
    forged = payload[:-2] + ("AA" if payload[-2:] != "AA" else "BB") + "." + signature
    for store, token in [(api.TokenStore("secret-a"), forged), (api.TokenStore("secret-b"), game["id"])]:
        with pytest.raises(api.ApiError) as err:
            store.get(token)
        assert err.value.status == 404


def test_token_round_trip_keeps_state() -> None:
    """Saving and reloading a session keeps position, counters and flags."""
    store = api.TokenStore()
    game = _new(store)
    session = store.get(game["id"])
    token = _walk(store, game["id"], session.optimal_path[:4])["id"]
    token = api.hint(store, token)["id"]
    restored = store.get(token)
    assert restored.controller.state.current == session.optimal_path[3]
    assert restored.controller.state.moves == 3
    assert restored.controller.state.hints_used == 1
    assert restored.first_move_at is not None and restored.finished_at is None


def test_wall_blocks_move() -> None:
    """Moving off the grid from the start corner is rejected and not counted."""
    store = api.TokenStore()
    game = _new(store)
    response = api.move(store, game["id"], {"direction": "up"})
    assert response["moved"] is False
    assert response["player"]["moves"] == 0


def test_optimal_walk_scores_perfect() -> None:
    """Walking the BFS path finishes the game with score 1 and both paths returned."""
    store = api.TokenStore()
    game = _new(store)
    session = store.get(game["id"])
    response = _walk(store, game["id"], session.optimal_path)
    result = response["result"]
    assert response["player"]["finished"]
    assert result["score"] == 1.0 and result["rating"] == "Perfect"
    assert result["player_moves"] == result["optimal_moves"] == game["optimal_moves"]
    assert result["solution_revealed"] is False
    assert api.move(store, response["id"], {"direction": "left"})["moved"] is False  # game over


def test_hint_and_restart() -> None:
    """A hint is the next BFS cell and is counted; restart resets the player."""
    store = api.TokenStore()
    game = _new(store)
    session = store.get(game["id"])
    response = api.hint(store, game["id"])
    assert response["hint"] == list(session.optimal_path[1])
    assert response["player"]["hints_used"] == 1
    token = _walk(store, response["id"], session.optimal_path[:3])["id"]
    restarted = api.restart(store, token)
    player = restarted["player"]
    assert player["current"] == game["maze"]["start"] and player["moves"] == 0 and player["hints_used"] == 0
    assert store.get(restarted["id"]).moves == []


def test_solve_marks_solution_revealed() -> None:
    """Asking for a solver's path is recorded and returned with the final result."""
    store = api.TokenStore()
    game = _new(store)
    solved = api.solve(store, game["id"], "a_star")
    assert solved["path_length"] == game["optimal_moves"]
    assert solved["explored_count"] == len(solved["explored_order"])
    session = store.get(solved["id"])
    assert _walk(store, solved["id"], session.optimal_path)["result"]["solution_revealed"] is True


def test_compare_runs_three_solvers() -> None:
    """compare returns BFS, DFS and A* results and a verdict sentence."""
    store = api.TokenStore()
    game = _new(store)
    data = api.compare(store, game["id"])
    assert set(data["results"]) == {"bfs", "dfs", "a_star"}
    assert data["results"]["bfs"]["path_length"] == game["optimal_moves"]
    assert data["verdict"].endswith(".")


def test_demo_and_spanning_trees() -> None:
    """The demo maze has a BFS path across it; a 3 x 3 grid has 192 spanning trees."""
    demo = api.demo({"rows": 5, "cols": 20, "seed": 1})
    assert demo["search"]["path"][0] == demo["maze"]["start"]
    assert api.spanning_trees({"rows": 3, "cols": 3})["count"] == "192"
    with pytest.raises(api.ApiError):
        api.spanning_trees({"rows": 30, "cols": 30})
