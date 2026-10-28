# What happens when you click "E"

A step-by-step trace of one guess, from the click in the browser to the
updated page, with file and line references. Line numbers refer to the
files as of the commit that added this document.

Example situation: a game is in progress, the hidden word is `eagle`
(the browser does **not** know this), and nothing has been guessed yet.

```
 Browser (static/app.js)                     Server (server.py)                 Engine (game.py)
 ───────────────────────                     ──────────────────                 ────────────────
 click <button data-letter="e">
   └─ guessLetter("e")          ── POST /api/games/<id>/guess ──►  guess(game_id)
        └─ api("POST", url, {letter:"e"})     {"letter":"e"}         ├─ store.get(game_id)
                                                                      ├─ read_json_object()
                                                                      └─ game.guess("e") ───────►  HangmanGame.guess
                                                                                                     ├─ is_over? no
                                                                                                     ├─ normalize_letter
                                                                                                     ├─ duplicate? no
                                                                                                     └─ append "e"
                                                                         game.to_dict()  ◄──────────  (no "word" key)
   render(data) ◄────────────── 200 OK  application/json ────────────── jsonify(...)
     ├─ pattern, stats text
     ├─ hangman parts
     ├─ message
     └─ updateKeyboard()
```

## 1. The click (browser)

1. When the page loads, `buildKeyboard()` (`static/app.js:167`) creates 26
   `<button>`s. Each has `data-letter="e"` etc. (`static/app.js:173`) and a
   click listener that calls `guessLetter(letter)` (`static/app.js:175`).
   The button shows "E" only because CSS uppercases it; the value sent is
   lowercase `"e"`.
   - Typing `E` on the physical keyboard goes through `onKeyDown`
     (`static/app.js:195`), which lowercases the key, ignores it if the
     game isn't in progress or the letter was already guessed, and then
     calls the same `guessLetter("e")` (`static/app.js:205`).
