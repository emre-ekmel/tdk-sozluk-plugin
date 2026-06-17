# Flow Launcher TDK Sözlük Plugin

An offline-first Flow Launcher plugin for looking up Turkish words in the Turkish Language Association (TDK) dictionary instantly.

## Features

- **Offline-First:** All search matching is performed locally against a pre-compiled database of ~98,000 words. No internet required for searching.
- **Sub-1ms Lookups:** Uses binary search (`bisect`) for prefix matching, achieving O(log N) lookup times.
- **Turkish Character Support:** Correctly handles Turkish-specific casing (e.g. `I`/`ı` and `İ`/`i` transitions) and character normalization during searches.
- **Zero External Dependencies:** Built using Python's standard library for minimal resource consumption and fast startup.
- **Browser Integration:** Select a word and press `Enter` to open the word's definition page on the official TDK website.

## Usage

Activate Flow Launcher and type `tdk` followed by your query:

- `tdk kalem` -> Shows matching words starting with "kalem".
- Press `Enter` on a result to open its definition in your default browser.
- Press `Shift + Enter` (or right-click) to open the context menu.

## Under the Hood

To maintain a fast startup and low memory footprint (< 12MB RAM), the plugin avoids loading heavy JSON parsers or conducting linear scans:
- **Index:** A clean, pre-sorted newline-delimited wordlist (`data/tdk_words.txt`) compiled directly from official autocomplete dictionaries.
- **Lookup:** Python's built-in `bisect` module is paired with a custom Turkish casing translator, ensuring exact alphabetical binary search index lookups at runtime.

### Rebuilding the Wordlist
To fetch and update the word database from the official TDK api endpoint:
```bash
python scripts/build_wordlist.py
```
This script will download, sanitize, and sort the words in a format compatible with the binary search engine.
