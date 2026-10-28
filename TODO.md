# TODO — Web-Based Hangman (CSE 4095, reduced scope)

This file is the implementation roadmap for this assignment.

The authoritative system requirements are defined in `SPECIFICATION.md`
(kept unmodified). This plan implements only the parts of the specification
needed for a web-based Hangman game: a Python game engine, a Flask REST API,
an HTML/CSS/JavaScript browser client, and a cloud deployment on Render.

## Implementation Rules

- Implement one phase at a time.
- Complete and test all items in the current phase before moving to the next phase.
- Do not change the REST API defined in `SPECIFICATION.md` unless necessary.
  Any deviation or addition is documented in `README.md`.
- Keep the game engine independent from Flask and the browser UI.
- The server is authoritative: all game rules run on the server.
- Never expose the hidden word before a game ends.
- Add tests as each phase is implemented rather than postponing testing until the end.
- Check off an item only after it has been implemented **and** verified.

> Note: the original TODO had every box pre-checked even though no code
> existed yet. All in-scope items below start unchecked and are checked off
> only as they are verified.

---

## Plan Review Against Assignment Requirements

Gaps and ambiguities found when comparing the first draft of this plan with
the assignment requirements:

| Requirement | In draft plan? | Action |
|---|---|---|
| Engine independent of Flask/UI | Yes (Phase 1) | — |
| No guesses after game ends | Yes | Added explicit test item |
| Unique game IDs, separate game states | Partly | Added "two simultaneous games don't interfere" test |
| Request validation + correct status codes | Vague | Status-code table below |
| Hidden word never sent while `playing` | Yes | Test **every** response, not just one |
| Click **and** physical keyboard | Yes | Physical keys ignored after game over |
| Hangman drawing updates | Yes | Exactly 6 parts, one per wrong guess |
| New game without page reload | Yes | — |
| No game logic / hidden word in JS | Yes | JS only renders server responses |
| Tests for all of the above | Partly | Phase 5 audit + E2E browser test |
| Public HTTPS deployment | Yes (Phase 7) | Render provides HTTPS |
| README with local run instructions | Yes (Phase 6) | — |
| Exact JSON field names | **Missing** | Defined below |
| Duplicate-guess behaviour | **Ambiguous** (spec: "ignored or rejected") | Decided below |
| Case of letters, whitespace | **Missing** | Decided below |
| Missing difficulty | **Missing** | Decided below |
| Thread safety of in-memory store | **Missing** | Lock around the dict |
| Gunicorn worker count | **Missing** | 1 worker (in-memory state) |

## Design Decisions

**JSON game state** (returned by all three endpoints):

```json
{
  "game_id": "3f2c9e0a...",           // uuid4 hex, 32 chars
  "difficulty": "medium",
  "pattern": "_ e _ _ e",             // lowercase letters / "_" separated by single spaces
  "guessed_letters": ["e", "x"],      // every accepted guess, in the order guessed
  "incorrect_letters": ["x"],         // accepted guesses not in the word, in order
  "remaining_guesses": 5,             // 6 - len(incorrect_letters)
  "max_incorrect": 6,
  "status": "playing"                 // "playing" | "won" | "lost"
}
```

`"word"` is added **only** when `status` is `"won"` or `"lost"`. While
`playing` the key is absent (not `null`).

**HTTP status codes:**

| Situation | Code |
|---|---|
| Game created | 201 |
| Get state / accepted guess | 200 |
| Body missing, not JSON, or not a JSON object | 400 |
| `difficulty` missing or not one of easy/medium/hard | 400 |
| `letter` missing, not a string, empty, more than one char, or not a–z | 400 |
| Duplicate guess (letter already guessed) | 409 |
| Guess after the game is over | 409 |
| Unknown game ID | 404 |
| Unknown `/api/...` route | 404 (JSON) |
| Wrong HTTP method | 405 (JSON) |

