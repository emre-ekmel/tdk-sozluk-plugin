import os
import sys
import webbrowser
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

from lib.flowlauncher import FlowLauncher

from src.engine import SearchEngine
from src.utils import sanitize
from src.config import DATA_FILE, TDK_BROWSER_URL, MAX_RESULTS, PLUGIN_ICON


class TDKDictionary(FlowLauncher):
    _engine = None

    def _get_engine(self):
        if TDKDictionary._engine is None:
            TDKDictionary._engine = SearchEngine(DATA_FILE)
        return TDKDictionary._engine

    def query(self, query):
        raw_query = query.strip()
        if not raw_query:
            return [{
                "Title": "TDK Sözlük",
                "SubTitle": "Aramak istediğiniz kelimeyi yazın...",
                "IcoPath": PLUGIN_ICON,
            }]

        sanitized = sanitize(raw_query)
        if not sanitized:
            return []

        engine = self._get_engine()
        matches = engine.search(sanitized, limit=MAX_RESULTS)

        if not matches:
            return [{
                "Title": f"'{raw_query}' bulunamadı",
                "SubTitle": "TDK sözlüğünde bu kelime mevcut değil.",
                "IcoPath": PLUGIN_ICON,
            }]

        results = []
        for word in matches:
            encoded_word = urllib.parse.quote(word, safe='')
            results.append({
                "Title": word,
                "SubTitle": f"TDK Sözlük'te '{word}' tanımını aç",
                "IcoPath": PLUGIN_ICON,
                "JsonRPCAction": {
                    "method": "open_url",
                    "parameters": [encoded_word],
                },
                "ContextData": [word],
            })

        return results

    def open_url(self, encoded_word):
        url = TDK_BROWSER_URL.format(word=encoded_word)
        webbrowser.open(url)

    def context_menu(self, data):
        word = data[0] if data else ""
        encoded_word = urllib.parse.quote(word, safe='')
        return [
            {
                "Title": f"Tarayıcıda aç: {word}",
                "SubTitle": TDK_BROWSER_URL.format(word=encoded_word),
                "IcoPath": PLUGIN_ICON,
                "JsonRPCAction": {
                    "method": "open_url",
                    "parameters": [encoded_word],
                },
            },
        ]


if __name__ == "__main__":
    TDKDictionary()
