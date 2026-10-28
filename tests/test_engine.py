import sys
import os
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine import SearchEngine
from src.config import DATA_FILE
from src.utils import search_key

_RAW_SAMPLE_WORDS = [
    "aba", "abajur", "abaküs", "bilge", "bilgi", "bilgili",
    "bilgisayar", "bilgisayarcı", "bilim", "çiçek", "çığ",
    "güzel", "güzellik", "istanbul", "ıslak", "ışık",
    "öğrenci", "öğretmen", "şeker", "şehir", "üzüm",
    "zurna", "zürafa", "kar", "kâr", "kara", "hâlâ", "hala",
    "şişman", "(bir şeye) kulak vermek", "allah'a ısmarladık",
]

from src.utils import turkish_lower as _tl, wordlist_sort_key
SAMPLE_WORDS = sorted(_RAW_SAMPLE_WORDS, key=wordlist_sort_key)


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
        assert all(_tl(r).startswith("bil") for r in results)

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
        assert all(_tl(r).startswith("öğr") for r in results)

    def test_turkish_s_search(self):
        results = self.engine.search("şe")
        assert len(results) > 0

    def test_limit_results(self):
        results = self.engine.search("a", limit=2)
        assert len(results) <= 2

    def test_word_count(self):
        assert self.engine.word_count == len(SAMPLE_WORDS)


class TestSearchEngineFolding:
    def setup_method(self):
        self.engine = _create_test_engine()

    def test_ascii_query_finds_turkish_word(self):
        assert "şişman" in self.engine.search("sisman")
        assert "öğretmen" in self.engine.search("ogretmen")
        assert "ışık" in self.engine.search("isik")

    def test_ascii_uppercase_query(self):
        assert "istanbul" in self.engine.search("ISTANBUL")

    def test_circumflex_folding(self):
        assert "hâlâ" in self.engine.search("hala")
        assert "kâr" in self.engine.search("kar")

    def test_exact_spelling_ranked_first(self):
        assert self.engine.search("kâr")[0] == "kâr"
        assert self.engine.search("kar")[0] == "kar"
        assert self.engine.search("hâlâ")[0] == "hâlâ"
        assert self.engine.search("hala")[0] == "hala"

    def test_shorter_prefix_matches_after_exact(self):
        assert self.engine.search("kar") == ["kar", "kâr", "kara"]

    def test_parenthesized_entry(self):
        assert "(bir şeye) kulak vermek" in self.engine.search("bir şeye")

    def test_apostrophe_entry(self):
        assert "allah'a ısmarladık" in self.engine.search("allaha")
        assert "allah'a ısmarladık" in self.engine.search("allah'a")

    def test_punctuation_only_query(self):
        assert self.engine.search("()'") == []


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

    def test_real_data_sorted_for_bisect(self):
        keys = [search_key(w) for w in self.engine._words]
        assert keys == sorted(keys)

    def test_real_ascii_search(self):
        assert "şişman" in self.engine.search("sisman")
        assert "hâlâ" in self.engine.search("hala")

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
