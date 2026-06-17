import sys
import os
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine import SearchEngine
from src.config import DATA_FILE

_RAW_SAMPLE_WORDS = [
    "aba", "abajur", "abaküs", "bilge", "bilgi", "bilgili",
    "bilgisayar", "bilgisayarcı", "bilim", "çiçek", "çığ",
    "güzel", "güzellik", "istanbul", "ıslak", "ışık",
    "öğrenci", "öğretmen", "şeker", "şehir", "üzüm",
    "zurna", "zürafa",
]

from src.utils import turkish_lower as _tl
SAMPLE_WORDS = sorted(_RAW_SAMPLE_WORDS, key=_tl)


def _create_test_engine():
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
    tmp.write("\n".join(SAMPLE_WORDS))
    tmp.close()
    engine = SearchEngine(tmp.name)
    os.unlink(tmp.name)
    return engine


class TestSearchEngineBasic:
    def setup_method(self):
        self.engine = _create_test_engine()

    def test_normal_prefix_search(self):
        results = self.engine.search("bil")
        assert len(results) > 0
        assert all(r.lower().startswith("bil") for r in results)

    def test_full_word_match(self):
        results = self.engine.search("bilgisayar")
        assert "bilgisayar" in results

    def test_case_insensitive(self):
        results = self.engine.search("BİLGİSAYAR")
        assert "bilgisayar" in results

    def test_no_results(self):
        results = self.engine.search("xyz123")
        assert results == []

    def test_empty_query(self):
        results = self.engine.search("")
        assert results == []

    def test_turkish_i_search(self):
        results = self.engine.search("ışık")
        assert "ışık" in results

    def test_turkish_c_search(self):
        results = self.engine.search("çiçek")
        assert "çiçek" in results

    def test_turkish_g_search(self):
        results = self.engine.search("güzel")
        assert "güzel" in results

    def test_turkish_o_search(self):
        results = self.engine.search("öğr")
        assert len(results) > 0
        assert all("öğr" in r.lower() for r in results)

    def test_turkish_s_search(self):
        results = self.engine.search("şe")
        assert len(results) > 0

    def test_limit_results(self):
        results = self.engine.search("a", limit=2)
        assert len(results) <= 2

    def test_word_count(self):
        assert self.engine.word_count == len(SAMPLE_WORDS)


class TestSearchEngineWithRealData:
    """These tests only run if the real tdk_words.txt exists."""

    @classmethod
    def setup_class(cls):
        if not os.path.exists(DATA_FILE):
            import pytest
            pytest.skip("tdk_words.txt not found, skipping real data tests")
        cls.engine = SearchEngine(DATA_FILE)

    def test_real_data_loaded(self):
        assert self.engine.word_count > 90000

    def test_real_prefix_search(self):
        results = self.engine.search("bilgisayar")
        assert len(results) > 0
        assert results[0] == "bilgisayar"

    def test_real_turkish_search(self):
        results = self.engine.search("güzel")
        assert len(results) > 0

    def test_performance_search_latency(self):
        queries = ["bil", "güzel", "İstanbul", "a", "ö", "zürafa", "şeker"]
        for q in queries:
            start = time.perf_counter()
            self.engine.search(q)
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert elapsed_ms < 50, f"Search for '{q}' took {elapsed_ms:.2f}ms (limit: 50ms)"

    def test_performance_memory(self):
        import tracemalloc
        tracemalloc.start()
        _ = SearchEngine(DATA_FILE)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 20, f"Peak memory: {peak_mb:.2f} MB (limit: 20MB)"
