"""REST API tests using Flask's test client."""

import random
import threading

import pytest

import words
from server import create_app

WORD = "eagle"  # letters: e a g l


@pytest.fixture
def app():
    return create_app(word_source=lambda difficulty: WORD)


@pytest.fixture
def client(app):
    return app.test_client()


def new_game(client, difficulty="medium"):
    r = client.post("/api/games", json={"difficulty": difficulty})
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def guess(client, game_id, letter):
    return client.post(f"/api/games/{game_id}/guess", json={"letter": letter})


def assert_no_word(body):
    assert "word" not in body
    assert WORD not in str(body).lower()


# ------------------------------------------------------------ create

def test_create_game_returns_201_and_state(client):
    r = client.post("/api/games", json={"difficulty": "medium"})
    assert r.status_code == 201
    assert r.is_json
    body = r.get_json()
    assert set(body) == {"game_id", "difficulty", "pattern", "guessed_letters",
                         "incorrect_letters", "remaining_guesses", "max_incorrect",
                         "status"}
    assert len(body["game_id"]) == 32
    assert body["difficulty"] == "medium"
    assert body["pattern"] == "_ _ _ _ _"
    assert body["guessed_letters"] == []
    assert body["incorrect_letters"] == []
    assert body["remaining_guesses"] == 6
    assert body["status"] == "playing"
    assert_no_word(body)


def test_game_ids_are_unique(client):
    ids = {new_game(client)["game_id"] for _ in range(20)}
    assert len(ids) == 20


@pytest.mark.parametrize("body", [{}, {"difficulty": "expert"}, {"difficulty": ""},
                                  {"difficulty": None}, {"difficulty": 2}])
def test_create_game_invalid_difficulty_400(client, body):
    r = client.post("/api/games", json=body)
    assert r.status_code == 400
    assert "error" in r.get_json()


@pytest.mark.parametrize("data", ["not json", "", "[1,2]", '"easy"', "{bad json"])
def test_create_game_bad_body_400(client, data):
    r = client.post("/api/games", data=data, content_type="application/json")
    assert r.status_code == 400
    assert "error" in r.get_json()


# ------------------------------------------------------------ get

def test_get_game_200(client):
    g = new_game(client)
    r = client.get(f"/api/games/{g['game_id']}")
    assert r.status_code == 200
    assert r.get_json() == g


def test_get_unknown_game_404(client):
    r = client.get("/api/games/doesnotexist")
    assert r.status_code == 404
    assert "error" in r.get_json()


# ------------------------------------------------------------ guess

def test_correct_guess_200(client):
    g = new_game(client)
    r = guess(client, g["game_id"], "e")
    assert r.status_code == 200
    body = r.get_json()
    assert body["pattern"] == "e _ _ _ e"
    assert body["guessed_letters"] == ["e"]
    assert body["incorrect_letters"] == []
    assert body["remaining_guesses"] == 6
    assert body["status"] == "playing"
    assert_no_word(body)


def test_incorrect_guess_200(client):
    g = new_game(client)
    body = guess(client, g["game_id"], "z").get_json()
    assert body["incorrect_letters"] == ["z"]
    assert body["remaining_guesses"] == 5


def test_uppercase_guess_accepted(client):
    g = new_game(client)
    r = guess(client, g["game_id"], "E")
    assert r.status_code == 200
    assert r.get_json()["guessed_letters"] == ["e"]


@pytest.mark.parametrize("letter", ["", "ab", "1", "!", " ", None, 5, ["e"]])
def test_invalid_letter_400(client, letter):
    g = new_game(client)
    r = guess(client, g["game_id"], letter)
    assert r.status_code == 400
    assert "error" in r.get_json()
    # state unchanged
    assert client.get(f"/api/games/{g['game_id']}").get_json() == g


def test_missing_letter_field_400(client):
    g = new_game(client)
    r = client.post(f"/api/games/{g['game_id']}/guess", json={"guess": "e"})
    assert r.status_code == 400
    assert "letter" in r.get_json()["error"]