All errors use the body `{"error": "<human-readable message>"}`.

**Other rules:**
- Letters are case-insensitive: `"E"` is accepted and stored as `"e"`.
- Surrounding whitespace is **not** stripped: `" e"` is rejected (400).
  Clients send exactly one letter.
- Duplicate guesses are **rejected** (409), never counted as incorrect and
  never change state (matches the spec's scoring section, which says
  duplicates "are rejected" and "do not change game state").
- Rejected guesses (400 or 409) never change game state.
- `difficulty` is required (no default) so mistakes are visible.
- Game IDs are `uuid.uuid4().hex`.
- Games are stored in a module-level dict guarded by a `threading.Lock`.
  No persistence and no eviction (documented as a known limitation).
- Production runs gunicorn with **1 worker**, because each worker process
  would have its own separate in-memory dict.
- The hangman drawing has 6 parts in this order: head, body, left arm,
  right arm, left leg, right leg.

---

## Phase 1 — Game Engine

### Tasks

- [x] Create `game.py` with a `HangmanGame` class.
- [x] Store the hidden word internally.
- [x] Track guessed letters and incorrect letters.
- [x] Allow a maximum of 6 incorrect guesses.
- [x] Validate that a guess is exactly one letter `a`–`z` (case-insensitive).
- [x] Detect and reject duplicate guesses.
- [x] Reject guesses after the game has ended.
- [x] Rejected guesses do not change game state.
- [x] Produce the masked pattern (e.g. `_ e _ _ e`).
- [x] Detect win and loss; status values `playing`, `won`, `lost`.
- [x] Provide a client-safe `to_dict()` that includes `word` only after the game ends.
- [x] No Flask or UI imports in `game.py`.
- [x] Unit tests in `tests/test_game.py`.

### Completion Criteria

The engine can be tested entirely without a web server, and all core rules
are covered by unit tests.

---

## Phase 2 — Word Management

### Tasks

- [x] Create `words/easy.txt`, `words/medium.txt`, `words/hard.txt`.
- [x] Create `words.py` that loads all three lists.
- [x] Strip whitespace, lowercase, drop non-alphabetic lines and duplicates.
- [x] Resolve paths relative to the module file (works from any working directory).
- [x] Provide `random_word(difficulty)`.
- [x] Raise a clear error for an invalid difficulty.
- [x] Tests in `tests/test_words.py`.

### Completion Criteria

A random word can be requested reliably from each difficulty; invalid
difficulties are rejected cleanly.

---

## Phase 3 — Flask Server + REST API

### Tasks

- [x] Create `server.py` using Flask.
- [x] In-memory storage for active games, keyed by unique IDs.
- [x] `POST /api/games` — create a game.
- [x] `GET /api/games/{game_id}` — get current state.
- [x] `POST /api/games/{game_id}/guess` — submit a guess.
- [x] Validate difficulty and guess input.
- [x] JSON responses everywhere, including errors.
- [x] Correct HTTP status codes.
- [x] Handle unknown game IDs and malformed requests.
- [x] Never leak the hidden word while a game is in progress.
- [x] Serve the browser client at `/`.
- [x] API tests in `tests/test_api.py`.

### Completion Criteria

A complete game can be played using only `curl`.

---

## Phase 4 — Browser Client

### Tasks

- [x] `static/index.html`, `static/style.css`, `static/app.js`.
- [x] Difficulty selector and New Game button.
- [x] Display masked word, guessed letters, incorrect letters, remaining guesses.
- [x] On-screen A–Z keyboard; guessed letters are disabled.
- [x] Physical keyboard input.
- [x] Graphical hangman that updates after each incorrect guess.
- [x] Win/loss message.
- [x] New game without reloading the page.
- [x] Uses `fetch()` only; no game logic or hidden word in JavaScript.
- [x] Usable on desktop and mobile widths.

### Completion Criteria

