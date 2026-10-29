"""Tests for word loading and selection."""

import os
import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

import words
from words import (
    DIFFICULTIES,
    InvalidDifficultyError,
    WordManager,
    load_word_file,
    normalize_difficulty,
    random_word,
)

ROOT = Path(__file__).resolve().parent.parent
LENGTHS = {"easy": (4, 7), "medium": (5, 9), "hard": (8, 12)}


# ------------------------------------------------------------ shipped lists

@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_shipped_word_files_are_clean(difficulty):
    raw = (ROOT / "words" / f"{difficulty}.txt").read_text(encoding="utf-8").split("\n")
    lines = [l for l in raw if l]
    assert len(lines) >= 150
    assert len(lines) == len(set(lines)), "duplicate words in file"
    lo, hi = LENGTHS[difficulty]
    for w in lines:
        assert re.fullmatch(r"[a-z]+", w), w
        assert lo <= len(w) <= hi, w


def test_shipped_lists_do_not_overlap():
    sets = {d: set(WordManager().words(d)) for d in DIFFICULTIES}
    assert not sets["easy"] & sets["medium"]
    assert not sets["easy"] & sets["hard"]
    assert not sets["medium"] & sets["hard"]


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_random_word_comes_from_correct_list(difficulty):
    allowed = set(WordManager().words(difficulty))
    for _ in range(50):
        assert random_word(difficulty) in allowed


def test_random_word_varies():
    assert len({random_word("medium") for _ in range(50)}) > 1


def test_random_word_is_case_insensitive_on_difficulty():
    assert random_word("EASY") in WordManager().words("easy")


# ------------------------------------------------------------ invalid input

@pytest.mark.parametrize("bad", ["", "expert", " easy", "easy ", None, 1, ["easy"]])
def test_invalid_difficulty_raises_clear_error(bad):
    with pytest.raises(InvalidDifficultyError) as exc:
        random_word(bad)
    assert "easy, medium, hard" in str(exc.value)


def test_invalid_difficulty_is_a_value_error():
    assert issubclass(InvalidDifficultyError, ValueError)


def test_normalize_difficulty():
    assert normalize_difficulty("Hard") == "hard"


# ------------------------------------------------------------ cleaning

def test_load_word_file_cleans_input(tmp_path):
    f = tmp_path / "w.txt"
    f.write_text("  Apple \n\nbanana\nAPPLE\nhello world\nabc123\nno-dash\ncafé\ncherry\n", encoding="utf-8")
    assert load_word_file(f) == ["apple", "banana", "cherry"]


def _write_lists(d, easy="cat\n", medium="horse\n", hard="elephant\n"):
    (d / "easy.txt").write_text(easy, encoding="utf-8")
    (d / "medium.txt").write_text(medium, encoding="utf-8")
    (d / "hard.txt").write_text(hard, encoding="utf-8")


def test_manager_with_custom_directory(tmp_path):
    _write_lists(tmp_path, easy="Dog\ndog\n  \n")
    m = WordManager(tmp_path, rng=random.Random(0))
    assert m.words("easy") == ["dog"]
    assert m.random_word("easy") == "dog"


def test_manager_rejects_empty_list(tmp_path):
    _write_lists(tmp_path, hard="123\n\n")
    with pytest.raises(ValueError, match="no valid words"):
        WordManager(tmp_path)


def test_manager_missing_file(tmp_path):
    (tmp_path / "easy.txt").write_text("cat\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        WordManager(tmp_path)


# ------------------------------------------------------------ cwd independence

def test_words_dir_is_absolute_and_next_to_module():
    assert words.WORDS_DIR.is_absolute()
    assert words.WORDS_DIR == Path(words.__file__).resolve().parent / "words"


def test_loading_works_from_another_working_directory(tmp_path):
    code = "import words; print(words.random_word('hard'))"
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    out = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env,
                         capture_output=True, text=True, check=True)
    assert out.stdout.strip() in WordManager().words("hard")
