"""
TDK kelime listesi indirme ve sıralama scripti.

Kaynak:  https://sozluk.gov.tr/autocomplete.json
Çıktı:   data/tdk_words.txt (sıralı, tekrarsız, satır-bazlı metin dosyası)

Sıralama, engine.py'nin bisect ile kullandığı turkish_lower() + Python
default string comparison ile birebir eşleşmelidir.
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils import turkish_lower

AUTOCOMPLETE_URL = "https://sozluk.gov.tr/autocomplete.json"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "tdk_words.txt")


def main():
    print(f"[1/4] İndiriliyor: {AUTOCOMPLETE_URL}")
    req = urllib.request.Request(AUTOCOMPLETE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw_data = json.loads(resp.read().decode("utf-8"))

    print(f"[2/4] Ham veri: {len(raw_data)} madde")

    words = {item.get("madde", "").strip() for item in raw_data if item.get("madde", "").strip()}

    print(f"[3/4] Tekrarsız kelime sayısı: {len(words)}")

    sorted_words = sorted(words, key=turkish_lower)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(sorted_words))

    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"[4/4] Yazıldı: {OUTPUT_FILE}")
    print(f"       Kelime sayısı: {len(sorted_words)}")
    print(f"       Dosya boyutu: {file_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
