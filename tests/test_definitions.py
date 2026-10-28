import json
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import definitions
from src.definitions import DefinitionService, Sense, parse_response

# Trimmed real responses from https://sozluk.gov.tr/gts
with open(os.path.join(os.path.dirname(__file__), "fixtures", "gts_responses.json"), encoding="utf-8") as f:
    GTS = json.load(f)


def fake_fetch(responses=GTS, calls=None, gate=None):
    def fetch(word, timeout):
        if calls is not None:
            calls.append(word)
        if gate is not None:
            gate.wait(5)
        if word not in responses:
            return {"error": "Sonuç bulunamadı"}
        return responses[word]
    return fetch


class TestParseResponse:
    def test_error_response(self):
        assert parse_response(GTS["xqzw"]) == {}

    def test_case_and_circumflex_variants_kept_separate(self):
        parsed = parse_response(GTS["kar"])
        assert set(parsed) == {"kar", "kâr"}
        assert parsed["kâr"][0].text.startswith("Alışveriş işlerinin")

    def test_homographs_merged_and_renumbered(self):
        senses = parse_response(GTS["yüz"])["yüz"]
        assert [s.number for s in senses] == list(range(1, len(senses) + 1))
        assert senses[0].text == "Doksan dokuzdan sonra gelen sayının adı"
        assert senses[0].kind == "isim"

    def test_kind_carries_forward_until_next_tag(self):
        senses = parse_response(GTS["yüz"])["yüz"]
        assert senses[1].kind == "isim"          # untagged, inherits
        assert senses[2].kind == "sıfat"         # tagged

    def test_example(self):
        senses = parse_response(GTS["kar"])["kar"]
        assert senses[0].example

    def test_skips_empty_senses(self):
        data = [{"madde": "x", "anlamlarListe": [{"anlam": ""}, {"anlam": " a "}]}]
        assert parse_response(data) == {"x": [Sense(number=1, text="a")]}


class TestDefinitionService:
    def test_lookup_and_cache(self):
        calls = []
        svc = DefinitionService(fetch=fake_fetch(calls=calls))
        senses = svc.lookup("kar", wait=2)
        assert senses[0].text.startswith("Atmosferdeki")
        assert svc.lookup("kar", wait=2) == senses
        assert calls == ["kar"]

    def test_variants_from_one_response_are_cached(self):
        calls = []
        svc = DefinitionService(fetch=fake_fetch(calls=calls))
        svc.lookup("kar", wait=2)
        assert svc.cached("kâr")
        assert svc.lookup("kâr", wait=2)
        assert calls == ["kar"]

    def test_case_and_circumflex_variants_share_one_fetch(self):
        calls = []
        svc = DefinitionService(fetch=fake_fetch(calls=calls))
        result = svc.lookup_many(["kar", "Kar", "kâr"], wait=2)
        assert len(calls) == 1
        assert result["kar"] and result["kâr"]
        assert result["Kar"] == []  # TDK has no separate "Kar" headword

    def test_not_found_cached_as_empty(self):
        calls = []
        svc = DefinitionService(fetch=fake_fetch(calls=calls))
        assert svc.lookup("xqzw", wait=2) == []
        assert svc.lookup("xqzw", wait=2) == []
        assert calls == ["xqzw"]

    def test_slow_fetch_returns_none_then_fills_cache(self):
        gate = threading.Event()
        svc = DefinitionService(fetch=fake_fetch(gate=gate))
        assert svc.lookup("kar", wait=0.01) is None
        gate.set()
        assert svc.lookup("kar", wait=2)

    def test_in_flight_fetch_is_shared(self):
        gate = threading.Event()
        calls = []
        svc = DefinitionService(fetch=fake_fetch(calls=calls, gate=gate))
        svc.lookup("kar", wait=0.01)
        svc.lookup("kar", wait=0.01)
        gate.set()
        svc.lookup("kar", wait=2)
        assert calls == ["kar"]

    def test_network_error_backs_off(self):
        now = [100.0]
        calls = []

        def failing(word, timeout):
            calls.append(word)
            raise OSError("offline")

        svc = DefinitionService(fetch=failing, clock=lambda: now[0])
        assert svc.lookup("kar", wait=2) is None
        assert svc.lookup("kalem", wait=2) is None  # second failure in a row starts the backoff
        assert svc.lookup("masa", wait=2) is None   # backing off, no new fetch
        assert calls == ["kar", "kalem"]
        assert svc.lookup("kar", wait=2) is None    # failures are not cached as "not found"

        now[0] += definitions.OFFLINE_BACKOFF + 1
        svc.lookup("masa", wait=2)
        assert calls == ["kar", "kalem", "masa"]

    def test_single_failure_does_not_back_off(self):
        attempts = []

        def flaky(word, timeout):
            attempts.append(word)
            if word == "kalem":
                raise OSError("one slow request")
            return GTS["kar"]

        svc = DefinitionService(fetch=flaky)
        assert svc.lookup("kalem", wait=2) is None
        assert svc.lookup("kar", wait=2)
        assert attempts == ["kalem", "kar"]

    def test_errors_are_not_cached(self):
        attempts = []

        def flaky(word, timeout):
            attempts.append(word)
            if len(attempts) == 1:
                raise OSError("blip")
            return GTS["kar"]

        svc = DefinitionService(fetch=flaky)
        assert svc.lookup("kar", wait=2) is None
        assert svc.lookup("kar", wait=2)

    def test_lookup_many(self):
        svc = DefinitionService(fetch=fake_fetch())
        result = svc.lookup_many(["kar", "xqzw"], wait=2)
        assert result["kar"] and result["xqzw"] == []
