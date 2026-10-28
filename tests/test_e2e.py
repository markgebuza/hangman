"""End-to-end browser tests (Playwright + headless Chromium).

Skipped automatically if Playwright or its Chromium browser is not
installed, so `pytest` still runs everywhere. To enable them locally:

    pip install playwright
    python -m playwright install chromium
"""

import threading

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from werkzeug.serving import make_server  # noqa: E402

from server import create_app  # noqa: E402


class FixedWords:
    """word_source that the tests can change between games."""

    def __init__(self, word="eagle"):
        self.word = word

    def __call__(self, difficulty):
        return self.word


@pytest.fixture(scope="module")
def words():
    return FixedWords()


@pytest.fixture(scope="module")
def base_url(words):
    app = create_app(word_source=words)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:  # browser binary not installed
            pytest.skip(f"Chromium not available for Playwright: {exc}")
        yield b
        b.close()


@pytest.fixture
def page(browser, base_url, words):
    words.word = "eagle"
    context = browser.new_context(viewport={"width": 1100, "height": 800})
    pg = context.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    pg.on("console", lambda m: pg.errors.append(m.text) if m.type == "error" else None)
    yield pg
    context.close()


def wait_for_game(pg, pattern):
    pg.wait_for_function(
        "p => document.getElementById('pattern').textContent === p", arg=pattern)


# ---------------------------------------------------------------- regression (Step 7)

@pytest.mark.parametrize("width", [320, 375, 1100])
def test_long_pattern_stays_on_one_line(page, base_url, words, width):
    """Regression: 10–12 letter patterns used to wrap mid-word on phones."""
    words.word = "kaleidoscope"  # 12 letters -> 23-character pattern
    page.set_viewport_size({"width": width, "height": 800})
    page.goto(base_url + "/")
    wait_for_game(page, " ".join("_" * 12))
    metrics = page.evaluate("""() => {
        const el = document.getElementById('pattern');
        const lh = parseFloat(getComputedStyle(el).lineHeight) ||
                   parseFloat(getComputedStyle(el).fontSize) * 1.4;
        return {height: el.getBoundingClientRect().height, lineHeight: lh,
                scroll: el.scrollWidth, client: el.clientWidth,
                page: document.documentElement.scrollWidth, vw: window.innerWidth};
    }""")
    assert metrics["height"] < 1.5 * metrics["lineHeight"], metrics   # one line
    assert metrics["scroll"] <= metrics["client"], metrics            # not clipped
    assert metrics["page"] <= metrics["vw"], metrics                  # no page h-scroll


# ---------------------------------------------------------------- main flows (Step 8)

def key(pg, letter):
    return pg.locator(f"#keyboard button[data-letter='{letter}']")


def click_and_wait(pg, letter):
    with pg.expect_response(lambda r: r.url.endswith("/guess")) as info:
        key(pg, letter).click()
    return info.value


def test_start_game_click_letters_and_page_updates(page, base_url):
    page.goto(base_url + "/")
    wait_for_game(page, "_ _ _ _ _")
    assert page.text_content("#remaining") == "6"
    assert page.locator("#keyboard button").count() == 26
    assert page.locator("#gallows .part.shown").count() == 0

    resp = click_and_wait(page, "e")
    req = resp.request
    assert req.method == "POST"
    assert req.post_data_json == {"letter": "e"}
    wait_for_game(page, "e _ _ _ e")
    assert key(page, "e").is_disabled()
    assert key(page, "e").get_attribute("class").split() == ["key", "correct"]
    assert page.text_content("#guessed") == "e"

    click_and_wait(page, "z")
    page.wait_for_function("document.getElementById('remaining').textContent === '5'")
    assert page.text_content("#incorrect") == "z"
    assert page.locator("#gallows .part.shown").count() == 1
    assert key(page, "z").get_attribute("class").split() == ["key", "incorrect"]
    assert page.errors == []


def test_win_shows_message_and_locks_keyboard(page, base_url):
    page.goto(base_url + "/")
    wait_for_game(page, "_ _ _ _ _")
    for ch in "eagl":
        click_and_wait(page, ch)
    page.wait_for_function("document.getElementById('message').textContent.includes('won')")
    assert "eagle" in page.text_content("#message")
    assert page.locator("#keyboard button:enabled").count() == 0


