# bible_parser/bible_data.py
"""
Canonical Bible book data: standard names, aliases, ordinal prefixes,
and spoken-word variants.  The parser uses this as its lookup table.
"""

from typing import Dict, List, Tuple

# (canonical_name, chapter_count)  — used for validation
BIBLE_BOOKS: List[Tuple[str, int]] = [
    # Old Testament
    ("Genesis", 50), ("Exodus", 40), ("Leviticus", 27), ("Numbers", 36),
    ("Deuteronomy", 34), ("Joshua", 24), ("Judges", 21), ("Ruth", 4),
    ("1 Samuel", 31), ("2 Samuel", 24), ("1 Kings", 22), ("2 Kings", 25),
    ("1 Chronicles", 29), ("2 Chronicles", 36), ("Ezra", 10), ("Nehemiah", 13),
    ("Esther", 10), ("Job", 42), ("Psalms", 150), ("Proverbs", 31),
    ("Ecclesiastes", 12), ("Song of Solomon", 8), ("Isaiah", 66),
    ("Jeremiah", 52), ("Lamentations", 5), ("Ezekiel", 48), ("Daniel", 12),
    ("Hosea", 14), ("Joel", 3), ("Amos", 9), ("Obadiah", 1), ("Jonah", 4),
    ("Micah", 7), ("Nahum", 3), ("Habakkuk", 3), ("Zephaniah", 3),
    ("Haggai", 2), ("Zechariah", 14), ("Malachi", 4),
    # New Testament
    ("Matthew", 28), ("Mark", 16), ("Luke", 24), ("John", 21),
    ("Acts", 28), ("Romans", 16), ("1 Corinthians", 16), ("2 Corinthians", 13),
    ("Galatians", 6), ("Ephesians", 6), ("Philippians", 4), ("Colossians", 4),
    ("1 Thessalonians", 5), ("2 Thessalonians", 3), ("1 Timothy", 6),
    ("2 Timothy", 4), ("Titus", 3), ("Philemon", 1), ("Hebrews", 13),
    ("James", 5), ("1 Peter", 5), ("2 Peter", 3), ("1 John", 5),
    ("2 John", 1), ("3 John", 1), ("Jude", 1), ("Revelation", 22),
]

BOOK_CHAPTER_COUNT: Dict[str, int] = {b: c for b, c in BIBLE_BOOKS}
CANONICAL_BOOKS: List[str] = [b for b, _ in BIBLE_BOOKS]

# ---------------------------------------------------------------------------
# Alias table: maps every variant → canonical name
# ---------------------------------------------------------------------------
_ALIASES: List[Tuple[str, str]] = [
    # Abbreviations
    ("gen", "Genesis"), ("ex", "Exodus"), ("exo", "Exodus"),
    ("lev", "Leviticus"), ("num", "Numbers"), ("deut", "Deuteronomy"),
    ("deu", "Deuteronomy"), ("josh", "Joshua"), ("judg", "Judges"),
    ("jdg", "Judges"), ("sam", "1 Samuel"),
    ("1sam", "1 Samuel"), ("2sam", "2 Samuel"),
    ("1ki", "1 Kings"), ("2ki", "2 Kings"),
    ("1chr", "1 Chronicles"), ("2chr", "2 Chronicles"),
    ("neh", "Nehemiah"), ("est", "Esther"),
    ("ps", "Psalms"), ("psa", "Psalms"), ("pss", "Psalms"),
    ("prov", "Proverbs"), ("pro", "Proverbs"),
    ("eccl", "Ecclesiastes"), ("ecc", "Ecclesiastes"),
    ("sol", "Song of Solomon"), ("song", "Song of Solomon"),
    ("sos", "Song of Solomon"), ("ss", "Song of Solomon"),
    ("isa", "Isaiah"), ("jer", "Jeremiah"), ("lam", "Lamentations"),
    ("ezek", "Ezekiel"), ("eze", "Ezekiel"), ("dan", "Daniel"),
    ("hos", "Hosea"), ("zech", "Zechariah"), ("zec", "Zechariah"),
    ("mal", "Malachi"), ("hab", "Habakkuk"), ("zeph", "Zephaniah"),
    ("zep", "Zephaniah"), ("hag", "Haggai"), ("nah", "Nahum"),
    ("mic", "Micah"), ("obad", "Obadiah"),
    ("matt", "Matthew"), ("mat", "Matthew"), ("mk", "Mark"),
    ("lk", "Luke"), ("jn", "John"), ("joh", "John"),
    ("act", "Acts"), ("rom", "Romans"),
    ("1cor", "1 Corinthians"), ("2cor", "2 Corinthians"),
    ("1co", "1 Corinthians"), ("2co", "2 Corinthians"),
    ("gal", "Galatians"), ("eph", "Ephesians"),
    ("phil", "Philippians"), ("php", "Philippians"),
    ("col", "Colossians"), ("phm", "Philemon"),
    ("1thess", "1 Thessalonians"), ("2thess", "2 Thessalonians"),
    ("1th", "1 Thessalonians"), ("2th", "2 Thessalonians"),
    ("1tim", "1 Timothy"), ("2tim", "2 Timothy"),
    ("1ti", "1 Timothy"), ("2ti", "2 Timothy"),
    ("tit", "Titus"), ("heb", "Hebrews"),
    ("jas", "James"), ("jms", "James"),
    ("1pet", "1 Peter"), ("2pet", "2 Peter"),
    ("1pe", "1 Peter"), ("2pe", "2 Peter"),
    ("1jn", "1 John"), ("2jn", "2 John"), ("3jn", "3 John"),
    ("1jo", "1 John"), ("2jo", "2 John"), ("3jo", "3 John"),
    ("jude", "Jude"), ("rev", "Revelation"), ("apoc", "Revelation"),

    # Spoken / expanded variants
    ("first samuel", "1 Samuel"), ("second samuel", "2 Samuel"),
    ("first kings", "1 Kings"), ("second kings", "2 Kings"),
    ("first chronicles", "1 Chronicles"), ("second chronicles", "2 Chronicles"),
    ("first corinthians", "1 Corinthians"), ("second corinthians", "2 Corinthians"),
    ("first thessalonians", "1 Thessalonians"),
    ("second thessalonians", "2 Thessalonians"),
    ("first timothy", "1 Timothy"), ("second timothy", "2 Timothy"),
    ("first peter", "1 Peter"), ("second peter", "2 Peter"),
    ("first john", "1 John"), ("second john", "2 John"), ("third john", "3 John"),
    ("song of songs", "Song of Solomon"),
    ("psalms", "Psalms"), ("psalm", "Psalms"),
    ("proverb", "Proverbs"),
]

ALIAS_MAP: Dict[str, str] = {}
for alias, canonical in _ALIASES:
    ALIAS_MAP[alias.lower()] = canonical
# Also add every canonical name lowercased → itself
for book in CANONICAL_BOOKS:
    ALIAS_MAP[book.lower()] = book

# ---------------------------------------------------------------------------
# Spoken number words → integer
# ---------------------------------------------------------------------------
SPOKEN_NUMBERS: Dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100, "thousand": 1000,
    # Ordinals
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
    "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
    "nineteenth": 19, "twentieth": 20, "thirtieth": 30, "fortieth": 40,
    "fiftieth": 50,
    # Ordinal compounds handled in parser
}