@pytest.mark.parametrize("data", ["e", "", "{", "[]"])
def test_guess_bad_body_400(client, data):
    g = new_game(client)
    r = client.post(f"/api/games/{g['game_id']}/guess", data=data,
                    content_type="application/json")
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_duplicate_guess_409_and_state_unchanged(client):
    g = new_game(client)
    first = guess(client, g["game_id"], "z").get_json()
    r = guess(client, g["game_id"], "Z")
    assert r.status_code == 409
    assert "already" in r.get_json()["error"]
    assert client.get(f"/api/games/{g['game_id']}").get_json() == first


def test_guess_unknown_game_404(client):
    r = guess(client, "nope", "e")
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_guess_after_win_409(client):
    g = new_game(client)
    for ch in "eagl":
        guess(client, g["game_id"], ch)
    r = guess(client, g["game_id"], "z")
    assert r.status_code == 409
    assert "over" in r.get_json()["error"]


def test_guess_after_loss_409(client):
    g = new_game(client)
    for ch in "qxzjvk":
        guess(client, g["game_id"], ch)
    r = guess(client, g["game_id"], "e")
    assert r.status_code == 409


# ------------------------------------------------------------ full games

def test_full_winning_game_hides_word_until_end(client):
    g = new_game(client)
    gid = g["game_id"]
    assert_no_word(g)
    for ch in "zeag":
        body = guess(client, gid, ch).get_json()
        assert body["status"] == "playing"
        assert_no_word(body)
        assert_no_word(client.get(f"/api/games/{gid}").get_json())
    final = guess(client, gid, "l").get_json()
    assert final["status"] == "won"
    assert final["word"] == WORD
    assert final["pattern"] == "e a g l e"
    assert final["remaining_guesses"] == 5
    assert client.get(f"/api/games/{gid}").get_json()["word"] == WORD


def test_full_losing_game_hides_word_until_end(client):
    g = new_game(client)
    gid = g["game_id"]
    for ch in "eqxzjv":
        body = guess(client, gid, ch).get_json()
        assert body["status"] == "playing"
        assert_no_word(body)
    final = guess(client, gid, "k").get_json()
    assert final["status"] == "lost"
    assert final["remaining_guesses"] == 0
    assert final["word"] == WORD


# ------------------------------------------------------------ misc HTTP

def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"<html" in r.data.lower()


def test_unknown_api_route_json_404(client):
    r = client.get("/api/nothing")
    assert r.status_code == 404
    assert "error" in r.get_json()


def test_wrong_method_json_405(client):
    r = client.delete("/api/games")
    assert r.status_code == 405
    assert "error" in r.get_json()


def test_api_responses_not_cached(client):
    g = new_game(client)
    r = client.get(f"/api/games/{g['game_id']}")
    assert r.headers["Cache-Control"] == "no-store"


def test_healthz(client):
    assert client.get("/healthz").get_json() == {"status": "ok"}


# ------------------------------------------------------------ audit additions (Step 8)

@pytest.fixture
def real_client():
    """App using the real word lists (random words)."""
    return create_app().test_client()


def assert_word_hidden(body, word=None):
    assert "word" not in body
    if word is not None:
        assert word not in body.values()


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_start_game_each_difficulty_real_words(real_client, difficulty):
    lengths = {len(w) for w in words.WordManager().words(difficulty)}
    r = real_client.post("/api/games", json={"difficulty": difficulty})
    assert r.status_code == 201
    body = r.get_json()
    assert body["difficulty"] == difficulty
    letters = body["pattern"].split(" ")
    assert set(letters) == {"_"}
    assert len(letters) in lengths
    assert_word_hidden(body)


