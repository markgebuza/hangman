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
