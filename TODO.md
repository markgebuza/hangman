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

## Phase 1 — Game Engine

### Tasks

- [ ] Create `game.py` with a `HangmanGame` class.
- [ ] Store the hidden word internally.
- [ ] Track guessed letters and incorrect letters.
- [ ] Allow a maximum of 6 incorrect guesses.
- [ ] Validate that a guess is exactly one letter `a`–`z` (case-insensitive).
- [ ] Detect and reject duplicate guesses.
- [ ] Reject guesses after the game has ended.
- [ ] Rejected guesses do not change game state.
- [ ] Produce the masked pattern (e.g. `_ e _ _ e`).
- [ ] Detect win and loss; status values `playing`, `won`, `lost`.
- [ ] Provide a client-safe `to_dict()` that includes `word` only after the game ends.
- [ ] No Flask or UI imports in `game.py`.
- [ ] Unit tests in `tests/test_game.py`.

### Completion Criteria

The engine can be tested entirely without a web server, and all core rules
are covered by unit tests.

---

## Phase 2 — Word Management

### Tasks

- [ ] Create `words/easy.txt`, `words/medium.txt`, `words/hard.txt`.
- [ ] Create `words.py` that loads all three lists.
- [ ] Strip whitespace, lowercase, drop non-alphabetic lines and duplicates.
- [ ] Resolve paths relative to the module file (works from any working directory).
- [ ] Provide `random_word(difficulty)`.
- [ ] Raise a clear error for an invalid difficulty.
- [ ] Tests in `tests/test_words.py`.

### Completion Criteria

A random word can be requested reliably from each difficulty; invalid
difficulties are rejected cleanly.

---

## Phase 3 — Flask Server + REST API

### Tasks

- [ ] Create `server.py` using Flask.
- [ ] In-memory storage for active games, keyed by unique IDs.
- [ ] `POST /api/games` — create a game.
- [ ] `GET /api/games/{game_id}` — get current state.
- [ ] `POST /api/games/{game_id}/guess` — submit a guess.
- [ ] Validate difficulty and guess input.
- [ ] JSON responses everywhere, including errors.
- [ ] Correct HTTP status codes.
- [ ] Handle unknown game IDs and malformed requests.
- [ ] Never leak the hidden word while a game is in progress.
- [ ] Serve the browser client at `/`.
- [ ] API tests in `tests/test_api.py`.

### Completion Criteria

A complete game can be played using only `curl`.

---

## Phase 4 — Browser Client

### Tasks

- [ ] `static/index.html`, `static/style.css`, `static/app.js`.
- [ ] Difficulty selector and New Game button.
- [ ] Display masked word, guessed letters, incorrect letters, remaining guesses.
- [ ] On-screen A–Z keyboard; guessed letters are disabled.
- [ ] Physical keyboard input.
- [ ] Graphical hangman that updates after each incorrect guess.
- [ ] Win/loss message.
- [ ] New game without reloading the page.
- [ ] Uses `fetch()` only; no game logic or hidden word in JavaScript.
- [ ] Usable on desktop and mobile widths.

### Completion Criteria

A human can play a full server-hosted game in a browser. No hidden word is
stored in browser-side JavaScript during play.

---

## Phase 5 — Testing and Debugging

### Tasks

- [ ] Audit engine, word, and API tests against the full checklist.
- [ ] End-to-end browser test (or a written manual checklist).
- [ ] Fix any bugs found while playing; add regression tests.

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
