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

---

## Step 6 — Prompt 6: Browser client

**Prompt (short):** "Implement Phase 4: index.html, style.css, app.js.
Difficulty select + New Game; masked word, guessed/incorrect letters,
remaining guesses; on-screen A–Z keyboard that disables guessed letters;
physical keyboard (ignored when game over); SVG hangman with 6 parts;
win/loss message with the word from the server; new game without reload;
all state from fetch(); show server errors; desktop + phone; relative URLs."

**What was built:**
- `static/index.html`: header with `<select>` + New Game (a `<form>` whose
  submit is `preventDefault`-ed, so no reload), inline SVG gallows with 6
  `.part` elements (head, body, left arm, right arm, left leg, right leg),
  pattern, stats, status message (`aria-live`), keyboard container.
- `static/app.js`: `api()` fetch wrapper that turns non-2xx responses into
  an `ApiError` carrying the server's `error` text; `startNewGame()`,
  `guessLetter()`, `render()`, `updateKeyboard()`. The JS never decides
  if a guess is right: it renders `pattern`, `incorrect_letters`,
  `status`, and shows `word` only when the server includes it at the end.
  A `busy` flag prevents double submits while a request is in flight.
  The game id (never the word) is kept in `sessionStorage` so a page
  refresh resumes the game via `GET /api/games/<id>`; if the server
  answers 404 (e.g. Render restarted and lost memory), the UI says so and
  asks for a new game instead of failing silently.
- `static/style.css`: light + dark colour schemes, CSS grid layout that
  stacks on phones, 13-column keyboard on desktop / 7-column on phones,
  44px touch targets; correct keys green, incorrect keys red.

**Manual/browser checks (headless Chromium via Playwright, scripted):**
- Played a medium game by clicking letters → lost on "pancake": 6 parts
  shown, incorrect `t o i s h r`, message `You lost. The word was
  "pancake".`
- Switched to Hard + New Game: new pattern, a JS marker variable survived
  (proves no page reload). Physical key `e` guessed and disabled the key;
  pressing `e` again sent no request and showed no error.
- Page reload resumed the same game. Killed the server → clicking a
  letter showed "Could not reach the server…". Restarted the server →
  clicking showed "This game no longer exists on the server…", all keys
  disabled; New Game worked again.
- No console errors. Dark mode checked by screenshot.

**Tests:** `pytest` → **112 passed** (no new automated tests in this step;
the browser test is added in Step 8).

**Problems found:**
- First version drew the not-yet-revealed body parts as faint "ghost"
  lines. That makes it look like the whole figure is already drawn, so it
  was changed to hide unrevealed parts completely (`opacity: 0`).
- **Bug found at phone width (375px):** on Hard, the 10-letter pattern
  wrapped onto two lines in the middle of the word. Fixed in Step 7.

---

## Step 7 — Prompt 7: Fix what I found (pattern wrapping on phones)

**Prompt (short):** "While playing I saw: on Hard, at phone width, the
masked word wraps onto two lines in the middle of the word. Find the root
cause, fix it, add a regression test, run the full suite."

**Root cause:** the pattern for a 12-letter word is 23 characters
(`_ _ _ … _`). The CSS used `font-size: clamp(1.6rem, 6vw, 2.6rem)`,
`letter-spacing: 0.15em`, and `word-break: break-all`. The minimum
1.6rem was too big for a 375px phone, and `break-all` let the browser
split anywhere. The font size was also tied to the *viewport* (`vw`), not
to the column the pattern lives in, so it **also wrapped on desktop**
(the regression test proved this — see below).

**Fix (`static/style.css`):**
- `white-space: nowrap`, smaller letter-spacing, and font size based on
  the pattern's container width: `.state { container-type: inline-size }`
  + `font-size: clamp(0.9rem, 5.6cqi, 2.6rem)` (with a plain `1.4rem`
  fallback line for older browsers).
