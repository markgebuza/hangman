"""Word-list loading and random word selection.

Word files live in ``words/`` next to this module. Paths are resolved
relative to this file (not the current working directory) so the server
works no matter which directory it is started from.
"""

import random
from pathlib import Path

WORDS_DIR = Path(__file__).resolve().parent / "words"
DIFFICULTIES = ("easy", "medium", "hard")


class InvalidDifficultyError(ValueError):
    """Raised for a difficulty that is not one of DIFFICULTIES."""


def normalize_difficulty(difficulty):
    """Return the canonical difficulty name or raise InvalidDifficultyError.

    Matching is case-insensitive ("Easy" -> "easy"); surrounding whitespace
    is not accepted.
    """
    if isinstance(difficulty, str) and difficulty.lower() in DIFFICULTIES:
        return difficulty.lower()
    raise InvalidDifficultyError(
        f"invalid difficulty {difficulty!r}; expected one of: {', '.join(DIFFICULTIES)}"
    )


def load_word_file(path):
    """Read one word file and return a clean list of words.

    Each line is stripped and lowercased. Blank lines, lines that are not
    purely a-z letters, and duplicates are dropped. Order is preserved.
    """
    words = []
    seen = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            word = line.strip().lower()
            if not word or not (word.isascii() and word.isalpha()):
                continue
            if word in seen:
                continue
            seen.add(word)
            words.append(word)
    return words


class WordManager:
    """Loads the three word lists once and hands out random words."""

    def __init__(self, words_dir=WORDS_DIR, rng=None):
        self.words_dir = Path(words_dir)
        self._rng = rng or random.SystemRandom()
        self._lists = {}
        for difficulty in DIFFICULTIES:
            path = self.words_dir / f"{difficulty}.txt"
            words = load_word_file(path)
            if not words:
                raise ValueError(f"word list {path} contains no valid words")
            self._lists[difficulty] = words

    def words(self, difficulty):
        """Return a copy of the cleaned list for a difficulty."""
        return list(self._lists[normalize_difficulty(difficulty)])

    def random_word(self, difficulty):
        return self._rng.choice(self._lists[normalize_difficulty(difficulty)])


_default_manager = None


def get_manager():
    """Lazily create the shared WordManager for the default words/ directory."""
    global _default_manager
    if _default_manager is None:
        _default_manager = WordManager()
    return _default_manager


def random_word(difficulty):
    """Return a random word for ``difficulty`` ("easy", "medium", or "hard")."""
    return get_manager().random_word(difficulty)
