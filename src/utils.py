import re

_TURKISH_LOWER_MAP = str.maketrans("ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZÂÎÛ", "abcçdefgğhıijklmnoöprsştuüvyzâîû")
_ASCII_FOLD_MAP = str.maketrans("çğıöşüâîû", "cgiosuaiu")

_SANITIZE_PATTERN = re.compile(r'[\"\'()\[\]{}\d]')
_NON_WORD_PATTERN = re.compile(r'[^\w\s]|[\d_]')
_WHITESPACE_PATTERN = re.compile(r'\s+')


def turkish_lower(text):
    return text.translate(_TURKISH_LOWER_MAP)


def sanitize(query):
    cleaned = _SANITIZE_PATTERN.sub('', query)
    cleaned = _WHITESPACE_PATTERN.sub(' ', cleaned).strip()
    return cleaned


def normalize_query(query):
    return turkish_lower(sanitize(query))


def search_key(text):
    """Lowercase, fold Turkish/circumflex letters to ASCII and drop punctuation.

    "(bir şeye) Kulak vermek" -> "bir seye kulak vermek", "hâlâ" -> "hala".
    """
    folded = turkish_lower(text).translate(_ASCII_FOLD_MAP)
    folded = _NON_WORD_PATTERN.sub('', folded)
    return _WHITESPACE_PATTERN.sub(' ', folded).strip()


def wordlist_sort_key(word):
    # data/tdk_words.txt must be sorted with this key; SearchEngine bisects on search_key.
    return (search_key(word), turkish_lower(word), word)