- **Second bug introduced by the fix:** on phones `.board` uses
  `justify-items: center`; a size container gets no width from its
  content, so `.state` collapsed to **0px wide** and the pattern
  overflowed. Caught by the new test (`clientWidth` was 0). Fixed by
  stretching `.state` to `width: 100%` in the mobile media query.
- Also switched the pattern from uppercase to lowercase because an
  uppercase monospace `O` looked like a zero in the screenshot.

**Regression test:** `tests/test_e2e.py::test_long_pattern_stays_on_one_line`
(Playwright, widths 320 / 375 / 1100, word `kaleidoscope`): asserts the
pattern is one line high, not clipped, and the page has no horizontal
scroll. Verified it is a real regression test:
- with the **old** CSS: 3 failed (320, 375, **and 1100**);
- with the first fix only: 2 failed (320, 375 — the 0px container);
- with the final fix: 3 passed.

**Tests:** `pytest` → **115 passed**, 0 failed.

Also added a minimal `.gitignore` (`__pycache__/`, `.pytest_cache/`)
because the test run created bytecode files that showed up in
`git status`.

---

## Step 8 — Prompt 8: Test-coverage audit

**Prompt (short):** "Audit the tests against: all difficulties, correct /
incorrect / repeated / invalid guesses (digits, "", "ab", missing field,
non-JSON), win, loss, guess after game over, new game after one ends,
unknown ID, invalid difficulty, word absent from every response while
playing, two simultaneous games. Add one end-to-end browser test. Run
everything and summarize pass/fail."

**Audit result — gaps found and filled:**
| Gap | Added |
|---|---|
| API tests only used one difficulty with a fixed word | `test_start_game_each_difficulty_real_words` (real lists, checks pattern length is a valid length for that list) |
| "word absent" only checked on 2 scripted games | `test_word_never_present_while_playing_real_words`: 15 full random games (3 difficulties × 5 seeds), every POST **and** GET response checked |
| New game after one ends | `test_new_game_after_previous_game_ends` |
| Two simultaneous games | `test_two_simultaneous_games_do_not_interfere` + `test_concurrent_duplicate_guesses_accepted_once` (12 threads guess the same letter at once → exactly one 200, eleven 409s) |
| Error shape not checked uniformly | `test_error_responses_are_json_with_error_key`, `test_oversized_body_rejected` (413) |
| Difficulty case-insensitivity untested at API level | `test_difficulty_is_case_insensitive` |
| No browser flow tests | 9 Playwright tests in `tests/test_e2e.py`: click letters + page/drawing/key colours update, request payload is `{"letter": "e"}`, win, loss (drawing grows 1→6), physical keyboard incl. ignored after game over, new game without reload, hidden word not in JS state / DOM / sessionStorage / any API response body while playing, server error messages shown (404 and 500 via route mocking), reload resumes game, phone width has no horizontal scroll |

- `tests/test_e2e.py` uses `pytest.importorskip("playwright.sync_api")` and
  skips if Chromium can't launch, so `pytest` still works on a machine
  without Playwright. It starts a real threaded werkzeug server on a free
  port with a controllable fixed word.
- `TESTING.md`: how to run tests, a table mapping each checklist item to
  test names, and a manual browser checklist for the demo.

**Tests:** `pytest` → **148 passed, 0 failed** (engine 47, words 24, API 65,
browser 12). Ran the full suite 5× in a row: 148 passed each time (no
flaky tests observed). With Playwright hidden from the import path:
**136 passed, 1 skipped** (the e2e module).

**Problems found + fixes:**
- My first assertion `"correct" in key.get_attribute("class")` would also
  pass for a key with class `incorrect` (substring match). Tightened to
  compare the exact class list.
- When I first simulated "Playwright not installed" by making the import
  raise a plain `ImportError`, the run **errored** instead of skipping:
  pytest 9's `importorskip` only skips on `ModuleNotFoundError`. A real
  missing package raises `ModuleNotFoundError`, so the real scenario does
  skip correctly (verified with a corrected simulation, and again in a
  fresh venv in Step 10).
