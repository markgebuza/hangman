#!/usr/bin/env python3
"""Smoke test for a running Hangman server (local or deployed).

Usage:
    python smoke_test.py https://<your-app>.onrender.com
    python smoke_test.py http://127.0.0.1:5000

Uses only the Python standard library. Exits with status 0 if every check
passes, 1 otherwise. Allows up to 60 seconds per request (and up to 60 s of
retries for the first request) because free Render instances may need to
wake up from sleep.
"""

import json
import sys
import time
import urllib.error
import urllib.request

TIMEOUT = 60          # seconds per request
WAKE_UP_BUDGET = 60   # seconds of retries while the instance wakes up
LETTER_ORDER = "etaoinshrdlcumwfgypbvkjxqz"  # common letters first

results = []


def check(name, condition, detail=""):
    results.append(bool(condition))
    mark = "PASS" if condition else "FAIL"
    detail = " ".join(str(detail).split())  # one line
    if len(detail) > 200:
        detail = detail[:200] + "..."
    print(f"[{mark}] {name}" + (f"  ({detail})" if detail and not condition else ""))
    return condition


def request(base, method, path, body=None):
    """Return (status_code, parsed_json_or_text). Never raises for HTTP errors."""
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            status, raw, ctype = resp.status, resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as err:
        status, raw, ctype = err.code, err.read(), err.headers.get("Content-Type", "")
    text = raw.decode("utf-8", errors="replace")
    if "json" in ctype:
        try:
            return status, json.loads(text)
        except ValueError:
            pass
    return status, text


def wake_up(base):
    """Load '/' and retry while the free instance is starting."""
    deadline = time.monotonic() + WAKE_UP_BUDGET
    while True:
        try:
            status, body = request(base, "GET", "/")
            if status < 500 or time.monotonic() > deadline:
                return status, body
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if time.monotonic() > deadline:
                raise SystemExit(f"Could not reach {base}: {exc}")
        print("  ...waiting for the server to wake up")
        time.sleep(3)


def no_word_while_playing(state):
    return isinstance(state, dict) and (state.get("status") != "playing" or "word" not in state)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    base = sys.argv[1].rstrip("/")
    print(f"Smoke testing {base}\n")
    started = time.monotonic()

    # 1. Home page
    status, body = wake_up(base)
    check("GET / returns 200", status == 200, f"got {status}")
    check("GET / is the Hangman page", isinstance(body, str) and "Hangman" in body)

    # 2. Create games at every difficulty
    games = {}
    for difficulty in ("easy", "medium", "hard"):
        status, state = request(base, "POST", "/api/games", {"difficulty": difficulty})
        ok = check(f"POST /api/games {difficulty} -> 201", status == 201, f"got {status}: {state}")
        if ok:
            check(f"  {difficulty}: status is playing", state.get("status") == "playing")
            check(f"  {difficulty}: pattern is all underscores",
                  set(state.get("pattern", "x").split(" ")) == {"_"})
            check(f"  {difficulty}: remaining_guesses is 6", state.get("remaining_guesses") == 6)
            check(f"  {difficulty}: no 'word' while playing", "word" not in state)
            games[difficulty] = state
    if "easy" not in games:
        return summary(started)

    gid = games["easy"]["game_id"]

    # 3. Valid, invalid and duplicate guesses
    status, state = request(base, "POST", f"/api/games/{gid}/guess", {"letter": "e"})
    check("valid guess 'e' -> 200", status == 200, f"got {status}: {state}")
    check("  guess recorded", isinstance(state, dict) and "e" in state.get("guessed_letters", []))
    check("  no 'word' while playing", no_word_while_playing(state))

    for bad in ("1", "", "ab"):
        status, body = request(base, "POST", f"/api/games/{gid}/guess", {"letter": bad})
        check(f"invalid guess {bad!r} -> 400 with JSON error",
              status == 400 and isinstance(body, dict) and "error" in body, f"got {status}: {body}")
    status, body = request(base, "POST", f"/api/games/{gid}/guess", b"not json")
    check("non-JSON body -> 400", status == 400, f"got {status}")

    status, body = request(base, "POST", f"/api/games/{gid}/guess", {"letter": "e"})
    check("duplicate guess 'e' -> 409", status == 409, f"got {status}: {body}")

    status, current = request(base, "GET", f"/api/games/{gid}")
    check("GET /api/games/<id> -> 200", status == 200, f"got {status}")
    check("  state unchanged by rejected guesses", current == state, f"{current} != {state}")

    # 4. Other error cases
    status, body = request(base, "GET", "/api/games/does-not-exist")
    check("unknown game id -> 404", status == 404, f"got {status}")
    status, body = request(base, "POST", "/api/games", {"difficulty": "expert"})
    check("invalid difficulty -> 400", status == 400, f"got {status}")

    # 5. Play one game to completion
    state = current
    leaked = False
    for letter in LETTER_ORDER:
        if state.get("status") != "playing":
            break
        if letter in state.get("guessed_letters", []):
            continue
        status, state = request(base, "POST", f"/api/games/{gid}/guess", {"letter": letter})
        if status != 200 or not isinstance(state, dict):
            check(f"guess {letter!r} during play -> 200", False, f"got {status}: {state}")
            return summary(started)
        if not no_word_while_playing(state):
            leaked = True
        _, polled = request(base, "GET", f"/api/games/{gid}")
        if not no_word_while_playing(polled):
            leaked = True
    check("'word' never present in any response while playing", not leaked)
    final = state.get("status")
    check("game finished (won or lost)", final in ("won", "lost"), f"status={final}")
    check("final response reveals 'word'", isinstance(state.get("word"), str) and state["word"])
    if final == "won":
        check("  won: pattern spells the word", state["pattern"].replace(" ", "") == state["word"])
    elif final == "lost":
        check("  lost: remaining_guesses is 0", state.get("remaining_guesses") == 0)
    status, body = request(base, "POST", f"/api/games/{gid}/guess", {"letter": "q"})
    check("guess after game over -> 409", status == 409, f"got {status}")

    # 6. The other games were not affected
    for difficulty in ("medium", "hard"):
        if difficulty in games:
            status, other = request(base, "GET", f"/api/games/{games[difficulty]['game_id']}")
            check(f"{difficulty} game untouched by the easy game",
                  status == 200 and other == games[difficulty], f"got {status}: {other}")

    return summary(started)


def summary(started):
    passed = sum(results)
    failed = len(results) - passed
    print(f"\n{passed} passed, {failed} failed in {time.monotonic() - started:.1f}s")
    return 0 if failed == 0 and results else 1


if __name__ == "__main__":
    sys.exit(main())
