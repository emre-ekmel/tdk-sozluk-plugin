"""
TDK kelime listesi indirme ve sıralama scripti.

Kaynak:  https://sozluk.gov.tr/autocomplete.json
Çıktı:   data/tdk_words.txt (sıralı, tekrarsız, satır-bazlı metin dosyası)

Sıralama, engine.py'nin bisect ile kullandığı search_key() ile uyumlu olmalıdır;
bu yüzden src.utils.wordlist_sort_key kullanılır.

Kullanım:
    python scripts/build_wordlist.py           # indir + sırala
    python scripts/build_wordlist.py --resort  # mevcut dosyayı indirmeden yeniden sırala
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils import wordlist_sort_key

AUTOCOMPLETE_URL = "https://sozluk.gov.tr/autocomplete.json"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "tdk_words.txt")


def download_words():
    print(f"[1/4] İndiriliyor: {AUTOCOMPLETE_URL}")
    req = urllib.request.Request(AUTOCOMPLETE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw_data = json.loads(resp.read().decode("utf-8"))

    print(f"[2/4] Ham veri: {len(raw_data)} madde")
    return {item.get("madde", "").strip() for item in raw_data if item.get("madde", "").strip()}


def read_existing_words():
    print(f"[1/4] Mevcut dosya okunuyor: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        words = {w.strip() for w in f.read().splitlines() if w.strip()}
    print(f"[2/4] Mevcut kelime sayısı: {len(words)}")
    return words


def main():
    words = read_existing_words() if "--resort" in sys.argv[1:] else download_words()

    print(f"[3/4] Tekrarsız kelime sayısı: {len(words)}")

    sorted_words = sorted(words, key=wordlist_sort_key)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(sorted_words))

    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"[4/4] Yazıldı: {OUTPUT_FILE}")
    print(f"       Kelime sayısı: {len(sorted_words)}")
    print(f"       Dosya boyutu: {file_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
