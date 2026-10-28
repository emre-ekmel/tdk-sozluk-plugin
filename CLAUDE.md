# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Flow Launcher plugin (Python 3.12+, action keyword `tdk`) that does offline prefix lookup of Turkish words against a bundled wordlist, shows meanings fetched from the TDK API (`https://sozluk.gov.tr/gts?ara=<word>`), and opens the selected word on `https://sozluk.gov.tr/?ara=<word>`. Runtime code uses only the standard library (no SDK, no `lib/`). User-facing strings are in Turkish.

## Commands

```bash
pip install pytest                       # only dev dependency
pytest                                   # run all tests
pytest tests/test_engine.py::TestSearchEngineBasic::test_case_insensitive   # single test
python scripts/build_wordlist.py         # re-download and rebuild data/tdk_words.txt from sozluk.gov.tr/autocomplete.json
python scripts/build_wordlist.py --resort  # re-sort the existing wordlist only (after changing search_key)
printf '%s
' '{"jsonrpc":"2.0","id":1,"method":"query","params":[{"search":"sisman"},{}]}' | python main.py   # talk to the plugin like Flow does
```

## Architecture

- [main.py](main.py) — `TDKDictionary` exposes the JSON-RPC methods (`initialize`, `query`, `context_menu`, `open_url`, `reload_data`, `close`). `plugin.json` declares `"Language": "Python_v2"`, so Flow starts the process **once** (via `runpy`) and keeps it alive; the wordlist is loaded in `initialize` and reused for every keystroke. `query` receives Flow's camelCase Query object (`search` = text without the action keyword) and must return `{"result": [...]}`; actions must return `{"hide": bool}`. Action/context arguments are unwrapped with `_first_str` because Flow may nest them (`["x"]` vs `[["x"]]`).
- [src/jsonrpc.py](src/jsonrpc.py) — stdlib JSON-RPC 2.0 `Server`: one UTF-8 JSON message per line on stdin/stdout. `query` and `context_menu` run on worker threads (responses may come back out of order). `Server.notify` calls Flow's public API (e.g. `CopyToClipboard`) — method names are the C# names in Flow's `JsonRPCPublicAPI`. **Never `print()` to stdout** — it corrupts the protocol; log to stderr.
- [src/definitions.py](src/definitions.py) — `DefinitionService`: fetches `/gts`, parses senses, caches in memory for the process lifetime. Callers pass a wait budget (`DEFINITION_WAIT` for queries, `CONTEXT_MENU_WAIT` for the context menu, in [src/config.py](src/config.py)) and get `None` if the answer isn't ready; the fetch continues and fills the cache. Fetches are de-duplicated by `_lookup_key` because TDK folds case and circumflex (`kar` returns both **kar** and **kâr**). Two consecutive network failures pause fetching for `OFFLINE_BACKOFF` seconds. Queries only fetch for results whose `search_key` equals the query's, so typing a prefix never hits the network.
- Pushing late results to Flow (`UpdateResults`) is deliberately not used: Flow's v2 handler builds a Query with only `TrimmedQuery`, and the main window discards updates whose `OriginalQuery` doesn't match.
- [src/engine.py](src/engine.py) — `SearchEngine` loads `data/tdk_words.txt` into a list and does prefix search with `bisect.bisect_left(..., key=search_key)`, walks forward while entries still match, then stably moves words spelled exactly as typed (e.g. `kâr` vs `kar`) to the front. `main.py` sets a descending `Score` so Flow Launcher keeps that order.
- [src/utils.py](src/utils.py) — `turkish_lower` (translate table handling `I→ı`, `İ→i`; do not replace with `str.lower()`), `search_key` (lowercase + fold `çğıöşüâîû` to ASCII + drop punctuation/digits, so `sisman`, `hala`, `bir şeye` match `şişman`, `hâlâ`, `(bir şeye) kulak vermek`), and `sanitize`.
- [src/config.py](src/config.py) — paths (resolved relative to the plugin dir), URL template, `MAX_RESULTS`.

Tests never touch the network: [tests/conftest.py](tests/conftest.py) replaces `fetch_from_tdk` with a failing stub. Inject `DefinitionService(fetch=fake_fetch(...))` (see `tests/test_definitions.py`, which uses trimmed real responses in `tests/fixtures/gts_responses.json`).

**Critical invariant:** `data/tdk_words.txt` must be sorted with `wordlist_sort_key` (primary key `search_key`). The binary search silently returns wrong/missing results if the file is edited by hand out of order or if `search_key` changes without regenerating the file — after changing it, run `python scripts/build_wordlist.py --resort` (re-sorts the existing file, no download). `TestSearchEngineWithRealData::test_real_data_sorted_for_bisect` guards this.

## Release

[.github/workflows/publish.yml](.github/workflows/publish.yml) runs on every push to `main` (except workflow-only changes): it runs `pytest`, zips `src data images main.py plugin.json` into `Flow.Launcher.Plugin.TDKSozluk.zip`, and publishes a GitHub release tagged `v<Version>` from [plugin.json](plugin.json). Bump `Version` in `plugin.json` when a push should produce a new release; anything the plugin needs at runtime must live in one of the zipped paths.

The root-level `TDK Sözlük-<ID>.json` is the Flow Launcher plugin-store manifest (submitted separately, not shipped in the zip). Its `Version`/`UrlDownload` should match `plugin.json`. Note `.gitignore` intends to exclude it via `TDKSozluk-*.json`, but that pattern doesn't match the actual filename.
