import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import sanitize, turkish_lower, normalize_query


class TestTurkishLower:
    def test_uppercase_turkish_i(self):
        assert turkish_lower("İSTANBUL") == "istanbul"

    def test_uppercase_turkish_I(self):
        assert turkish_lower("ILIK") == "ılık"

    def test_mixed_case(self):
        assert turkish_lower("BiLGiSAYAR") == "bilgisayar"

    def test_all_turkish_chars(self):
        assert turkish_lower("ÇĞİÖŞÜ") == "çğiöşü"

    def test_already_lowercase(self):
        assert turkish_lower("merhaba") == "merhaba"

    def test_empty_string(self):
        assert turkish_lower("") == ""


class TestSanitize:
    def test_remove_double_quotes(self):
        assert sanitize('"bilgi"') == "bilgi"

    def test_remove_single_quotes(self):
        assert sanitize("'kelime'") == "kelime"

    def test_remove_parentheses(self):
        assert sanitize("(sözlük)") == "sözlük"

    def test_remove_digits(self):
        assert sanitize("bilgisayar2024") == "bilgisayar"

    def test_remove_brackets(self):
        assert sanitize("[test]") == "test"

    def test_mixed_junk(self):
        assert sanitize('"bilgi" (123)') == "bilgi"

    def test_preserve_turkish_chars(self):
        assert sanitize("çğıöşü") == "çğıöşü"

    def test_collapse_whitespace(self):
        assert sanitize("  çok   boşluk  ") == "çok boşluk"

    def test_empty_string(self):
        assert sanitize("") == ""


class TestNormalizeQuery:
    def test_combined(self):
        assert normalize_query('"BİLGİSAYAR"') == "bilgisayar"

    def test_turkish_I_sanitized(self):
        assert normalize_query("ILIK (1)") == "ılık"

    def test_plain_word(self):
        assert normalize_query("merhaba") == "merhaba"
