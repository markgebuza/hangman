# Development Log

Record of each step of building this project with an AI coding agent
(Claude Code), following the prompt sequence in the assignment guide.
For each step: the prompt used (short), what was built, test results, and
problems found + fixes.

---

## Step 1 — Prompt 1: Rescope the TODO

**Prompt (short):** "Read SPECIFICATION.md and TODO.md. Revise TODO.md into a
phased plan covering only engine, words, Flask API, browser client, testing,
docs/deploy config, cloud deployment. Keep out-of-scope phases at the bottom.
Keep the spec's REST API. No code yet."

**What was done:**
- Rewrote `TODO.md` into 7 in-scope phases, each with a task checklist and
  completion criteria.
- Moved terminal client, bots, evaluation mode, scoring, leaderboard,
  anti-cheating safeguards, logging/replay, and optional future phases into
  an "Out of Scope for This Assignment" section (kept, not deleted).
- `SPECIFICATION.md` untouched.

**Problems found:**
- The original `TODO.md` had **every** checkbox already checked (`[x]`) even
  though the repo contained no code. Leaving it like that would make the
  TODO meaningless as a progress tracker. Fix: all in-scope items reset to
  `[ ]` and are checked off only after verification; a note explains why.
- The original `TODO.md` referred to the spec as
  `Hangman_Project_Specification.md`, but the file in the repo is
  `SPECIFICATION.md`. Fix: references updated in TODO.md (the spec itself
  is not modified).

**Tests:** none (no code yet).

---

## Step 2 — Prompt 2: Check the plan against the assignment

**Prompt (short):** "Compare the revised TODO.md against the engine / server /
browser / tests / deployment requirements, list anything missing or
ambiguous, and propose concrete decisions (duplicate guesses, exact JSON
field names...). Add them to TODO.md. No code yet."

**What was done:**
- Added a "Plan Review Against Assignment Requirements" table to `TODO.md`
  listing each requirement, whether the draft covered it, and the action.
- Added a "Design Decisions" section: exact JSON field names, a full
  HTTP status-code table, case handling, whitespace handling, duplicate
  guesses, ID format, thread safety, single gunicorn worker, and the
  order of the 6 hangman body parts.

