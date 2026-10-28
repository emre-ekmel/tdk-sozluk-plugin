import os

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TDK_BROWSER_URL = "https://sozluk.gov.tr/?ara={word}"

MAX_RESULTS = 10

DATA_FILE = os.path.join(PLUGIN_DIR, "data", "tdk_words.txt")

PLUGIN_ICON = os.path.join(PLUGIN_DIR, "images", "icon.png")

TDK_API_URL = "https://sozluk.gov.tr/gts?ara={word}"

# How long a query may wait for definitions of its top matches before returning without them.
# TDK answers in ~150-250 ms on a warm connection; exact-word keystrokes may wait this long once per word.
DEFINITION_WAIT = 0.4

# How long the context menu may wait for definitions; Flow blocks its UI while loading it.
CONTEXT_MENU_WAIT = 1.5
