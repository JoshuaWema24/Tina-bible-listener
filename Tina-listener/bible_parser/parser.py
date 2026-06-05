# bible_parser/parser.py
"""
Bible Reference Detection Engine
---------------------------------
Hybrid regex + fuzzy-match approach that handles:
  • Standard written format:   "John 3:16"
  • Spoken numeric:            "John three sixteen" / "John chapter 3 verse 16"
  • Spoken ordinal prefixes:   "First Corinthians 13:4"
  • Corrections:               "sorry I meant John 3:18"
  • Psalm/Psalms variants:     "Psalm 23 verse 1"

Returns BibleReference dataclasses with a confidence score.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from rapidfuzz import process, fuzz

from .bible_data import (
    ALIAS_MAP,
    CANONICAL_BOOKS,
    BOOK_CHAPTER_COUNT,
    SPOKEN_NUMBERS,
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class BibleReference:
    book: str           # Canonical book name, e.g. "1 Corinthians"
    chapter: int
    verse: int
    verse_end: Optional[int] = None   # For ranges: "John 3:16-17"
    confidence: float = 1.0
    raw_text: str = ""
    is_correction: bool = False       # "I meant X"

    @property
    def display(self) -> str:
        ref = f"{self.book} {self.chapter}:{self.verse}"
        if self.verse_end:
            ref += f"-{self.verse_end}"
        return ref

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BibleReference):
            return False
        return (self.book == other.book
                and self.chapter == other.chapter
                and self.verse == other.verse)

    def __hash__(self) -> int:
        return hash((self.book, self.chapter, self.verse))


# ---------------------------------------------------------------------------
# Number word conversion helpers
# ---------------------------------------------------------------------------

_ORDINAL_PREFIX_RE = re.compile(
    r'\b(first|second|third|1st|2nd|3rd)\b', re.IGNORECASE
)
_ORDINAL_MAP = {"first": "1", "second": "2", "third": "3",
                "1st": "1", "2nd": "2", "3rd": "3"}


def _spoken_words_to_int(text: str) -> Optional[int]:
    """Convert a sequence of number words to an integer, e.g. 'twenty three' → 23."""
    tokens = text.lower().split()
    total = 0
    current = 0
    for token in tokens:
        val = SPOKEN_NUMBERS.get(token)
        if val is None:
            return None
        if val == 100:
            current = current * 100 if current else 100
        elif val == 1000:
            total += current * 1000
            current = 0
        else:
            current += val
    return total + current


def _parse_number_token(token: str) -> Optional[int]:
    """Parse a single token that could be a digit string or a number word."""
    token = token.strip()
    if token.isdigit():
        return int(token)
    return _spoken_words_to_int(token)


# ---------------------------------------------------------------------------
# Book name resolver
# ---------------------------------------------------------------------------

def _resolve_book(raw: str) -> Tuple[Optional[str], float]:
    """
    Resolve a raw book string to a canonical name.
    Returns (canonical_name, confidence) or (None, 0.0).
    """
    cleaned = raw.strip().lower()
    # 1) Exact alias match
    if cleaned in ALIAS_MAP:
        return ALIAS_MAP[cleaned], 1.0

    # 2) Fuzzy match against the alias keys
    match = process.extractOne(
        cleaned,
        ALIAS_MAP.keys(),
        scorer=fuzz.token_sort_ratio,
        score_cutoff=78,
    )
    if match:
        matched_alias, score, _ = match
        return ALIAS_MAP[matched_alias], score / 100.0

    # 3) Fuzzy match directly against canonical names
    match2 = process.extractOne(
        raw.strip(),
        CANONICAL_BOOKS,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=75,
    )
    if match2:
        canonical, score, _ = match2
        return canonical, score / 100.0

    return None, 0.0


# ---------------------------------------------------------------------------
# Main Parser
# ---------------------------------------------------------------------------

# Matches ordinal-prefixed book names: "First Corinthians", "1st John"
_ORDINAL_BOOK_RE = re.compile(
    r'\b(first|second|third|1st|2nd|3rd)\s+(\w+)', re.IGNORECASE
)

# Standard numeric reference: "John 3:16" or "John 3:16-18"
_NUMERIC_REF_RE = re.compile(
    r'(?P<book>[1-3]?\s*[A-Za-z][\w\s]{1,24}?)'
    r'\s+(?P<chapter>\d{1,3})\s*[:\s]\s*(?P<verse>\d{1,3})'
    r'(?:\s*[-–]\s*(?P<verse_end>\d{1,3}))?',
    re.IGNORECASE,
)

# Spoken format: "John chapter three verse sixteen"
_SPOKEN_REF_RE = re.compile(
    r'(?P<book>[1-3]?\s*[A-Za-z][\w\s]{1,24}?)\s+'
    r'(?:chapter\s+)?(?P<chapter_words>[\w\s-]{1,30}?)\s+'
    r'(?:verse\s+)(?P<verse_words>[\w\s-]{1,20})',
    re.IGNORECASE,
)

# Correction phrases
_CORRECTION_RE = re.compile(
    r'\b(?:sorry|i\s+meant|actually|correction|no\s+wait|i\s+mean)\b',
    re.IGNORECASE,
)


class BibleReferenceParser:
    """
    Stateless parser.  Call parse(text) to get a list of references.
    """

    def parse(self, text: str) -> List[BibleReference]:
        """Parse text and return all detected BibleReferences, sorted by confidence."""
        is_correction = bool(_CORRECTION_RE.search(text))

        # Pre-process: normalise ordinal prefixes
        normalised = self._normalise_ordinals(text)

        results: List[BibleReference] = []

        # Strategy 1: standard numeric "Book N:N"
        results.extend(self._parse_numeric(normalised, text, is_correction))

        # Strategy 2: spoken "Book chapter N verse N"
        if not results:
            results.extend(self._parse_spoken(normalised, text, is_correction))

        # Deduplicate (same reference appearing from both strategies)
        seen = set()
        unique = []
        for ref in sorted(results, key=lambda r: -r.confidence):
            key = (ref.book, ref.chapter, ref.verse)
            if key not in seen:
                seen.add(key)
                unique.append(ref)

        return unique

    # ------------------------------------------------------------------
    # Internal strategies
    # ------------------------------------------------------------------

    def _normalise_ordinals(self, text: str) -> str:
        """Replace 'first/second/third' book prefixes with '1/2/3'."""
        def replacer(m: re.Match) -> str:
            num = _ORDINAL_MAP[m.group(1).lower()]
            return f"{num} {m.group(2)}"
        return _ORDINAL_BOOK_RE.sub(replacer, text)

    def _parse_numeric(
        self, text: str, raw_text: str, is_correction: bool
    ) -> List[BibleReference]:
        refs = []
        for m in _NUMERIC_REF_RE.finditer(text):
            book_raw = m.group("book").strip()
            chapter = int(m.group("chapter"))
            verse = int(m.group("verse"))
            verse_end_str = m.group("verse_end")
            verse_end = int(verse_end_str) if verse_end_str else None

            canonical, conf = _resolve_book(book_raw)
            if canonical is None or conf < 0.65:
                continue
            if not self._validate(canonical, chapter, verse):
                continue

            refs.append(BibleReference(
                book=canonical,
                chapter=chapter,
                verse=verse,
                verse_end=verse_end,
                confidence=conf,
                raw_text=m.group(0),
                is_correction=is_correction,
            ))
        return refs

    def _parse_spoken(
        self, text: str, raw_text: str, is_correction: bool
    ) -> List[BibleReference]:
        refs = []
        for m in _SPOKEN_REF_RE.finditer(text):
            book_raw = m.group("book").strip()
            chapter_words = m.group("chapter_words").strip()
            verse_words = m.group("verse_words").strip()

            chapter = _parse_number_token(chapter_words)
            verse = _parse_number_token(verse_words)
            if chapter is None or verse is None:
                continue

            canonical, conf = _resolve_book(book_raw)
            if canonical is None or conf < 0.65:
                continue
            if not self._validate(canonical, chapter, verse):
                continue

            refs.append(BibleReference(
                book=canonical,
                chapter=chapter,
                verse=verse,
                confidence=conf * 0.95,   # slight penalty for spoken path
                raw_text=m.group(0),
                is_correction=is_correction,
            ))
        return refs

    @staticmethod
    def _validate(book: str, chapter: int, verse: int) -> bool:
        """Sanity-check that chapter/verse are plausible."""
        max_chapters = BOOK_CHAPTER_COUNT.get(book, 150)
        if chapter < 1 or chapter > max_chapters:
            return False
        if verse < 1 or verse > 176:   # Psalm 119 has 176 verses
            return False
        return True