- Honest caveat: the concurrency test passes, but under CPython's GIL the
  race it guards against is rare, so passing doesn't fully prove the lock
  is needed — it's a guard against regressions, not a proof.

---

## Step 9 — Prompt 9: Understand the request/response flow

**Prompt (short):** "Walk me through exactly what happens when I click
the letter E: JS function, fetch() request (method, URL, body), Flask
route, what the engine does, JSON returned, how the JS updates the DOM.
File names and line numbers. Then what to look for in Chrome DevTools >
Network for the demo."

**What was produced:** `docs/REQUEST_FLOW.md`
- ASCII sequence diagram browser → Flask route → engine → back.
- 15 numbered steps with `file:line` references (`static/app.js`,
  `server.py`, `game.py`), the exact HTTP request and response.
- A DevTools demo guide: Fetch/XHR filter, what to show in Headers /
  Payload / Response for `POST /api/games` and `POST …/guess`, where the
  `word` field first appears, how to show a 404/409 from the Console, and
  how to prove New Game doesn't reload the page.

**Verification:** every line reference was checked against the files
with `sed -n` after writing (all matched). Re-checked again at the end
of the project (Step 14) in case later edits shifted lines.

**Tests:** no code changes; `pytest` → 148 passed.

---

## Step 10 — Prompt 10: Deployment readiness + README

**Prompt (short):** "Prepare for Render: pinned requirements.txt,
render.yaml (free, build pip install, start gunicorn --workers 1
server:app — explain why one worker), .gitignore, debug off, no secrets.
Write README: overview, structure, local setup, tests, API reference with
examples, deployment, known limitations. Run tests; verify a fresh install
using only the README in a new venv."

**What was built:**
- `requirements.txt`: `Flask==3.1.3`, `Werkzeug==3.1.9`,
  `gunicorn==26.2.0`, `pytest==9.1.1`.
- `requirements-dev.txt`: adds `playwright==1.63.0` for the optional
  browser tests (kept out of the main file so Render doesn't install it).
- `render.yaml`: free Python web service, build/start commands as given,
  `healthCheckPath: /healthz`, with a comment explaining the single worker.
- `.gitignore`: venv/.venv/env, `__pycache__`, `*.pyc`, `.pytest_cache`,
  `.env`, `.DS_Store`, editor folders.
- `README.md`: everything requested, incl. the "why one worker"
  explanation, a status-code table, documented additions to the spec's
  API, Render steps (Blueprint and manual), and known limitations. Live URL
  is a placeholder until the student deploys.

**Verification:**
- Secret scan (`grep` for secret/key/password/token/private key):
  nothing found. Debug is off by default (`FLASK_DEBUG` must be set to
  `1` explicitly); gunicorn never calls `app.run`.
- **Fresh install** following only the README: copied the tracked files to
  an empty directory, `python3 -m venv venv`, `pip install -r
  requirements.txt`, `pytest` → **136 passed, 1 skipped** (Playwright not
  in the fresh venv, so the browser tests skipped cleanly — this is the
  real-world confirmation promised in Step 8). `python server.py` →
  "Debug mode: off", `/` → 200, `POST /api/games` → 201. Then gunicorn with
  exactly the Render start command (port 8123) → `/healthz` 200, `/` 200.
- Full suite in the dev environment: **148 passed**.

**Problems found + fixes:**
- Noticed the pinned gunicorn 26.x and pytest 9.x require **Python ≥3.10**
  (checked `Requires-Python` metadata). macOS's built-in `python3` can be
  3.9, so the README now states "Python 3.10 or newer" and explains how to
  set `PYTHON_VERSION` on Render if its build ever picks an older Python.
- My first README API examples were inconsistent (same game ID, but a
  pattern containing `e` for the word `canvas`). Fixed so all examples
  describe one consistent game.
- Not verified here (needs the student's accounts): the actual Render
  build. The README's log excerpt is what gunicorn printed locally plus
  Render's usual build/live lines, so exact wording on Render may differ.
