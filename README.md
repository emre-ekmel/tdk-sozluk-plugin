# Flow Launcher TDK Sözlük Plugin

An offline-first Flow Launcher plugin for looking up Turkish words in the Turkish Language Association (TDK) dictionary instantly.

## Features

- **Offline-First:** All search matching is performed locally against a pre-compiled database of ~98,000 words. No internet required for searching.
- **Sub-1ms Lookups:** Uses binary search (`bisect`) for prefix matching, achieving O(log N) lookup times.
- **Turkish Character Support:** Correctly handles Turkish-specific casing (e.g. `I`/`ı` and `İ`/`i` transitions) and character normalization during searches.
- **Typo-Friendly Matching:** Works without Turkish characters or circumflexes: `sisman` finds **şişman**, `hala` finds **hâlâ**, `bir seye` finds **(bir şeye) kulak vermek**.
- **Persistent Process:** Uses Flow Launcher's JSON-RPC v2 (`Python_v2`) protocol, so the plugin starts once and answers each keystroke from memory.
- **Zero External Dependencies:** Built using Python's standard library only, including the JSON-RPC layer.
- **Did You Mean?:** If nothing matches, the plugin suggests words one typo away (`kalwm` → **kalem**, `teşekür` → **teşekkür**).
- **Definitions in the Launcher:** When what you type is a whole word, its first meaning appears under the result (hover for more). These are fetched from the TDK API and cached; if you're offline, search still works and only the meanings are skipped.
- **Browser Integration:** Select a word and press `Enter` to open the word's definition page on the official TDK website.

## Usage

Activate Flow Launcher and type `tdk` followed by your query:

- `tdk kalem` -> Shows matching words starting with "kalem".
- Press `Enter` on a result to open its definition in your default browser.
- Press `Shift + Enter` (or right-click) to open the context menu: it lists every meaning of the word. Press `Enter` on a meaning to copy it, or copy the word itself.

## Under the Hood

To maintain a fast startup and low memory footprint (< 12MB RAM), the plugin avoids loading heavy JSON parsers or conducting linear scans:
- **Index:** A clean, pre-sorted newline-delimited wordlist (`data/tdk_words.txt`) compiled directly from official autocomplete dictionaries.
- **Lookup:** Python's built-in `bisect` module runs on a search key that applies Turkish casing and folds `çğıöşüâîû` and punctuation away, so the wordlist is sorted once at build time and every lookup is a binary search.

### Rebuilding the Wordlist
To fetch and update the word database from the official TDK api endpoint:
```bash
python scripts/build_wordlist.py
```
This script will download, sanitize, and sort the words in a format compatible with the binary search engine. Use `python scripts/build_wordlist.py --resort` to re-sort the existing file without downloading (needed after changing the search key).
