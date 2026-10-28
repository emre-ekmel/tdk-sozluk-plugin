"""Online word definitions from the TDK API, cached for the life of the plugin process.

Lookups never block for long: callers say how long they are willing to wait and
get None if the answer isn't ready yet (the fetch keeps going and fills the
cache). After FAILURES_BEFORE_BACKOFF network errors in a row, fetching pauses
for OFFLINE_BACKOFF seconds so an offline machine doesn't pay a timeout on every
keystroke.
"""

import concurrent.futures
import http.client
import json
import sys
import threading
import time
import urllib.parse
from dataclasses import dataclass

from src.config import TDK_API_URL
from src.utils import turkish_lower

OFFLINE_BACKOFF = 60.0
FAILURES_BEFORE_BACKOFF = 2

_API = urllib.parse.urlsplit(TDK_API_URL)
# One keep-alive HTTPS connection per worker thread saves the TLS handshake (~70 ms) on repeat lookups.
_connections = threading.local()


_CIRCUMFLEX_FOLD = str.maketrans("âîû", "aiu")


def _lookup_key(word):
    # TDK answers "kale" and "Kale", or "kar" and "kâr", with the same response, so fetch once per key.
    return turkish_lower(word).translate(_CIRCUMFLEX_FOLD)


@dataclass(frozen=True)
class Sense:
    number: int
    text: str
    kind: str = ""
    example: str = ""


def parse_response(data):
    """Map a /gts response to {headword: [Sense, ...]}, merging homographs (e.g. the two "yüz" entries)."""
    if not isinstance(data, list):
        return {}

    senses_by_word = {}
    for entry in data:
        word = (entry.get("madde") or "").strip()
        if not word:
            continue
        senses = senses_by_word.setdefault(word, [])
        kind = ""
        for sense in entry.get("anlamlarListe") or []:
            text = (sense.get("anlam") or "").strip()
            if not text:
                continue
            # Only the first sense of a group is tagged (isim, sıfat, ...); later ones inherit it.
            tags = [o.get("tam_adi") for o in sense.get("ozelliklerListe") or [] if o.get("tam_adi")]
            if tags:
                kind = ", ".join(tags)
            examples = sense.get("orneklerListe") or []
            example = (examples[0].get("ornek") or "").strip() if examples else ""
            senses.append(Sense(number=len(senses) + 1, text=text, kind=kind, example=example))
    return senses_by_word


def fetch_from_tdk(word, timeout):
    path = f"{_API.path}?{_API.query}".format(word=urllib.parse.quote(word, safe=""))
    for attempt in range(2):
        conn = getattr(_connections, "conn", None)
        if conn is None:
            conn = _connections.conn = http.client.HTTPSConnection(_API.netloc, timeout=timeout)
        try:
            conn.request("GET", path, headers={"User-Agent": "Mozilla/5.0"})
            resp = conn.getresponse()
            body = resp.read()
        except (http.client.RemoteDisconnected, ConnectionResetError, BrokenPipeError):
            # The server closed an idle keep-alive connection; reconnect once.
            conn.close()
            _connections.conn = None
            if attempt:
                raise
            continue
        except Exception:
            conn.close()
            _connections.conn = None
            raise
        if resp.status != 200:
            raise OSError(f"TDK API returned HTTP {resp.status}")
        return json.loads(body.decode("utf-8"))


class DefinitionService:
    def __init__(self, fetch=None, timeout=3.0, max_workers=4, clock=time.monotonic):
        self._fetch = fetch
        self._timeout = timeout
        self._clock = clock
        self._cache = {}
        self._fetched_keys = set()
        self._in_flight = {}
        self._offline_until = 0.0
        self._failures = 0
        self._lock = threading.Lock()
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tdk-def")

    def cached(self, word):
        """Senses for word if known ([] means TDK has no entry), else None."""
        senses = self._cache.get(word)
        if senses is None and _lookup_key(word) in self._fetched_keys:
            return []
        return senses

    def lookup_many(self, words, wait):
        """Return {word: senses or None}, waiting at most `wait` seconds overall for missing ones."""
        futures = set()
        for word in words:
            if self.cached(word) is None:
                future = self._start(word)
                if future is not None:
                    futures.add(future)
        if futures:
            concurrent.futures.wait(futures, timeout=wait)
        return {word: self.cached(word) for word in words}

    def lookup(self, word, wait):
        return self.lookup_many([word], wait)[word]

    def close(self):
        self._pool.shutdown(wait=False, cancel_futures=True)

    def _start(self, word):
        key = _lookup_key(word)
        with self._lock:
            if key in self._in_flight:
                return self._in_flight[key]
            if key in self._fetched_keys:
                return None  # finished since the caller checked the cache
            if self._clock() < self._offline_until:
                return None
            future = self._pool.submit(self._fetch_and_cache, word, key)
            self._in_flight[key] = future
            return future

    def _fetch_and_cache(self, word, key):
        try:
            data = (self._fetch or fetch_from_tdk)(word, self._timeout)
        except Exception as exc:
            print(f"TDK lookup failed for {word!r}: {exc}", file=sys.stderr)
            with self._lock:
                self._failures += 1
                if self._failures >= FAILURES_BEFORE_BACKOFF:
                    self._offline_until = self._clock() + OFFLINE_BACKOFF
                self._in_flight.pop(key, None)
            return

        # The response covers every case/circumflex variant ("kar" also returns "kâr"); cache them all.
        senses_by_word = parse_response(data)
        with self._lock:
            self._failures = 0
            self._cache.update(senses_by_word)
            self._fetched_keys.add(key)
            self._in_flight.pop(key, None)
