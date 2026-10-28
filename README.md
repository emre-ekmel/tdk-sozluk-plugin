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

## Installation

### Via Flow Launcher (Direct)
Open Flow Launcher, type `pm install`, and paste the release URL:
```cmd
pm install https://github.com/emre-ekmel/tdk-sozluk-plugin/releases/download/v2.0.0/Flow.Launcher.Plugin.TDKSozluk.zip
```

### Manual Installation
1. Download the latest release `.zip` file from the [releases](https://github.com/emre-ekmel/tdk-sozluk-plugin/releases) page.
2. Extract the archive into your Flow Launcher plugins folder (typically `%APPDATA%\FlowLauncher\Plugins`).
3. Restart Flow Launcher.

## Usage

Activate Flow Launcher and type `tdk` followed by your query:

- `tdk kalem` -> Shows matching words starting with "kalem".
- Press `Enter` on a result to open its definition in your default browser.
- Press `Shift + Enter` (or right-click) to open the context menu: it lists every meaning of the word. Press `Enter` on a meaning to copy it, or copy the word itself.

## Under the Hood

To maintain a fast startup and low memory footprint (< 12MB RAM), the plugin avoids loading heavy JSON parsers or conducting linear scans:
- **Index:** A clean, pre-sorted newline-delimited wordlist (`data/tdk_words.txt`) compiled directly from official autocomplete dictionaries.
- **Lookup:** Python's built-in `bisect` module is paired with a custom Turkish casing translator, ensuring exact alphabetical binary search index lookups at runtime.

## Development

If you want to contribute or build/test the plugin locally:

### Prerequisites
- Python 3.12+

### Set Up & Run Tests
The plugin has no runtime dependencies; only `pytest` is needed for tests:
```bash
pip install pytest
pytest
```

### Talking to the Plugin by Hand
The plugin reads one JSON-RPC 2.0 request per line on stdin and writes responses to stdout:
```bash
printf '%s
' '{"jsonrpc":"2.0","id":1,"method":"query","params":[{"search":"sisman"},{}]}'   '{"jsonrpc":"2.0","id":2,"method":"close","params":[]}' | python main.py
```

### Rebuilding the Wordlist
To fetch and update the word database from the official TDK api endpoint:
```bash
python scripts/build_wordlist.py
```
This script will download, sanitize, and sort the words in a format compatible with the binary search engine. Use `python scripts/build_wordlist.py --resort` to re-sort the existing file without downloading (needed after changing the search key).