def test_loss_draws_all_six_parts(page, base_url):
    page.goto(base_url + "/")
    wait_for_game(page, "_ _ _ _ _")
    for i, ch in enumerate("qxzjvk", start=1):
        click_and_wait(page, ch)
        page.wait_for_function(
            "n => document.querySelectorAll('#gallows .part.shown').length === n", arg=i)
    page.wait_for_function("document.getElementById('message').textContent.includes('lost')")
    assert "eagle" in page.text_content("#message")
    assert page.text_content("#remaining") == "0"


def test_physical_keyboard_and_ignored_after_game_over(page, base_url):
    page.goto(base_url + "/")
    wait_for_game(page, "_ _ _ _ _")
    with page.expect_response(lambda r: r.url.endswith("/guess")):
        page.keyboard.press("E")  # Shift+E style uppercase
    wait_for_game(page, "e _ _ _ e")
    for ch in "agl":
        with page.expect_response(lambda r: r.url.endswith("/guess")):
            page.keyboard.press(ch)
    page.wait_for_function("document.getElementById('message').textContent.includes('won')")

    sent = []
    page.on("request", lambda r: sent.append(r.url) if "/guess" in r.url else None)
    page.keyboard.press("q")
    page.wait_for_timeout(300)
    assert sent == []  # no request after the game is over


def test_new_game_without_reload(page, base_url, words):
    page.goto(base_url + "/")
    wait_for_game(page, "_ _ _ _ _")
    click_and_wait(page, "z")
    page.evaluate("window.__noReload = true")

    words.word = "kaleidoscope"
    page.select_option("#difficulty", "hard")
    with page.expect_response(lambda r: r.url.endswith("/api/games")) as info:
        page.click("#new-game")
    assert info.value.status == 201
    assert info.value.request.post_data_json == {"difficulty": "hard"}
    wait_for_game(page, " ".join("_" * 12))
    assert page.evaluate("window.__noReload") is True
    assert page.text_content("#remaining") == "6"
    assert page.locator("#gallows .part.shown").count() == 0
    assert page.locator("#keyboard button:enabled").count() == 26


def test_hidden_word_not_in_browser_while_playing(page, base_url, words):
    words.word = "zucchini"
    bodies = []
    page.on("response", lambda r: bodies.append(r.text()) if "/api/" in r.url else None)
    page.goto(base_url + "/")
    wait_for_game(page, " ".join("_" * 8))
    for ch in "zuc":
        click_and_wait(page, ch)
    assert page.evaluate("JSON.stringify(state)").find("zucchini") == -1
    assert "zucchini" not in page.content()
    assert "zucchini" not in page.evaluate("JSON.stringify(sessionStorage)")
    assert bodies and all("zucchini" not in b for b in bodies)


def test_server_error_message_shown_in_ui(page, base_url):
    page.goto(base_url + "/")
    wait_for_game(page, "_ _ _ _ _")
    # Simulate the server forgetting the game (e.g. a restart on Render).
    page.route("**/guess", lambda route: route.fulfill(
        status=404, content_type="application/json",
        body='{"error": "game not found"}'))
    key(page, "e").click()
    page.wait_for_function("document.getElementById('message').textContent.length > 0")
    assert "no longer exists" in page.text_content("#message")
    page.unroute("**/guess")
    page.route("**/api/games", lambda route: route.fulfill(
        status=500, content_type="application/json",
        body='{"error": "internal server error"}'))
    page.click("#new-game")
    page.wait_for_function(
        "document.getElementById('message').textContent.includes('internal server error')")


def test_reload_resumes_current_game(page, base_url):
    page.goto(base_url + "/")
    wait_for_game(page, "_ _ _ _ _")
    click_and_wait(page, "e")
    wait_for_game(page, "e _ _ _ e")
    page.reload()
    wait_for_game(page, "e _ _ _ e")
    assert key(page, "e").is_disabled()


def test_phone_width_has_no_horizontal_scroll(page, base_url):
    page.set_viewport_size({"width": 360, "height": 740})
    page.goto(base_url + "/")
    wait_for_game(page, "_ _ _ _ _")
    assert page.evaluate("document.documentElement.scrollWidth") <= 360
    box = key(page, "a").bounding_box()
    assert box["height"] >= 40  # comfortable touch target
