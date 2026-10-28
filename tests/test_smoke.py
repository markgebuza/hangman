"""Runs smoke_test.py against a real local server so the script stays working."""

import threading

from werkzeug.serving import make_server

import smoke_test
from server import create_app


def test_smoke_script_passes_against_local_server(monkeypatch, capsys):
    server = make_server("127.0.0.1", 0, create_app(), threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setattr(smoke_test, "results", [])
        monkeypatch.setattr("sys.argv", ["smoke_test.py", f"http://127.0.0.1:{server.server_port}/"])
        assert smoke_test.main() == 0
    finally:
        server.shutdown()
    out = capsys.readouterr().out
    assert "[FAIL]" not in out
    assert " 0 failed" in out
