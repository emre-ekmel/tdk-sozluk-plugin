import io
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main
from main import TDKDictionary
from src.definitions import DefinitionService
from src.jsonrpc import Server, serve, handle_message, METHOD_NOT_FOUND, INTERNAL_ERROR
from tests.test_definitions import GTS, fake_fetch


def _plugin(fetch=None, **kwargs):
    return TDKDictionary(definitions=DefinitionService(fetch=fetch or fake_fetch()), **kwargs)


def _offline(word, timeout):
    raise OSError("offline")


def _run_session(handlers, messages):
    stdin = io.BytesIO(b"".join(json.dumps(m, ensure_ascii=False).encode("utf-8") + b"\n" for m in messages))
    stdout = io.BytesIO()
    serve(handlers, stdin=stdin, stdout=stdout)
    return [json.loads(line) for line in stdout.getvalue().decode("utf-8").splitlines()]


def _query_obj(search):
    return {"rawQuery": f"tdk {search}", "search": search, "actionKeyword": "tdk", "searchTerms": search.split()}


class TestHandleMessage:
    def test_positional_params(self):
        resp = handle_message({"add": lambda a, b: a + b}, {"jsonrpc": "2.0", "id": 1, "method": "add", "params": [2, 3]})
        assert resp == {"jsonrpc": "2.0", "id": 1, "result": 5}

    def test_named_params(self):
        resp = handle_message({"add": lambda a, b: a + b}, {"id": 1, "method": "add", "params": {"a": 2, "b": 3}})
        assert resp["result"] == 5

    def test_unknown_method(self):
        resp = handle_message({}, {"id": 7, "method": "nope"})
        assert resp["id"] == 7
        assert resp["error"]["code"] == METHOD_NOT_FOUND

    def test_handler_exception_returns_error(self):
        def boom():
            raise ValueError("bad")
        resp = handle_message({"boom": boom}, {"id": 3, "method": "boom", "params": []})
        assert resp["error"]["code"] == INTERNAL_ERROR

    def test_notification_gets_no_response(self):
        assert handle_message({"ping": lambda: "pong"}, {"method": "ping"}) is None
        assert handle_message({}, {"method": "missing"}) is None


class TestServe:
    def test_skips_blank_and_invalid_lines(self):
        stdin = io.BytesIO(b"\n not json \n" + json.dumps({"id": 1, "method": "ping"}).encode() + b"\n")
        stdout = io.BytesIO()
        serve({"ping": lambda: "pong"}, stdin=stdin, stdout=stdout)
        assert [json.loads(l) for l in stdout.getvalue().splitlines()] == [{"jsonrpc": "2.0", "id": 1, "result": "pong"}]

    def test_stops_after_close(self):
        responses = _run_session(
            {"ping": lambda: "pong", "close": lambda: {}},
            [{"id": 1, "method": "close"}, {"id": 2, "method": "ping"}],
        )
        assert [r["id"] for r in responses] == [1]

    def test_output_is_utf8_one_line_per_message(self):
        stdin = io.BytesIO(json.dumps({"id": 1, "method": "w"}).encode() + b"\n")
        stdout = io.BytesIO()
        serve({"w": lambda: "şişman\nkâr"}, stdin=stdin, stdout=stdout)
        raw = stdout.getvalue()
        assert raw.count(b"\n") == 1 and b"\r" not in raw
        assert "şişman".encode("utf-8") in raw


class TestPluginSession:
    def test_full_session(self, monkeypatch):
        opened = []
        monkeypatch.setattr(main.webbrowser, "open", opened.append)

        plugin = _plugin()
        responses = _run_session(plugin.handlers(), [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": [{"currentPluginMetadata": {}}]},
            {"jsonrpc": "2.0", "id": 2, "method": "query", "params": [_query_obj("sisman"), {}]},
            {"jsonrpc": "2.0", "id": 3, "method": "context_menu", "params": ["şişman"]},
            {"jsonrpc": "2.0", "id": 4, "method": "open_url", "params": [["şişman"]]},
            {"jsonrpc": "2.0", "id": 5, "method": "close", "params": []},
        ])
        by_id = {r["id"]: r for r in responses}
        assert all("error" not in r for r in responses)

        assert by_id[1]["result"] == {}
        assert plugin._engine is not None

        results = by_id[2]["result"]["result"]
        assert results[0]["Title"] == "şişman"
        assert results[0]["JsonRPCAction"] == {"method": "open_url", "parameters": ["şişman"]}
        assert results[0]["ContextData"] == "şişman"

        menu = by_id[3]["result"]["result"]
        assert menu[0]["SubTitle"].endswith("?ara=%C5%9Fi%C5%9Fman")

        assert by_id[4]["result"] == {"hide": True}
        assert opened == ["https://sozluk.gov.tr/?ara=%C5%9Fi%C5%9Fman"]

    def test_action_parameter_shapes(self, monkeypatch):
        opened = []
        monkeypatch.setattr(main.webbrowser, "open", opened.append)
        plugin = _plugin()
        plugin.open_url("kâr")
        plugin.open_url(["kâr"])
        plugin.open_url([["kâr"]])
        assert len(set(opened)) == 1 and opened[0].endswith("?ara=k%C3%A2r")

    def test_context_menu_shapes(self):
        plugin = _plugin()
        for arg in ("kâr", ["kâr"], [["kâr"]]):
            assert plugin.context_menu(arg)["result"][0]["Title"] == "Tarayıcıda aç: kâr"

    def test_empty_query(self):
        results = _plugin().query(_query_obj(""), {})["result"]
        assert results[0]["Title"] == "TDK Sözlük"
        assert "JsonRPCAction" not in results[0]

    def test_not_found(self):
        results = _plugin().query(_query_obj("xqzw"), {})["result"]
        assert results[0]["Title"] == "'xqzw' bulunamadı"

    def test_scores_descending(self):
        results = _plugin().query(_query_obj("kar"), {})["result"]
        scores = [r["Score"] for r in results]
        assert scores == sorted(scores, reverse=True) and len(set(scores)) == len(scores)

    def test_reload_data(self):
        plugin = _plugin()
        plugin.initialize({})
        first = plugin._engine
        plugin.reload_data({})
        assert plugin._engine is not None and plugin._engine is not first


