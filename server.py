"""Flask REST API for Hangman.

Endpoints (see README.md for full examples):
    POST /api/games                    {"difficulty": "easy|medium|hard"} -> 201
    GET  /api/games/<game_id>                                             -> 200
    POST /api/games/<game_id>/guess    {"letter": "e"}                    -> 200

All game rules live in ``game.py``; this module only translates HTTP
requests into engine calls and engine results/exceptions into JSON.
Games are kept in memory, so run a single worker process in production.
"""

import os
import threading
import uuid

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

import words
from game import DuplicateGuessError, GameOverError, HangmanGame, InvalidGuessError


class GameStore:
    """Thread-safe in-memory mapping of game_id -> HangmanGame."""

    def __init__(self):
        self._games = {}
        self._lock = threading.Lock()

    def add(self, game):
        with self._lock:
            self._games[game.game_id] = game

    def get(self, game_id):
        with self._lock:
            return self._games.get(game_id)

    def lock(self):
        return self._lock

    def __len__(self):
        with self._lock:
            return len(self._games)


def error(message, status):
    response = jsonify({"error": message})
    response.status_code = status
    return response


def create_app(word_source=None):
    """Build the Flask app.

    ``word_source`` is a callable ``difficulty -> word``; tests pass a fixed
    word so games are deterministic. Defaults to ``words.random_word``.
    """
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # request bodies are tiny
    app.json.sort_keys = False

    if word_source is None:
        words.get_manager()  # load word lists at startup so problems fail fast
        word_source = words.random_word

    store = GameStore()
    app.extensions["hangman_store"] = store

    def read_json_object():
        """Return the request body as a dict, or None if it isn't a JSON object."""
        data = request.get_json(force=True, silent=True)
        return data if isinstance(data, dict) else None

    # ------------------------------------------------------------- routes

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.get("/healthz")
    def healthz():
        return jsonify({"status": "ok"})

    @app.post("/api/games")
    def create_game():
        data = read_json_object()
        if data is None:
            return error("request body must be a JSON object", 400)
        if "difficulty" not in data:
            return error("missing field 'difficulty' (easy, medium, or hard)", 400)
        try:
            difficulty = words.normalize_difficulty(data["difficulty"])
        except words.InvalidDifficultyError as exc:
            return error(str(exc), 400)

        game = HangmanGame(word_source(difficulty),
                           game_id=uuid.uuid4().hex, difficulty=difficulty)
        store.add(game)
        return jsonify(game.to_dict()), 201

    @app.get("/api/games/<game_id>")
    def get_game(game_id):
        game = store.get(game_id)
        if game is None:
            return error(f"game '{game_id}' not found", 404)
        with store.lock():
            return jsonify(game.to_dict())

    @app.post("/api/games/<game_id>/guess")
    def guess(game_id):
        game = store.get(game_id)
        if game is None:
            return error(f"game '{game_id}' not found", 404)
        data = read_json_object()
        if data is None:
            return error("request body must be a JSON object", 400)
        if "letter" not in data:
            return error("missing field 'letter'", 400)

        with store.lock():
            try:
                game.guess(data["letter"])
            except InvalidGuessError as exc:
                return error(str(exc), 400)
            except (DuplicateGuessError, GameOverError) as exc:
                return error(str(exc), 409)
            return jsonify(game.to_dict())

    # ------------------------------------------------------------- errors

    @app.errorhandler(HTTPException)
    def http_error(exc):
        # 404 for unknown routes, 405 for wrong methods, 413 for huge bodies...
        return error(exc.description, exc.code)

    @app.errorhandler(Exception)
    def unexpected_error(exc):
        app.logger.exception("unhandled error")
        return error("internal server error", 500)

    @app.after_request
    def no_cache_api(response):
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return app


app = create_app()


if __name__ == "__main__":
    # Local development only. In production gunicorn imports `server:app`.
    app.run(host="127.0.0.1",
            port=int(os.environ.get("PORT", "5000")),
            debug=os.environ.get("FLASK_DEBUG") == "1")