A human can play a full server-hosted game in a browser. No hidden word is
stored in browser-side JavaScript during play.

---

## Phase 5 — Testing and Debugging

### Tasks

- [x] Audit engine, word, and API tests against the full checklist.
- [x] End-to-end browser test (or a written manual checklist).
- [x] Fix any bugs found while playing; add regression tests.

### Completion Criteria

Major user flows and failure cases are covered by automated tests, and the
full suite passes.

---

## Phase 6 — Documentation + Deployment Config

### Tasks

- [ ] `requirements.txt` with pinned versions.
- [ ] `render.yaml` for a Render web service.
- [ ] `.gitignore`.
- [ ] Debug mode off in production; no secrets committed.
- [ ] `README.md`: overview, structure, local setup, tests, API reference, deployment, known limitations.
- [ ] Verify a fresh install from the README instructions.

### Completion Criteria

A new user can clone, install, run, and test the project using only the README.

---

## Phase 7 — Cloud Deployment and Live Verification

### Tasks

- [ ] Push the repository to GitHub.
- [ ] Deploy to Render.
- [ ] Verify the public HTTPS URL loads and a full game can be played.
- [ ] Run a smoke test against the live URL.
- [ ] Add the live URL to the README.

### Completion Criteria

The game is publicly playable over HTTPS.

---

# Out of Scope for This Assignment

The following phases from the original TODO are part of the full project
specification but are **not** required for this assignment. They are kept
here for reference and are intentionally not implemented.

## Human Terminal Client (out of scope)

- [ ] Create `terminal_client.py`.
- [ ] Connect to the Hangman server over HTTP.
- [ ] Let the user choose Easy, Medium, or Hard.
- [ ] Display masked word, guessed/incorrect letters, remaining guesses.
- [ ] Prompt for one letter at a time and submit through the REST API.
- [ ] Display win and loss messages; allow another game.

## Reference Automated Clients (out of scope)

- [ ] Create `bot_examples/` with `random_bot.py` and `frequency_bot.py`.
- [ ] Define a common bot interaction pattern and HTTP client helper.
- [ ] Print game results and summary statistics.
- [ ] Document how students can write their own bot.

## Dictionary-Based Bot Example (out of scope)

- [ ] Implement `dictionary_bot.py` with candidate filtering by pattern.
- [ ] Choose letters by candidate-letter frequency; fall back to global frequency.
- [ ] Compare performance against the simpler bots.

## Evaluation Mode (out of scope)

- [ ] Evaluation sessions (`POST /api/evaluation/start`), unique evaluation IDs.
- [ ] 100 Easy / 100 Medium / 100 Hard server-chosen games played in sequence.
- [ ] Record wins, losses, guesses, remaining guesses, per-game results.
- [ ] Tests for evaluation integrity.

## Scoring System (out of scope)

- [ ] Official formula: Win = 100 + 10 × remaining_guesses; Loss/Abandoned = 0.
- [ ] Define effect of invalid/duplicate/abandoned games; tests for scoring.

## Leaderboard (out of scope)

- [ ] Leaderboard record format, ranking, `GET /api/leaderboard`, browser view.

## Evaluation Integrity and Anti-Cheating Safeguards (out of scope)

- [ ] Idle timeouts, repeated-invalid-guess abandonment, rate limiting.
- [ ] Evaluation action log; separate hidden evaluation word lists.

## Logging and Replay (out of scope)

- [ ] Game-log format; `GET /api/games/{id}/log` and `/replay`.
- [ ] Evaluation logs and replays; `replay.py` utility.

## Optional Future Phases (out of scope)

- [ ] Persistent storage (database for games, evaluations, leaderboard).
- [ ] Accounts and authentication (student accounts, API keys).
- [ ] Tournament mode.
- [ ] Advanced bot analysis (entropy, information gain, charts).
- [ ] Multiplayer (human-vs-human, custom words, spectator mode).
