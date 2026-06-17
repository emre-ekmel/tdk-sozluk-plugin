import bisect

from src.utils import turkish_lower


class SearchEngine:
    def __init__(self, data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            self._words = [w for w in f.read().splitlines() if w]

    @property
    def word_count(self):
        return len(self._words)

    def search(self, query, limit=10):
        if not query:
            return []

        query_lower = turkish_lower(query)
        idx = bisect.bisect_left(self._words, query_lower, key=turkish_lower)

        results = []
        while idx < len(self._words) and len(results) < limit:
            word_lower = turkish_lower(self._words[idx])
            if word_lower.startswith(query_lower):
                results.append(self._words[idx])
                idx += 1
            else:
                break

        return results
