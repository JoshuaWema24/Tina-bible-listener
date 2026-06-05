# easyworship_controller/decision_engine.py
"""
Decision Engine
---------------
Receives raw transcript text and classifies it as:
  - VERSE    → detected Bible reference(s) to display
  - COMMAND  → slide/media control command
  - NOISE    → ignore

Also handles:
  - Debouncing (same verse within N seconds → ignore)
  - Correction detection ("I meant John 3:18" → override last verse)
  - Confidence gating
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

from loguru import logger

from bible_parser import BibleReference, BibleReferenceParser
from config.settings import EngineConfig


class IntentType(Enum):
    VERSE = auto()
    COMMAND = auto()
    NOISE = auto()


@dataclass
class SlideCommand:
    action: str       # "next", "previous", "go_live", "black_screen", "clear"
    raw_text: str = ""


@dataclass
class DecisionResult:
    intent: IntentType
    references: List[BibleReference] = field(default_factory=list)
    command: Optional[SlideCommand] = None
    is_correction: bool = False


# ---------------------------------------------------------------------------
# Slide command patterns
# ---------------------------------------------------------------------------

_COMMAND_PATTERNS: List[tuple[re.Pattern, str]] = [
    (re.compile(r'\b(next\s+slide|go\s+next|advance)\b', re.I), "next"),
    (re.compile(r'\b(previous\s+slide|go\s+back|back\s+slide)\b', re.I), "previous"),
    (re.compile(r'\b(go\s+live|show\s+live)\b', re.I), "go_live"),
    (re.compile(r'\b(black\s+screen|blank\s+screen|blackout)\b', re.I), "black_screen"),
    (re.compile(r'\b(clear\s+screen|clear\s+slide|clear)\b', re.I), "clear"),
]


def _detect_command(text: str) -> Optional[SlideCommand]:
    for pattern, action in _COMMAND_PATTERNS:
        if pattern.search(text):
            return SlideCommand(action=action, raw_text=text)
    return None


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class DecisionEngine:
    """
    Stateful engine — tracks recent verse history for debouncing.
    Thread-safe for single-producer (STT thread) usage.
    """

    def __init__(self, cfg: Optional[EngineConfig] = None) -> None:
        self._cfg = cfg or EngineConfig()
        self._parser = BibleReferenceParser()
        # {verse_key: timestamp} for debounce
        self._recent: dict[tuple, float] = {}

    def evaluate(self, text: str) -> DecisionResult:
        """Classify a transcript segment and return a DecisionResult."""

        # 1) Check for slide commands first
        cmd = _detect_command(text)
        if cmd:
            logger.info("Command detected: {}", cmd.action)
            return DecisionResult(intent=IntentType.COMMAND, command=cmd)

        # 2) Parse Bible references
        refs = self._parser.parse(text)
        if not refs:
            return DecisionResult(intent=IntentType.NOISE)

        # 3) Filter by confidence
        refs = [r for r in refs if r.confidence >= self._cfg.min_confidence]
        if not refs:
            logger.debug("References found but below confidence threshold")
            return DecisionResult(intent=IntentType.NOISE)

        # 4) Handle corrections — bypass debounce
        is_correction = any(r.is_correction for r in refs)
        if not is_correction:
            refs = self._apply_debounce(refs)

        if not refs:
            return DecisionResult(intent=IntentType.NOISE)

        # 5) Record in history
        now = time.monotonic()
        for ref in refs:
            self._recent[(ref.book, ref.chapter, ref.verse)] = now

        logger.info(
            "Verse(s) detected: {}{}",
            ", ".join(r.display for r in refs),
            " [CORRECTION]" if is_correction else "",
        )
        return DecisionResult(
            intent=IntentType.VERSE,
            references=refs,
            is_correction=is_correction,
        )

    def _apply_debounce(self, refs: List[BibleReference]) -> List[BibleReference]:
        now = time.monotonic()
        # Purge expired entries
        expired = [k for k, t in self._recent.items()
                   if now - t > self._cfg.debounce_seconds]
        for k in expired:
            del self._recent[k]

        kept = []
        for ref in refs:
            key = (ref.book, ref.chapter, ref.verse)
            last_seen = self._recent.get(key)
            if last_seen and (now - last_seen) < self._cfg.debounce_seconds:
                logger.debug(
                    "Debouncing {} (last seen {:.1f}s ago)",
                    ref.display,
                    now - last_seen,
                )
                continue
            kept.append(ref)
        return kept
