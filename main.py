import os
import sys
import webbrowser
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.engine import SearchEngine
from src.jsonrpc import serve
from src.utils import sanitize
from src.config import DATA_FILE, TDK_BROWSER_URL, MAX_RESULTS, PLUGIN_ICON


def _first_str(value):
    # Flow may pass action/context arguments as "x", ["x"] or [["x"]].
    while isinstance(value, list):
        if not value:
            return ""
        value = value[0]
    return value if isinstance(value, str) else ""


def _query_text(query):
    # Python_v2 sends the Query object (camelCase); "search" excludes the action keyword.
    if isinstance(query, dict):
        return query.get("search") or ""
    return _first_str(query)


class TDKDictionary:
    def __init__(self, data_file=DATA_FILE):
        self._data_file = data_file
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            self._engine = SearchEngine(self._data_file)
        return self._engine

    def handlers(self):
        return {
            "initialize": self.initialize,
            "query": self.query,
            "context_menu": self.context_menu,
            "open_url": self.open_url,
            "reload_data": self.reload_data,
            "close": self.close,
        }

    def initialize(self, *_context):
        # Load the wordlist up front so the first keystroke doesn't pay for it.
        self._get_engine()
        return {}

    def reload_data(self, *_args):
        self._engine = None
        self._get_engine()
        return {}

    def close(self, *_args):
        return {}

    def query(self, query, *_settings):
        return {"result": self.search_results(_query_text(query))}

    def search_results(self, text):
        raw_query = text.strip()
        if not raw_query:
            return [{
                "Title": "TDK Sözlük",
                "SubTitle": "Aramak istediğiniz kelimeyi yazın...",
                "IcoPath": PLUGIN_ICON,
            }]

        sanitized = sanitize(raw_query)
        if not sanitized:
            return []

        matches = self._get_engine().search(sanitized, limit=MAX_RESULTS)

        if not matches:
            return [{
                "Title": f"'{raw_query}' bulunamadı",
                "SubTitle": "TDK sözlüğünde bu kelime mevcut değil.",
                "IcoPath": PLUGIN_ICON,
            }]

        results = []
        for rank, word in enumerate(matches):
            results.append({
                "Title": word,
                "SubTitle": f"TDK Sözlük'te '{word}' tanımını aç",
                "IcoPath": PLUGIN_ICON,
                # Explicit descending score keeps the engine's order (exact match first).
                "Score": (len(matches) - rank) * 100,
                "JsonRPCAction": {
                    "method": "open_url",
                    "parameters": [word],
                },
                "ContextData": word,
            })

        return results

    def open_url(self, *args):
        word = _first_str(list(args))
        webbrowser.open(_tdk_url(word))
        return {"hide": True}

    def context_menu(self, *args):
        word = _first_str(list(args))
        return {"result": [
            {
                "Title": f"Tarayıcıda aç: {word}",
                "SubTitle": _tdk_url(word),
                "IcoPath": PLUGIN_ICON,
                "JsonRPCAction": {
                    "method": "open_url",
                    "parameters": [word],
                },
            },
        ]}


def _tdk_url(word):
    return TDK_BROWSER_URL.format(word=urllib.parse.quote(word, safe=''))


if __name__ == "__main__":
    serve(TDKDictionary().handlers())