2. `guessLetter` (`static/app.js:84`) returns early if a request is
   already in flight or the game is over (`static/app.js:85`), sets the
   `busy` flag (which disables the keyboard so you can't double-click),
   and calls `api("POST", "/api/games/<game_id>/guess", { letter: "e" })`
   (`static/app.js:88`).
3. `api()` (`static/app.js:34`) builds the request: method `POST`, header
   `Content-Type: application/json`, body `JSON.stringify({letter: "e"})`
   (`static/app.js:38`), and calls `fetch(url, options)`
   (`static/app.js:42`). The URL is relative, so the same code works on
   `localhost` and on Render.

**The HTTP request:**

```http
POST /api/games/3f2c9e0a7b1d4c5e8f90a1b2c3d4e5f6/guess HTTP/1.1
Content-Type: application/json
Accept: application/json

{"letter":"e"}
```

## 2. The route (server.py)

4. Flask matches the URL to the `guess(game_id)` view registered with
   `@app.post("/api/games/<game_id>/guess")` (`server.py:110-111`).
   `game_id` is taken from the URL.
5. `store.get(game_id)` looks the game up in the in-memory `GameStore`
   (`server.py:112`, store defined at `server.py:24-44`). Unknown ID →
   `404 {"error": "game '…' not found"}` (`server.py:114`).
6. `read_json_object()` (`server.py:70-73`) parses the body. If it isn't
   a JSON object → `400` (`server.py:117`); if the `letter` key is missing
   → `400` (`server.py:119`).
7. Holding the store lock (`server.py:121`) so two requests can't change
   the same game at once, the view calls the engine:
   `game.guess(data["letter"])` (`server.py:123`).

## 3. The engine (game.py)

8. `HangmanGame.guess("e")` (`game.py:103`):
   - game already over? → `GameOverError` (`game.py:109-110`)
   - `normalize_letter` (`game.py:88-101`) checks it's exactly one
     character a–z and lowercases it; otherwise `InvalidGuessError`.
   - already guessed? → `DuplicateGuessError` (`game.py:112-113`)
   - records the guess (`game.py:115`); `"e"` **is** in `eagle`, so it is
     not added to `incorrect_letters` (`game.py:116-118`).
   This is the **only** place in the whole project that decides whether a
   guess is right.
9. Back in the route, exceptions become HTTP errors
   (`server.py:124-127`): `InvalidGuessError` → 400,
   `DuplicateGuessError` / `GameOverError` → 409. On success the route
   returns `jsonify(game.to_dict())` with status 200 (`server.py:128`).
10. `to_dict()` (`game.py:123-138`) builds the response. `pattern`,
    `remaining_guesses` and `status` are computed properties
    (`game.py:56-76`). The `word` key is added **only** if the status is
    not `"playing"` (`game.py:136-137`) — this is how the hidden word is
    kept out of every in-progress response.
11. `no_cache_api` (`server.py:142-146`) adds `Cache-Control: no-store`
    so the browser never shows a stale cached state.

**The HTTP response:**

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-store

{"game_id":"3f2c9e0a7b1d4c5e8f90a1b2c3d4e5f6","difficulty":"medium",
 "pattern":"e _ _ _ e","guessed_letters":["e"],"incorrect_letters":[],
 "remaining_guesses":6,"max_incorrect":6,"status":"playing"}
```

(no `"word"` — the game is still being played)

## 4. Updating the page (browser)

12. In `api()`, `await response.json()` parses the body
    (`static/app.js:48`). `response.ok` is true, so the data is returned
    (`static/app.js:52-57`). For a 4xx/5xx it would throw an `ApiError`
    carrying the server's `error` text, which `guessLetter` shows in the
    message area.
13. `guessLetter` passes the data to `render(data)` (`static/app.js:89`).
14. `render` (`static/app.js:124`):
    - writes `data.pattern` into `#pattern` (`static/app.js:126`) → the
      page now shows `e _ _ _ e`;
    - fills remaining guesses, guessed letters and incorrect letters;
    - shows one SVG body part per incorrect letter by toggling the
      `shown` class (`static/app.js:132`) — still 0 here;
    - if `status` is `won`/`lost`, shows the message with `data.word`
      from the server (`static/app.js:134-138`); otherwise clears it;
    - calls `updateKeyboard()` (`static/app.js:141`, defined at `:144`),
      which disables the E key and colours it green because `"e"` is in
      `guessed_letters` but not in `incorrect_letters`.
15. `finally { setBusy(false) }` re-enables the other keys.

The JavaScript never compares the letter to the word (it never has the
word): it only displays what the server returned.

---

# DevTools demo guide (Chrome)

1. Open the app (local or Render URL). Press **F12** (Mac: **Cmd+Opt+I**)
   and choose the **Network** tab.
2. Click the **Fetch/XHR** filter so only API calls show. Optionally tick
   **Preserve log**.
3. Click **New Game**. A row `games` appears:
   - **Headers**: Request URL `…/api/games`, Request Method `POST`,
     Status Code `201 Created`.
   - **Payload**: `{"difficulty": "medium"}`.
   - **Response/Preview**: `game_id`, `pattern` of underscores,
     `remaining_guesses: 6`, `status: "playing"` — point out there is
     **no `word` field**.
4. Click the letter **E**. A row `guess` appears:
   - **Headers**: `POST …/api/games/<id>/guess`, `200 OK`,
     response header `Content-Type: application/json`.
   - **Payload**: `{"letter": "e"}`.
   - **Response/Preview**: updated `pattern`, `guessed_letters: ["e"]`,
     and still no `word`.
5. Click a letter that's wrong: show `incorrect_letters` and
   `remaining_guesses` decreasing and the drawing gaining a body part.
6. Finish the game: the last `guess` response now has `status: "won"` or
   `"lost"` **and** the `word` field — that's the first time the browser
   ever receives the word.
7. Optional: in the **Console** tab, run
   `fetch('/api/games/nope').then(r => r.json()).then(console.log)` to show
   a JSON `404` error, or click an already-guessed letter via the console
   (`fetch(location.origin + '/api/games/' + gameId + '/guess', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{"letter":"e"}'}).then(r=>r.status)`)
   to show the `409` duplicate response.
8. Point out that clicking **New Game** adds only a `games` request — no
   `document` request — proving the page didn't reload.
