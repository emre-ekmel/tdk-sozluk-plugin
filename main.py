import os
import sys
import webbrowser
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.engine import SearchEngine
from src.definitions import DefinitionService
from src.jsonrpc import Server
from src.utils import sanitize, search_key
from src.config import (
    DATA_FILE, TDK_BROWSER_URL, MAX_RESULTS, PLUGIN_ICON, DEFINITION_WAIT, CONTEXT_MENU_WAIT,
)

# Fetch definitions for at most this many results that match the query exactly (e.g. "kar" -> kar, kâr).
MAX_DEFINED_RESULTS = 3
MAX_SUGGESTIONS = 5
TOOLTIP_SENSES = 10


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


def _describe(senses):
    first = senses[0]
    summary = f"{first.kind} · {first.text}" if first.kind else first.text
    if len(senses) > 1:
        summary += f"  ({len(senses)} anlam)"
    return summary


def _tooltip(senses):
    lines = [f"{s.number}. {s.text}" for s in senses[:TOOLTIP_SENSES]]
    if len(senses) > TOOLTIP_SENSES:
        lines.append(f"… +{len(senses) - TOOLTIP_SENSES} anlam")
    return "\n".join(lines)


class TDKDictionary:
    def __init__(self, data_file=DATA_FILE, definitions=None, notify=None):
        self._data_file = data_file
        self._engine = None
        self._definitions = definitions if definitions is not None else DefinitionService()
        # Sends a notification to Flow's public API; set by the server.
        self.notify = notify or (lambda method, params: None)

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
            "copy_text": self.copy_text,
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
        self._definitions.close()
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
            return self._not_found_results(raw_query, sanitized)

        query_key = search_key(sanitized)
        exact = [w for w in matches if search_key(w) == query_key][:MAX_DEFINED_RESULTS]
        definitions = self._definitions.lookup_many(exact, wait=DEFINITION_WAIT) if exact else {}

        results = []
        for rank, word in enumerate(matches):
            senses = definitions.get(word) or self._definitions.cached(word)
            result = {
                "Title": word,
                "SubTitle": _describe(senses) if senses else f"TDK Sözlük'te '{word}' tanımını aç",
                "IcoPath": PLUGIN_ICON,
                # Explicit descending score keeps the engine's order (exact match first).
                "Score": (len(matches) - rank) * 100,
                "JsonRPCAction": {
                    "method": "open_url",
                    "parameters": [word],
                },
                "ContextData": word,
            }
            if senses:
                result["SubTitleToolTip"] = _tooltip(senses)
            results.append(result)

        return results

    def _not_found_results(self, raw_query, sanitized):
        suggestions = self._get_engine().suggest(sanitized, limit=MAX_SUGGESTIONS)
        results = [{
            "Title": f"'{raw_query}' bulunamadı",
            "SubTitle": "Bunu mu demek istediniz?" if suggestions else "TDK sözlüğünde bu kelime mevcut değil.",
            "IcoPath": PLUGIN_ICON,
            "Score": (len(suggestions) + 1) * 100,
        }]
        for rank, word in enumerate(suggestions):
            senses = self._definitions.cached(word)
            results.append({
                "Title": word,
                "SubTitle": _describe(senses) if senses else f"TDK Sözlük'te '{word}' tanımını aç",
                "IcoPath": PLUGIN_ICON,
                "Score": (len(suggestions) - rank) * 100,
                "JsonRPCAction": {"method": "open_url", "parameters": [word]},
                "ContextData": word,
            })
        return results

    def open_url(self, *args):
        word = _first_str(list(args))
        webbrowser.open(_tdk_url(word))
        return {"hide": True}

    def copy_text(self, *args):
        text = _first_str(list(args))
        # Flow API: CopyToClipboard(text, directCopy, showDefaultNotification)
        self.notify("CopyToClipboard", [text, False, True])
        return {"hide": True}

    def context_menu(self, *args):
        word = _first_str(list(args))
        items = [
            {
                "Title": f"Tarayıcıda aç: {word}",
                "SubTitle": _tdk_url(word),
                "IcoPath": PLUGIN_ICON,
                "JsonRPCAction": {"method": "open_url", "parameters": [word]},
            },
            {
                "Title": f"Kelimeyi kopyala: {word}",
                "SubTitle": "Panoya kopyala",
                "IcoPath": PLUGIN_ICON,
                "JsonRPCAction": {"method": "copy_text", "parameters": [word]},
            },
        ]

        senses = self._definitions.lookup(word, wait=CONTEXT_MENU_WAIT)
        if senses is None:
            items.append({
                "Title": "Anlamlar yüklenemedi",
                "SubTitle": "İnternet bağlantınızı kontrol edip tekrar deneyin.",
                "IcoPath": PLUGIN_ICON,
            })
        elif not senses:
            items.append({
                "Title": "TDK'da bu madde için anlam bulunamadı",
                "SubTitle": "Tarayıcıda açarak kontrol edebilirsiniz.",
                "IcoPath": PLUGIN_ICON,
            })
        for sense in senses or []:
            details = [d for d in (sense.kind, f"“{sense.example}”" if sense.example else "") if d]
            items.append({
                "Title": f"{sense.number}. {sense.text}",
                "SubTitle": " · ".join(details + ["Enter: anlamı kopyala"]),
                "TitleToolTip": sense.text,
                "IcoPath": PLUGIN_ICON,
                "JsonRPCAction": {"method": "copy_text", "parameters": [sense.text]},
            })
        return {"result": items}


def _tdk_url(word):
    return TDK_BROWSER_URL.format(word=urllib.parse.quote(word, safe=''))


if __name__ == "__main__":
    # Flow reads stderr as UTF-8; Windows would otherwise use the ANSI code page (cp1254 on Turkish systems).
    if sys.stderr is not None:  # pythonw.exe has no stderr unless Flow redirects it
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    plugin = TDKDictionary()
    server = Server(plugin.handlers(), concurrent=("query", "context_menu"))
    plugin.notify = server.notify
    server.serve()
