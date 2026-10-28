"""Unit tests for the game engine (no Flask, no server)."""

import ast
import pathlib

import pytest

from game import (
    MAX_INCORRECT,
    DuplicateGuessError,
    GameOverError,
    GuessError,
    HangmanGame,
    InvalidGuessError,
)


def snapshot(game):
    return (list(game.guessed_letters), list(game.incorrect_letters),
            game.remaining_guesses, game.status, game.pattern)


def lose(game, letters="qxzjvk"):
    for ch in letters:
        if game.is_over:
            break
        game.guess(ch)


# ---------------------------------------------------------------- new game

def test_new_game_initial_state():
    g = HangmanGame("eagle")
    assert g.status == "playing"
    assert g.pattern == "_ _ _ _ _"
    assert g.guessed_letters == []
    assert g.incorrect_letters == []
    assert g.remaining_guesses == MAX_INCORRECT == 6


def test_word_is_normalized_to_lowercase():
    g = HangmanGame("  Eagle ")
    g.guess("e")
    assert g.pattern == "e _ _ _ e"


@pytest.mark.parametrize("bad", ["", "ab1", "two words", None, 5])
def test_invalid_word_rejected(bad):
    with pytest.raises(ValueError):
        HangmanGame(bad)


# ---------------------------------------------------------------- guessing

def test_correct_guess_reveals_all_positions():
    g = HangmanGame("eagle")
    assert g.guess("e") is True
    assert g.pattern == "e _ _ _ e"
    assert g.guessed_letters == ["e"]
    assert g.incorrect_letters == []
    assert g.remaining_guesses == 6


def test_incorrect_guess_costs_one_life():
    g = HangmanGame("eagle")
    assert g.guess("z") is False
    assert g.pattern == "_ _ _ _ _"
    assert g.guessed_letters == ["z"]
    assert g.incorrect_letters == ["z"]
    assert g.remaining_guesses == 5
    assert g.status == "playing"


def test_uppercase_guess_is_accepted_and_lowercased():
    g = HangmanGame("eagle")
    assert g.guess("E") is True
    assert g.guessed_letters == ["e"]


def test_guessed_letters_keep_guess_order():
    g = HangmanGame("eagle")
    for ch in "zgx":
        g.guess(ch)
    assert g.guessed_letters == ["z", "g", "x"]
    assert g.incorrect_letters == ["z", "x"]


@pytest.mark.parametrize("letter", ["e", "E", "z", "Z"])
def test_duplicate_guess_rejected_without_state_change(letter):
    g = HangmanGame("eagle")
    g.guess(letter)
    before = snapshot(g)
    with pytest.raises(DuplicateGuessError):
        g.guess(letter.swapcase())  # duplicates are case-insensitive
    assert snapshot(g) == before


@pytest.mark.parametrize("bad", ["", "ab", "1", "!", " ", " e", "é", None, 3, ["e"]])
def test_invalid_guess_rejected_without_state_change(bad):
    g = HangmanGame("eagle")
    g.guess("z")
    before = snapshot(g)
    with pytest.raises(InvalidGuessError):
        g.guess(bad)
    assert snapshot(g) == before


def test_all_rejections_share_a_base_class():
    assert issubclass(InvalidGuessError, GuessError)
    assert issubclass(DuplicateGuessError, GuessError)
    assert issubclass(GameOverError, GuessError)


# ---------------------------------------------------------------- win / loss

def test_win():
    g = HangmanGame("eagle")
    for ch in "eagl":
        g.guess(ch)
    assert g.status == "won"
    assert g.pattern == "e a g l e"
    assert g.is_over


def test_win_with_some_wrong_guesses():
    g = HangmanGame("cat")
    for ch in "xyzcat":
        g.guess(ch)
    assert g.status == "won"
    assert g.remaining_guesses == 3


def test_win_on_last_life():
    g = HangmanGame("cat")
    for ch in "qweru":   # five wrong letters
        g.guess(ch)
    assert g.remaining_guesses == 1
    for ch in "cat":
        g.guess(ch)
    assert g.status == "won"
    assert g.remaining_guesses == 1


def test_loss_after_six_incorrect_guesses():
    g = HangmanGame("eagle")
    for i, ch in enumerate("qxzjvk", start=1):
        g.guess(ch)
        assert g.remaining_guesses == 6 - i
    assert g.status == "lost"
    assert g.remaining_guesses == 0


def test_five_incorrect_guesses_is_still_playing():
    g = HangmanGame("eagle")
    for ch in "qxzjv":
        g.guess(ch)
    assert g.status == "playing"
    assert g.remaining_guesses == 1


def test_custom_max_incorrect():
    g = HangmanGame("eagle", max_incorrect=2)
    g.guess("q")
    g.guess("x")
    assert g.status == "lost"


# ---------------------------------------------------------------- after end

@pytest.mark.parametrize("finish", ["win", "loss"])
@pytest.mark.parametrize("letter", ["b", "e", "ab", "1"])
def test_no_guesses_after_game_ends(finish, letter):
    g = HangmanGame("eagle")
    if finish == "win":
        for ch in "eagl":
            g.guess(ch)
    else:
        lose(g)
    before = snapshot(g)
    with pytest.raises(GameOverError):
        g.guess(letter)
    assert snapshot(g) == before


# ---------------------------------------------------------------- hiding the answer

def test_to_dict_hides_word_while_playing():
    g = HangmanGame("eagle", game_id="abc", difficulty="easy")
    d = g.to_dict()
    assert "word" not in d
    assert "eagle" not in repr(d)
    assert d == {
        "game_id": "abc",
        "difficulty": "easy",
        "pattern": "_ _ _ _ _",
        "guessed_letters": [],
        "incorrect_letters": [],
        "remaining_guesses": 6,
        "max_incorrect": 6,
        "status": "playing",
    }


def test_word_hidden_through_whole_game_until_win():
    g = HangmanGame("eagle")
    for ch in "zeagl":
        assert "word" not in g.to_dict()
        g.guess(ch)
    d = g.to_dict()
    assert d["status"] == "won"
    assert d["word"] == "eagle"


def test_word_revealed_after_loss():
    g = HangmanGame("eagle")
    lose(g)
    d = g.to_dict()
    assert d["status"] == "lost"
    assert d["word"] == "eagle"


def test_word_property_guarded_while_playing():
    g = HangmanGame("eagle")
    with pytest.raises(GameOverError):
        _ = g.word
    lose(g)
    assert g.word == "eagle"


def test_repr_does_not_leak_word():
    assert "eagle" not in repr(HangmanGame("eagle"))


def test_to_dict_returns_copies():
    g = HangmanGame("eagle")
    d = g.to_dict()
    d["guessed_letters"].append("q")
    assert g.guessed_letters == []


# ---------------------------------------------------------------- independence

def test_engine_has_no_flask_or_ui_imports():
    src = pathlib.Path(__file__).resolve().parent.parent / "game.py"
    tree = ast.parse(src.read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported <= {"string"}, imported
