"""Hangman game engine.

This module contains all Hangman rules. It has no dependency on Flask or on
any user interface, so it can be unit-tested on its own and reused by any
front end (the Flask API in ``server.py`` is just one client of it).
"""

import string

MAX_INCORRECT = 6

STATUS_PLAYING = "playing"
STATUS_WON = "won"
STATUS_LOST = "lost"

_ALPHABET = frozenset(string.ascii_lowercase)


class GuessError(Exception):
    """Base class for every rejected guess. A rejected guess never changes state."""


class InvalidGuessError(GuessError):
    """The guess is not exactly one letter a-z."""


class DuplicateGuessError(GuessError):
    """The letter has already been guessed in this game."""


class GameOverError(GuessError):
    """The game has already been won or lost."""


class HangmanGame:
    """State and rules for a single game of Hangman."""

    def __init__(self, word, max_incorrect=MAX_INCORRECT, game_id=None, difficulty=None):
        if not isinstance(word, str):
            raise ValueError("word must be a string")
        word = word.strip().lower()
        if not word or not set(word) <= _ALPHABET:
            raise ValueError("word must be a non-empty string of letters a-z")
        if max_incorrect < 1:
            raise ValueError("max_incorrect must be at least 1")

        self._word = word
        self.max_incorrect = max_incorrect
        self.game_id = game_id
        self.difficulty = difficulty
        self.guessed_letters = []      # every accepted guess, in order
        self.incorrect_letters = []    # accepted guesses not in the word, in order

    # ------------------------------------------------------------------ state

    @property
    def remaining_guesses(self):
        return self.max_incorrect - len(self.incorrect_letters)

    @property
    def status(self):
        if set(self._word) <= set(self.guessed_letters):
            return STATUS_WON
        if self.remaining_guesses <= 0:
            return STATUS_LOST
        return STATUS_PLAYING

    @property
    def is_over(self):
        return self.status != STATUS_PLAYING

    @property
    def pattern(self):
        """Masked word, e.g. ``"_ e _ _ e"``."""
        guessed = set(self.guessed_letters)
        return " ".join(ch if ch in guessed else "_" for ch in self._word)

    @property
    def word(self):
        """The hidden word, available only once the game is over."""
        if not self.is_over:
            raise GameOverError("the word is hidden until the game ends")
        return self._word

    # ---------------------------------------------------------------- actions

    @staticmethod
    def normalize_letter(letter):
        """Validate a raw guess and return it lowercased.

        Raises InvalidGuessError unless ``letter`` is a single character a-z
        (either case). Whitespace is not stripped.
        """
        if not isinstance(letter, str):
            raise InvalidGuessError("guess must be a string containing one letter")
        if len(letter) != 1:
            raise InvalidGuessError("guess must be exactly one letter")
        lowered = letter.lower()
        if lowered not in _ALPHABET:
            raise InvalidGuessError("guess must be a letter from a to z")
        return lowered

    def guess(self, letter):
        """Apply a guess. Returns True if the letter is in the word.

        Raises a GuessError subclass (and leaves state untouched) if the
        guess is invalid, a duplicate, or the game is already over.
        """
        if self.is_over:
            raise GameOverError("the game is already over")
        letter = self.normalize_letter(letter)
        if letter in self.guessed_letters:
            raise DuplicateGuessError(f"letter '{letter}' has already been guessed")

        self.guessed_letters.append(letter)
        correct = letter in self._word
        if not correct:
            self.incorrect_letters.append(letter)
        return correct

    # ---------------------------------------------------------- serialization

    def to_dict(self):
        """Client-safe state. ``word`` is included only after the game ends."""
        status = self.status
        data = {
            "game_id": self.game_id,
            "difficulty": self.difficulty,
            "pattern": self.pattern,
            "guessed_letters": list(self.guessed_letters),
            "incorrect_letters": list(self.incorrect_letters),
            "remaining_guesses": self.remaining_guesses,
            "max_incorrect": self.max_incorrect,
            "status": status,
        }
        if status != STATUS_PLAYING:
            data["word"] = self._word
        return data

    def __repr__(self):
        # Deliberately does not show the word, so it can't leak via logs.
        return (f"HangmanGame(game_id={self.game_id!r}, pattern={self.pattern!r}, "
                f"status={self.status!r})")
