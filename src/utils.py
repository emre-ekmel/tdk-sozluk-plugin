import re

_TURKISH_LOWER_MAP = str.maketrans("ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ", "abcçdefgğhıijklmnoöprsştuüvyz")

_SANITIZE_PATTERN = re.compile(r'[\"\'()\[\]{}\d]')
_WHITESPACE_PATTERN = re.compile(r'\s+')


def turkish_lower(text):
    return text.translate(_TURKISH_LOWER_MAP)


def sanitize(query):
    cleaned = _SANITIZE_PATTERN.sub('', query)
    cleaned = _WHITESPACE_PATTERN.sub(' ', cleaned).strip()
    return cleaned


def normalize_query(query):
    return turkish_lower(sanitize(query))