class TestServerConcurrency:
    def test_slow_concurrent_request_does_not_block_next(self):
        release = threading.Event()

        def slow():
            release.wait(5)
            return "slow"

        def fast():
            release.set()
            return "fast"

        stdin = io.BytesIO(b"".join(json.dumps(m).encode() + b"\n" for m in [
            {"id": 1, "method": "slow"}, {"id": 2, "method": "fast"},
        ]))
        stdout = io.BytesIO()
        Server({"slow": slow, "fast": fast}, stdin=stdin, stdout=stdout, concurrent=("slow",)).serve()
        responses = [json.loads(l) for l in stdout.getvalue().splitlines()]
        assert [r["id"] for r in responses] == [2, 1]

    def test_notify_writes_notification(self):
        stdout = io.BytesIO()
        Server({}, stdin=io.BytesIO(b""), stdout=stdout).notify("CopyToClipboard", ["kâr", False, True])
        assert json.loads(stdout.getvalue()) == {"jsonrpc": "2.0", "method": "CopyToClipboard", "params": ["kâr", False, True]}

    def test_ignores_incoming_responses(self):
        stdin = io.BytesIO(json.dumps({"jsonrpc": "2.0", "id": 5, "result": None}).encode() + b"\n")
        stdout = io.BytesIO()
        Server({}, stdin=stdin, stdout=stdout).serve()
        assert stdout.getvalue() == b""


class TestDefinitionsInResults:
    def test_exact_match_shows_first_meaning(self):
        results = _plugin().query(_query_obj("kar"), {})["result"]
        kar = next(r for r in results if r["Title"] == "kar")
        assert kar["SubTitle"].startswith("isim · Atmosferdeki su buharının")
        assert kar["SubTitleToolTip"].startswith("1. Atmosferdeki")

    def test_circumflex_variant_defined_from_same_response(self):
        calls = []
        results = _plugin(fetch=fake_fetch(calls=calls)).query(_query_obj("kar"), {})["result"]
        kar_ = next(r for r in results if r["Title"] == "kâr")
        assert kar_["SubTitle"] == "isim · Alışveriş işlerinin sağladığı para kazancı; getiri  (4 anlam)"
        assert calls == ["kar"] or set(calls) == {"kar", "kâr"}

    def test_prefix_only_matches_not_fetched(self):
        calls = []
        _plugin(fetch=fake_fetch(calls=calls)).query(_query_obj("kar"), {})
        assert set(calls) <= {"kar", "kâr", "Kar"}

    def test_offline_falls_back_quickly(self):
        plugin = _plugin(fetch=_offline)
        start = time.perf_counter()
        results = plugin.query(_query_obj("kar"), {})["result"]
        results = plugin.query(_query_obj("kar"), {})["result"]
        assert time.perf_counter() - start < 1.0
        assert results[0]["SubTitle"] == "TDK Sözlük'te 'kar' tanımını aç"
        assert "SubTitleToolTip" not in results[0]

    def test_slow_network_does_not_hold_results(self, monkeypatch):
        monkeypatch.setattr(main, "DEFINITION_WAIT", 0.05)
        gate = threading.Event()
        plugin = _plugin(fetch=fake_fetch(gate=gate))
        start = time.perf_counter()
        first = plugin.query(_query_obj("kar"), {})["result"]
        assert time.perf_counter() - start < 1.0
        assert first[0]["SubTitle"] == "TDK Sözlük'te 'kar' tanımını aç"
        gate.set()
        plugin._definitions.lookup("kar", wait=2)
        again = plugin.query(_query_obj("kar"), {})["result"]
        assert again[0]["SubTitle"].startswith("isim ·")


class TestContextMenuDefinitions:
    def test_lists_meanings_with_copy_action(self):
        items = _plugin().context_menu("kar")["result"]
        assert items[0]["Title"] == "Tarayıcıda aç: kar"
        assert items[1]["JsonRPCAction"] == {"method": "copy_text", "parameters": ["kar"]}
        meanings = items[2:]
        assert meanings[0]["Title"].startswith("1. Atmosferdeki")
        assert meanings[0]["SubTitle"].startswith("isim · “")
        assert meanings[0]["JsonRPCAction"]["method"] == "copy_text"

    def test_not_in_tdk(self):
        items = _plugin().context_menu("xqzw")["result"]
        assert items[-1]["Title"] == "TDK'da bu madde için anlam bulunamadı"

    def test_offline(self):
        items = _plugin(fetch=_offline).context_menu("kar")["result"]
        assert items[-1]["Title"] == "Anlamlar yüklenemedi"
        assert "JsonRPCAction" not in items[-1]

    def test_copy_text_calls_flow_api(self):
        sent = []
        plugin = _plugin(notify=lambda method, params: sent.append((method, params)))
        assert plugin.copy_text(["kâr"]) == {"hide": True}
        assert sent == [("CopyToClipboard", ["kâr", False, True])]
