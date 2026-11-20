"""Comparing place names across providers and the world dataset. Pure: no database, no network."""

import re
import unicodedata

# Letters that NFKD does not split into a base letter and an accent.
_TRANSLITERATION = str.maketrans({
    'ø': 'o', 'Ø': 'o', 'æ': 'ae', 'Æ': 'ae', 'œ': 'oe', 'Œ': 'oe', 'ß': 'ss',
    'ð': 'd', 'Ð': 'd', 'þ': 'th', 'Þ': 'th', 'ł': 'l', 'Ł': 'l', 'đ': 'd', 'Đ': 'd', 'ı': 'i',
})

# Words that describe the kind of division, which providers add or leave out ("Saint Peter Parish").
_GENERIC_WORDS = re.compile(
    r"\b(parish|district|county|province|region|municipality|canton|commune|prefecture|governorate|"
    r"division|state|city of|town of|the|la|le|atoll|islands?|village|sar|s\.a\.r\.)\b",
    re.IGNORECASE,
)
_ALTERNATIVE_SEPARATORS = re.compile(r"\s*/\s*|\s*[()]\s*|\s*,\s*|\s+and\s+")


def normalize_name(value):
    """
    A comparison key for a name: lowercase letters and digits only, accents and ligatures folded.

    A name with no Latin letters (Cyrillic, Arabic, CJK) keeps its own letters rather than
    becoming an empty key, which would match every other such name.
    """
    text = str(value)
    folded = unicodedata.normalize('NFKD', text.translate(_TRANSLITERATION))
    key = re.sub(r'[^a-z0-9]', '', folded.encode('ascii', 'ignore').decode('ascii').lower())
    if key:
        return key
    return re.sub(r'[\W_]+', '', unicodedata.normalize('NFKC', text).casefold())


def name_keys(value, alternatives=True):
    """
    Every comparison key a name can be known by.

    Covers the name as written, without generic division words, and "Saint" written as "St".
    With ``alternatives``, each side of "A / B", "A (B)", "A, B" and "A and B" counts too.
    Empty keys are left out.
    """
    if value is None:
        return set()
    text = str(value).strip()
    keys = set()
    for part in [text, *(_ALTERNATIVE_SEPARATORS.split(text) if alternatives else [])]:
        part = part.strip()
        for candidate in (part, _GENERIC_WORDS.sub(' ', part)):
            key = normalize_name(candidate)
            if key:
                keys.add(key)
                keys.add(re.sub(r'^saint', 'st', key))
    return keys


def name_words(value):
    """The distinctive words of a name, for telling whether two names share one."""
    stop = {'and', 'of', 'the', 'island', 'islands', 'saint', 'st', 'republic'}
    words = {normalize_name(word) for word in re.split(r'[^\w]+', str(value or ''))}
    return {word for word in words if word and word not in stop}