def test_difficulty_is_case_insensitive(client):
    r = client.post("/api/games", json={"difficulty": "HARD"})
    assert r.status_code == 201
    assert r.get_json()["difficulty"] == "hard"


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
@pytest.mark.parametrize("seed", range(5))
def test_word_never_present_while_playing_real_words(real_client, difficulty, seed):
    """Play full random games; check every POST and GET response."""
    rng = random.Random(seed)
    alphabet = list("abcdefghijklmnopqrstuvwxyz")
    rng.shuffle(alphabet)
    g = real_client.post("/api/games", json={"difficulty": difficulty}).get_json()
    gid = g["game_id"]
    assert_word_hidden(g)
    body = g
    for letter in alphabet:
        body = real_client.post(f"/api/games/{gid}/guess", json={"letter": letter}).get_json()
        state = real_client.get(f"/api/games/{gid}").get_json()
        assert state == body
        if body["status"] == "playing":
            assert_word_hidden(body)
        else:
            break
    assert body["status"] in ("won", "lost")
    word = body["word"]
    assert len(word) == len(body["pattern"].split(" "))
    assert word in words.WordManager().words(difficulty)
    if body["status"] == "won":
        assert body["pattern"] == " ".join(word)


def test_new_game_after_previous_game_ends(client):
    g1 = new_game(client)
    for ch in "eagl":
        guess(client, g1["game_id"], ch)
    assert client.get(f"/api/games/{g1['game_id']}").get_json()["status"] == "won"

    g2 = new_game(client, "easy")
    assert g2["game_id"] != g1["game_id"]
    assert g2["status"] == "playing"
    assert g2["guessed_letters"] == []
    assert g2["remaining_guesses"] == 6
    r = guess(client, g2["game_id"], "e")
    assert r.status_code == 200
    # the old game is still finished and still reveals its word
    old = client.get(f"/api/games/{g1['game_id']}").get_json()
    assert old["status"] == "won" and old["word"] == WORD


def test_two_simultaneous_games_do_not_interfere(client):
    a = new_game(client)["game_id"]
    b = new_game(client)["game_id"]
    guess(client, a, "e")
    guess(client, b, "z")
    guess(client, a, "x")
    sa = client.get(f"/api/games/{a}").get_json()
    sb = client.get(f"/api/games/{b}").get_json()
    assert sa["guessed_letters"] == ["e", "x"]
    assert sa["incorrect_letters"] == ["x"]
    assert sa["pattern"] == "e _ _ _ e"
    assert sb["guessed_letters"] == ["z"]
    assert sb["incorrect_letters"] == ["z"]
    assert sb["pattern"] == "_ _ _ _ _"
    # finishing one game leaves the other playing
    for ch in "agl":
        guess(client, a, ch)
    assert client.get(f"/api/games/{a}").get_json()["status"] == "won"
    sb2 = client.get(f"/api/games/{b}").get_json()
    assert sb2 == sb
    # a guess "e" is still allowed in game b even though it was used in a
    assert guess(client, b, "e").status_code == 200


def test_concurrent_duplicate_guesses_accepted_once(app):
    """The store lock must stop a letter being accepted twice in a race."""
    gid = app.test_client().post("/api/games", json={"difficulty": "easy"}).get_json()["game_id"]
    codes = []
    barrier = threading.Barrier(12)

    def worker():
        c = app.test_client()
        barrier.wait()
        codes.append(c.post(f"/api/games/{gid}/guess", json={"letter": "z"}).status_code)

    threads = [threading.Thread(target=worker) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(codes) == [200] + [409] * 11
    state = app.test_client().get(f"/api/games/{gid}").get_json()
    assert state["incorrect_letters"] == ["z"]
    assert state["remaining_guesses"] == 5


def test_error_responses_are_json_with_error_key(client):
    g = new_game(client)
    responses = [
        client.post("/api/games", data="x"),
        client.post("/api/games", json={"difficulty": "x"}),
        client.get("/api/games/nope"),
        guess(client, "nope", "a"),
        guess(client, g["game_id"], "12"),
        client.put("/api/games"),
        client.get("/api/unknown"),
    ]
    for r in responses:
        assert r.status_code >= 400
        assert r.is_json
        assert set(r.get_json()) == {"error"}
        assert r.get_json()["error"]


def test_oversized_body_rejected(client):
    r = client.post("/api/games", data="{" + " " * 20000 + "}",
                    content_type="application/json")
    assert r.status_code == 413
    assert "error" in r.get_json()