**Ambiguities found and decisions:**
- Spec says duplicates are "ignored or rejected" — chose **reject with
  409**, state unchanged (consistent with the spec's scoring section).
- Spec doesn't define error format — chose `{"error": "..."}` everywhere.
- Spec's guess response omits `game_id`; decided every response returns
  the same full state object (superset of the spec's fields) to keep the
  client simple.
- Missing `difficulty` → 400 (no silent default).

**Tests:** none (no code yet).

---

## Step 3 — Prompt 3: Game engine (+ word lists)

**Prompt (short):** "Implement Phase 1 in game.py: HangmanGame with hidden
word, guessed/incorrect letters, max 6 wrong, status playing/won/lost;
guess() accepts one a–z letter, rejects invalid/duplicate/after-end guesses
without changing state; pattern; to_dict() with word only after the end; no
Flask imports. Add tests/test_game.py. Create words/*.txt if missing."

**What was built:**
- `game.py`: `HangmanGame` class plus exceptions `GuessError` (base),
  `InvalidGuessError`, `DuplicateGuessError`, `GameOverError`. Status is
  derived from state (never stored separately) so it can't get out of sync.
  `__repr__` deliberately omits the word so it can't leak into logs.
- `words/easy.txt` (200 words, 4–7 letters), `words/medium.txt` (183, 5–9),
  `words/hard.txt` (184, 8–12). Written by hand by the agent; validated by a
  script: all lowercase a–z, lengths in range, no duplicates, no overlap
  between files.
- `tests/test_game.py`: correct, incorrect, uppercase, duplicate (case-
  insensitive), invalid inputs (`""`, `"ab"`, digits, punctuation, space,
  accented letter, non-strings), win, win on last life, loss, guess after
  win/loss, word hidden while playing, word revealed after win/loss, and a
  test that parses `game.py` and asserts it imports nothing but `string`.
- `pytest.ini` so `pytest` works from the repo root without installing
  the project.

**Tests:** `pytest` → **47 passed**, 0 failed.

**Problems found + fixes:**
- Word-list validation script flagged `gazebo` (6 letters) in `hard.txt`,
  below the 8-letter minimum — replaced with `graceful`. Also replaced
  `eclipsed` (an inflected form) with `election` and `saloon` with `sandal`,
  and trimmed easy.txt from 206 to 200 words.

---

## Step 4 — Prompt 4: Word management

**Prompt (short):** "Implement Phase 2: words.py loads easy/medium/hard,
strips, lowercases, drops non-alphabetic lines and duplicates, provides
random_word(difficulty); invalid difficulty raises a clear error; paths
resolved relative to the module file. Add tests/test_words.py."

**What was built:**
- `words.py`: `WORDS_DIR` resolved from `__file__`; `load_word_file()`
  (strip, lowercase, drop blanks / non a–z / duplicates, keep order);
  `WordManager` (loads all three lists once, refuses an empty list, uses
  `random.SystemRandom`); module-level `random_word(difficulty)` using a
  lazily created shared manager; `InvalidDifficultyError(ValueError)` whose
  message lists the valid options. Difficulty is case-insensitive.
- `tests/test_words.py`: shipped files are clean (≥150 words, a–z, correct
  length range, no duplicates, no cross-file overlap), random words come
  from the right list and vary, invalid difficulties (`""`, `"expert"`,
  `" easy"`, `None`, `1`, list) raise, cleaning logic on a temp file,
  missing/empty files, and a subprocess test that imports `words` from a
  **different working directory** (simulates Render starting elsewhere).

**Tests:** `pytest` → **71 passed** (47 engine + 24 words), 0 failed.

**Problems found + fixes:**
- Potential name clash: the module `words.py` and the data directory
  `words/` share a name. Checked that `import words` resolves to the module
  (a plain module wins over a directory without `__init__.py`); the
  different-cwd subprocess test confirms it. Kept the spec's layout.

---

## Step 5 — Prompt 5: Flask REST API

**Prompt (short):** "Implement Phase 3 in server.py: in-memory dict of games
keyed by uuid4 hex; POST /api/games -> 201; GET /api/games/<id> -> 200/404;
POST /api/games/<id>/guess -> 200, 400 bad JSON/letter/difficulty, 409
duplicate/game over, 404 unknown; JSON errors; never send the word while
playing; serve static/index.html at /. Add tests/test_api.py. Show curl
commands to play by hand."

**What was built:**
- `server.py`: `create_app(word_source=None)` app factory (tests inject a
  fixed word so games are deterministic) plus a module-level `app` for
  gunicorn (`server:app`). `GameStore` wraps the dict with a
  `threading.Lock`. Engine exceptions map to HTTP codes:
  `InvalidGuessError` → 400, `DuplicateGuessError`/`GameOverError` → 409.
  A generic `HTTPException` handler makes 404/405/413 JSON too. API
  responses get `Cache-Control: no-store`. Body size capped at 16 KB.
  `/healthz` endpoint for Render health checks. Word lists are loaded at
  startup so a missing file fails at boot, not on the first request.
  `python server.py` runs with debug **off** unless `FLASK_DEBUG=1`.
- Placeholder `static/index.html` (real client comes in Phase 4).
- `tests/test_api.py` (41 tests): every status code (201, 200, 400, 404,
  405, 409), bad bodies (`"not json"`, `""`, `[1,2]`, `"easy"`, broken
  JSON), invalid letters, missing fields, state unchanged after rejected
  guesses, unique IDs, and full winning/losing games asserting `word` is
  absent from every POST *and* GET response until the end.

**Tests:** `pytest` → **112 passed**, 0 failed.

**Manual curl check:** started `python3 server.py`, created an easy game,
guessed e a o i s t r n → pattern progressed `_ _ _ _ _` → `s n a _ e`,
incorrect letters o i t r, remaining 2, no `word` field; `"7"` → 400,
unknown id → 404, POST without Content-Type header → 201 (body is parsed
as JSON regardless of header, by design, so plain `curl -d` works).

**Problems found + fixes:**
- Decided to parse the body with `get_json(force=True, silent=True)` after
  noticing that a `curl -d '{...}'` without `-H 'Content-Type:
  application/json'` would otherwise be rejected with a confusing
  error. Non-object JSON (e.g. a list or a bare string) is still a 400.
- Small tooling gotcha: `pkill -f "python3 server.py"` inside the same
  shell command also matched the shell running it (exit code 144). The
  server was stopped correctly; later steps start/stop servers by PID.
