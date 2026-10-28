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

    def suggest(self, query, limit=5):
        """Words one typo away from query: whole-word matches first, then words it could be the start of."""
        query_key = search_key(query)
        if len(query_key) < MIN_SUGGEST_LENGTH:
            return []

        ranked = {}
        for edit in _single_edits(query_key):
            idx = bisect.bisect_left(self._words, edit, key=search_key)
            if idx == len(self._words):
                continue
            word = self._words[idx]
            word_key = search_key(word)
            if not word_key.startswith(edit):
                continue
            rank = (word_key != edit, len(word_key), word_key)
            if word not in ranked or rank < ranked[word]:
                ranked[word] = rank

        return sorted(ranked, key=ranked.get)[:limit]


# Shorter queries have too many one-letter neighbours to be useful.
MIN_SUGGEST_LENGTH = 3

# search_key output is ASCII letters and single spaces.
_EDIT_ALPHABET = "abcdefghijklmnopqrstuvwxyz "


def _single_edits(key):
    splits = [(key[:i], key[i:]) for i in range(len(key) + 1)]
    deletes = [a + b[1:] for a, b in splits if b]
    transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1]
    replaces = [a + c + b[1:] for a, b in splits if b for c in _EDIT_ALPHABET if c != b[0]]
    inserts = [a + c + b for a, b in splits for c in _EDIT_ALPHABET]
    edits = {e.strip() for e in deletes + transposes + replaces + inserts}
    edits.discard(key)
    return {e for e in edits if len(e) >= MIN_SUGGEST_LENGTH - 1 and "  " not in e}
