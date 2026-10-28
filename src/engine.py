import bisect

from src.utils import search_key, turkish_lower


class SearchEngine:
    def __init__(self, data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            self._words = [w for w in f.read().splitlines() if w]

    @property
    def word_count(self):
        return len(self._words)

    def search(self, query, limit=10):
        query_key = search_key(query)
        if not query_key:
            return []

        idx = bisect.bisect_left(self._words, query_key, key=search_key)

        results = []
        while idx < len(self._words) and len(results) < limit:
            if search_key(self._words[idx]).startswith(query_key):
                results.append(self._words[idx])
                idx += 1
            else:
                break

        # Words spelled exactly as typed (e.g. "kâr" vs "kar") go first; sort is stable.
        query_lower = turkish_lower(query.strip())
        results.sort(key=lambda w: turkish_lower(w) != query_lower)
        return results
