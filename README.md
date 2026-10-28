# Hangman (web)

A web-based Hangman game for CSE 4095: a Python game engine, a Flask REST
API, and an HTML/CSS/JavaScript browser client, deployed on Render.

**Live site:** `https://<your-app>.onrender.com` *(replace after deploying —
see [Deploying to Render](#deploying-to-render))*

The server is authoritative: all game rules run in Python, and the hidden
word is never sent to the browser until the game is over. The browser only
renders the JSON the server returns.

The original project specification is in [`SPECIFICATION.md`](SPECIFICATION.md)
(unmodified). This assignment implements only the web game; the terminal
client, bots, evaluation mode, scoring, leaderboard, and logging/replay are
out of scope (see [`TODO.md`](TODO.md)).

## Project structure

```
hangman/
├── SPECIFICATION.md      original spec (unmodified)
├── TODO.md               phased plan, design decisions, out-of-scope list
├── README.md             this file
├── TESTING.md            how to test + manual browser checklist
├── DEV_LOG.md            per-step development log
├── docs/REQUEST_FLOW.md  what happens when you click a letter + DevTools guide
├── requirements.txt      pinned runtime + test dependencies
├── requirements-dev.txt  + Playwright for browser tests (optional)
├── render.yaml           Render Blueprint (deployment config)
├── pytest.ini
├── game.py               game engine (no Flask, no UI)
├── words.py              word-list loading + random word selection
├── server.py             Flask app + REST API
├── smoke_test.py         checks a running/deployed server end to end
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js            browser client (fetch() only, no game logic)
├── words/
│   ├── easy.txt          200 words, 4–7 letters
│   ├── medium.txt        183 words, 5–9 letters
│   └── hard.txt          184 words, 8–12 letters
└── tests/
    ├── test_game.py      engine unit tests
    ├── test_words.py     word-list tests
    ├── test_api.py       REST API tests (Flask test client)
    ├── test_e2e.py       browser tests (Playwright; skipped if not installed)
    └── test_smoke.py     runs smoke_test.py against a local server
```

## Local setup

Requires **Python 3.10 or newer** (`python3 --version`).

```bash
git clone https://github.com/<your-username>/hangman.git
cd hangman

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Run the server

```bash
python server.py
```

Then open **http://127.0.0.1:5000/** in your browser. Stop with Ctrl+C.

- Different port: `PORT=8000 python server.py`
  (Windows PowerShell: `$env:PORT=8000; python server.py`)
- Debug mode (auto-reload, detailed errors) is **off** by default. Turn it on
  only locally: `FLASK_DEBUG=1 python server.py`.
- To run it the same way Render does (Linux/macOS only, gunicorn doesn't
  run on Windows): `gunicorn --bind 0.0.0.0:8000 --workers 1 server:app`

## Running the tests

```bash
pytest            # all tests
pytest -v         # verbose
```

The browser tests in `tests/test_e2e.py` are skipped unless Playwright is
installed. To run them too:

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium
pytest
```

Current result: **149 passed** with Playwright installed (137 passed,
1 module skipped without it). See [`TESTING.md`](TESTING.md) for what each
test covers and a manual browser checklist.

### Smoke test against a running server

```bash
python smoke_test.py http://127.0.0.1:5000
python smoke_test.py https://<your-app>.onrender.com
```

It loads `/`, creates games at all three difficulties, makes a valid,
an invalid and a duplicate guess, plays one game to the end, checks every
status code, and confirms `word` never appears while a game is in progress.
It allows up to 60 s per request for free-tier cold starts and exits with
a non-zero code if any check fails. Uses only the Python standard library.

## REST API

All request and response bodies are JSON. Every error response has the
form `{"error": "<message>"}`.

### Game state object

Returned by all three endpoints:

| Field | Type | Meaning |
|---|---|---|
| `game_id` | string | 32-char hex ID (uuid4) |
| `difficulty` | string | `easy`, `medium`, or `hard` |
| `pattern` | string | masked word, letters/underscores separated by spaces, e.g. `"_ e _ _ e"` |
| `guessed_letters` | list | every accepted guess, in the order guessed |
| `incorrect_letters` | list | accepted guesses not in the word, in order |
| `remaining_guesses` | int | incorrect guesses left (starts at 6) |
| `max_incorrect` | int | always 6 |
| `status` | string | `playing`, `won`, or `lost` |
| `word` | string | **only present when `status` is `won` or `lost`** |

### `POST /api/games` — create a game

```bash
curl -X POST http://127.0.0.1:5000/api/games \
     -H "Content-Type: application/json" \
     -d '{"difficulty": "medium"}'
```

`201 Created`

```json
{
  "game_id": "7108923cf3a4463f884863f47bd3c74c",
  "difficulty": "medium",
  "pattern": "_ _ _ _ _ _",
  "guessed_letters": [],
  "incorrect_letters": [],
  "remaining_guesses": 6,
  "max_incorrect": 6,
  "status": "playing"
}
```

`difficulty` is required and must be `easy`, `medium`, or `hard`
(case-insensitive). Otherwise `400`:

```json
{"error": "invalid difficulty 'expert'; expected one of: easy, medium, hard"}
```

### `GET /api/games/{game_id}` — current state

```bash
curl http://127.0.0.1:5000/api/games/7108923cf3a4463f884863f47bd3c74c
```

`200 OK` with the game state, or `404` if the ID is unknown:

```json
{"error": "game 'abc' not found"}
```

### `POST /api/games/{game_id}/guess` — guess a letter

```bash
curl -X POST http://127.0.0.1:5000/api/games/7108923cf3a4463f884863f47bd3c74c/guess \
     -H "Content-Type: application/json" \
     -d '{"letter": "a"}'
```

`200 OK`

```json
{
  "game_id": "7108923cf3a4463f884863f47bd3c74c",
  "difficulty": "medium",
  "pattern": "_ a _ _ a _",
  "guessed_letters": ["a"],
  "incorrect_letters": [],
  "remaining_guesses": 6,
  "max_incorrect": 6,
  "status": "playing"
}
```

When the game ends, the response includes the word:

```json
{
  "game_id": "7108923cf3a4463f884863f47bd3c74c",
  "difficulty": "medium",
  "pattern": "c a n v a s",
  "guessed_letters": ["a", "e", "s", "t", "n", "c", "v"],
  "incorrect_letters": ["e", "t"],
  "remaining_guesses": 4,
  "max_incorrect": 6,
  "status": "won",
  "word": "canvas"
}
```

### Status codes

| Situation | Code |
|---|---|
| Game created | 201 |
| State returned / guess accepted | 200 |
| Body missing, not JSON, or not a JSON object | 400 |
| `difficulty` missing or invalid | 400 |
| `letter` missing, empty, more than one character, or not a–z | 400 |
| Letter already guessed (duplicate) | 409 |
| Guess after the game is over | 409 |
| Unknown game ID or unknown `/api/…` URL | 404 |
| Wrong HTTP method | 405 |

Rejected guesses (400/409) never change the game state and never cost a
life. Letters are case-insensitive (`"E"` is treated as `"e"`).

### Additions to the spec's API

These are compatible extensions, not changes:
- Every response returns the full state object (the spec's guess example
  omits `game_id`; here it's always included), plus `difficulty` and
  `max_incorrect`.
- Duplicate guesses are *rejected* with 409 (the spec allows "ignored or
  rejected").
- `GET /healthz` → `{"status": "ok"}` for Render's health check.

## Deploying to Render

Render's free tier serves the app over HTTPS at `https://<name>.onrender.com`.

1. **Push to GitHub.** Make sure the repo contains `requirements.txt`,
   `render.yaml`, and everything above, then `git push origin main`.
2. **Sign in to Render** at https://dashboard.render.com with your GitHub
   account and allow Render to access the `hangman` repository.
3. **Create the service** — either:
   - **Blueprint (uses `render.yaml`):** *New → Blueprint* → choose the
     repo → Render reads `render.yaml` → *Apply* / *Deploy Blueprint*.
   - **Manual Web Service:** *New → Web Service* → choose the repo, then:
     - Language / Runtime: **Python 3**
     - Branch: `main`
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 1 server:app`
     - Instance Type: **Free**
     - (optional) Advanced → Health Check Path: `/healthz`
4. **Watch the logs.** A successful deploy shows the build installing
   Flask/gunicorn, then gunicorn starting, roughly:
   ```
   ==> Build successful 🎉
   ==> Running 'gunicorn --bind 0.0.0.0:$PORT --workers 1 server:app'
   [INFO] Starting gunicorn 26.2.0
   [INFO] Listening at: http://0.0.0.0:10000
   [INFO] Using worker: sync
   [INFO] Booting worker with pid: …
   ==> Your service is live 🎉
   ```
5. **Verify:** open the URL Render shows, play a game, then run
   `python smoke_test.py https://<your-app>.onrender.com`.
6. Put the URL at the top of this README.

If the build fails because of the Python version (all pinned packages need
3.10+), add an environment variable `PYTHON_VERSION` with a 3.10+ version
such as `3.12.8` in the service's *Environment* settings.

### Why exactly one worker?

Games are stored in a Python dict inside the server process. gunicorn's
`--workers N` starts N separate processes, each with its **own** dict. With
2+ workers, the game created by one request could be unknown to the worker
that handles the next request, giving random `404 game not found` errors.
One worker keeps all games in one place. (Within that one process, a lock
around the dict makes it safe to add `--threads N` later if needed.)

### Production settings

- Debug mode is off: gunicorn imports `server:app` and never calls
  `app.run(debug=...)`; `python server.py` also defaults to debug off.
- There are no secrets, API keys, or `.env` files in this project, and
  `.env` is in `.gitignore`.

## Known limitations

- **In-memory state.** All games are lost when the server restarts or
  redeploys. Render's free instances also restart after being idle. The
  browser detects this (the server returns 404 for the old game) and asks
  you to start a new game.
- **Free-tier cold starts.** A free Render service sleeps after about
  15 minutes without traffic; the next visit can take up to a minute while
  it wakes up.
- **Single worker.** Required by the in-memory store (see above); this
  limits throughput, which is fine for a class project.
- **No cleanup of old games.** Finished and abandoned games stay in memory
  until the next restart. Fine at this scale, but a real deployment would
  expire old games or use a database/Redis.
- **No accounts, persistence, or rate limiting**; anyone with a game ID
  can play that game.
- Browser support: needs a modern browser (2023+) for the CSS container
  units that keep long words on one line; older browsers fall back to a
  fixed font size.
