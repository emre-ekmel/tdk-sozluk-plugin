# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Flow Launcher plugin (Python 3.12+, action keyword `tdk`) that does offline prefix lookup of Turkish words against a bundled wordlist and opens the selected word on `https://sozluk.gov.tr/?ara=<word>`. Runtime code uses only the standard library plus the `flowlauncher` SDK. User-facing strings are in Turkish.

## Commands

```bash
pip install -r requirements.txt pytest   # requirements.txt only contains the flowlauncher SDK
pytest                                   # run all tests
pytest tests/test_engine.py::TestSearchEngineBasic::test_case_insensitive   # single test
python scripts/build_wordlist.py         # re-download and rebuild data/tdk_words.txt from sozluk.gov.tr/autocomplete.json
python scripts/build_wordlist.py --resort  # re-sort the existing wordlist only (after changing search_key)
PYTHONIOENCODING=utf-8 python main.py '{"method":"query","parameters":["sisman"]}'   # call the plugin like Flow Launcher does
```

To run the plugin locally, the `flowlauncher` package must exist under `lib/` (gitignored): `pip install -r requirements.txt -t ./lib`.

## Architecture

- [main.py](main.py) — Flow Launcher JSON-RPC entry point (`TDKDictionary(FlowLauncher)`). `query()` sanitizes input, calls the engine, and returns result dicts whose `JsonRPCAction` calls `open_url`; `context_menu()` receives `ContextData`. The `SearchEngine` is cached as a class attribute so the wordlist loads once per process. It inserts `lib/` into `sys.path` but also imports `lib.flowlauncher` as a package path.
- [src/engine.py](src/engine.py) — `SearchEngine` loads `data/tdk_words.txt` into a list and does prefix search with `bisect.bisect_left(..., key=search_key)`, walks forward while entries still match, then stably moves words spelled exactly as typed (e.g. `kâr` vs `kar`) to the front. `main.py` sets a descending `Score` so Flow Launcher keeps that order.
- [src/utils.py](src/utils.py) — `turkish_lower` (translate table handling `I→ı`, `İ→i`; do not replace with `str.lower()`), `search_key` (lowercase + fold `çğıöşüâîû` to ASCII + drop punctuation/digits, so `sisman`, `hala`, `bir şeye` match `şişman`, `hâlâ`, `(bir şeye) kulak vermek`), and `sanitize`.
- [src/config.py](src/config.py) — paths (resolved relative to the plugin dir), URL template, `MAX_RESULTS`.

**Critical invariant:** `data/tdk_words.txt` must be sorted with `wordlist_sort_key` (primary key `search_key`). The binary search silently returns wrong/missing results if the file is edited by hand out of order or if `search_key` changes without regenerating the file — after changing it, run `python scripts/build_wordlist.py --resort` (re-sorts the existing file, no download). `TestSearchEngineWithRealData::test_real_data_sorted_for_bisect` guards this.

## Release

[.github/workflows/publish.yml](.github/workflows/publish.yml) runs on every push to `main` (except workflow-only changes): it installs requirements into `lib/`, zips `src data images lib main.py plugin.json` into `Flow.Launcher.Plugin.TDKSozluk.zip`, and publishes a GitHub release tagged `v<Version>` from [plugin.json](plugin.json). Bump `Version` in `plugin.json` when a push should produce a new release; anything the plugin needs at runtime must live in one of the zipped paths.

The root-level `TDK Sözlük-<ID>.json` is the Flow Launcher plugin-store manifest (submitted separately, not shipped in the zip). Its `Version`/`UrlDownload` should match `plugin.json`. Note `.gitignore` intends to exclude it via `TDKSozluk-*.json`, but that pattern doesn't match the actual filename.
