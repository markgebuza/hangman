# Testing

## Running the tests

```bash
pip install -r requirements.txt
pytest                 # everything
pytest -v              # one line per test
pytest tests/test_api.py -k duplicate   # a subset
```

The browser tests in `tests/test_e2e.py` use Playwright and headless
Chromium. If Playwright is not installed they are **skipped** (the rest of
the suite still runs). To enable them:

```bash
pip install playwright
python -m playwright install chromium
pytest tests/test_e2e.py -v
```

## What is covered

| Checklist item | Where |
|---|---|
| Start games at all three difficulties | `test_api.py::test_start_game_each_difficulty_real_words`, `test_words.py::test_random_word_comes_from_correct_list` |
| Correct guess | `test_game.py::test_correct_guess_reveals_all_positions`, `test_api.py::test_correct_guess_200` |
| Incorrect guess | `test_game.py::test_incorrect_guess_costs_one_life`, `test_api.py::test_incorrect_guess_200` |
| Repeated (duplicate) guess → 409, state unchanged | `test_game.py::test_duplicate_guess_rejected_without_state_change`, `test_api.py::test_duplicate_guess_409_and_state_unchanged` |
| Invalid guesses: digits, `""`, `"ab"`, symbols, non-strings | `test_game.py::test_invalid_guess_rejected_without_state_change`, `test_api.py::test_invalid_letter_400` |
| Missing field / non-JSON body | `test_api.py::test_missing_letter_field_400`, `test_guess_bad_body_400`, `test_create_game_bad_body_400` |
| Winning | `test_game.py::test_win*`, `test_api.py::test_full_winning_game_hides_word_until_end`, `test_e2e.py::test_win_shows_message_and_locks_keyboard` |
| Losing | `test_game.py::test_loss_after_six_incorrect_guesses`, `test_api.py::test_full_losing_game_hides_word_until_end`, `test_e2e.py::test_loss_draws_all_six_parts` |
| Guessing after game over → 409 | `test_game.py::test_no_guesses_after_game_ends`, `test_api.py::test_guess_after_win_409`, `test_guess_after_loss_409` |
| New game after one ends | `test_api.py::test_new_game_after_previous_game_ends`, `test_e2e.py::test_new_game_without_reload` |
| Unknown game ID → 404 | `test_api.py::test_get_unknown_game_404`, `test_guess_unknown_game_404` |
| Invalid difficulty → 400 | `test_api.py::test_create_game_invalid_difficulty_400`, `test_words.py::test_invalid_difficulty_raises_clear_error` |
| Hidden word absent from every response while playing | `test_api.py::test_word_never_present_while_playing_real_words` (15 full random games, every POST and GET checked), `test_api.py::test_full_*_game_hides_word_until_end`, `test_e2e.py::test_hidden_word_not_in_browser_while_playing` |
| Two simultaneous games don't interfere | `test_api.py::test_two_simultaneous_games_do_not_interfere`, `test_concurrent_duplicate_guesses_accepted_once` |
| Engine has no Flask/UI imports | `test_game.py::test_engine_has_no_flask_or_ui_imports` |
| Word lists load from any working directory | `test_words.py::test_loading_works_from_another_working_directory` |
| Browser: click letters, page updates, drawing updates | `test_e2e.py::test_start_game_click_letters_and_page_updates` |
| Browser: physical keyboard, ignored after game over | `test_e2e.py::test_physical_keyboard_and_ignored_after_game_over` |
| Browser: server errors shown in UI | `test_e2e.py::test_server_error_message_shown_in_ui` |
| Browser: layout at phone widths | `test_e2e.py::test_long_pattern_stays_on_one_line`, `test_phone_width_has_no_horizontal_scroll` |

Deployed site: `python smoke_test.py https://<your-app>.onrender.com`. The script itself is kept working by `tests/test_smoke.py`, which runs it against a local server.
(see README).

## Manual browser checklist

Use this before the demo, or if the Playwright tests can't run on your
machine. Open the app (`http://127.0.0.1:5000/` locally, or the Render URL).

- [ ] Page loads with a masked word (`_ _ _ …`), 6 remaining guesses, empty
      gallows, and 26 enabled letter buttons.
- [ ] Click a letter that is in the word → it appears in the pattern, the
      key turns green and is disabled, remaining guesses unchanged.
- [ ] Click a letter that is not in the word → key turns red, it is listed
      under "Incorrect letters", remaining guesses drops by 1, one more body
      part appears (head → body → left arm → right arm → left leg → right leg).
- [ ] Type a letter on the physical keyboard → same behaviour as clicking.
- [ ] Type an already-guessed letter → nothing happens (no error, no
      request in DevTools).
- [ ] Win a game → green "You won! The word was …" message; all keys disabled.
- [ ] Lose a game → all 6 parts drawn, red "You lost. The word was …"; all
      keys disabled; typing letters does nothing.
- [ ] Change difficulty to Hard and click New Game → new longer pattern,
      drawing cleared, keys re-enabled, **no page reload** (DevTools
      Network shows only a `POST /api/games`, not a document request).
- [ ] Refresh the page in the middle of a game → the same game comes back.
- [ ] DevTools → Network: every `/api/...` response while `status` is
      `"playing"` has **no** `word` field.
- [ ] DevTools → Device toolbar at 375px wide (iPhone) → no horizontal
      scrolling, the pattern stays on one line on Hard, keys are easy to tap.
- [ ] Stop the server and click a letter → an error message appears
      ("Could not reach the server…") instead of nothing happening.
