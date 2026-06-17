import os

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TDK_BROWSER_URL = "https://sozluk.gov.tr/?ara={word}"

MAX_RESULTS = 10

DATA_FILE = os.path.join(PLUGIN_DIR, "data", "tdk_words.txt")

PLUGIN_ICON = os.path.join(PLUGIN_DIR, "images", "icon.png")
