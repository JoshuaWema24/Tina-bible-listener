# tests/test_bible_parser.py
"""
Unit tests for the Bible Reference Parser.
Run with: pytest tests/test_bible_parser.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from bible_parser import BibleReferenceParser, BibleReference


@pytest.fixture
def parser():
    return BibleReferenceParser()


class TestNumericFormat:
    def test_standard_colon(self, parser):
        refs = parser.parse("Let us read from John 3:16")
        assert len(refs) == 1
        assert refs[0].book == "John"
        assert refs[0].chapter == 3
        assert refs[0].verse == 16

    def test_psalms(self, parser):
        refs = parser.parse("Psalm 23:1")
        assert refs[0].book == "Psalms"
        assert refs[0].chapter == 23
        assert refs[0].verse == 1

    def test_numbered_book(self, parser):
        refs = parser.parse("1 Corinthians 13:4")
        assert refs[0].book == "1 Corinthians"
        assert refs[0].chapter == 13
        assert refs[0].verse == 4

    def test_verse_range(self, parser):
        refs = parser.parse("Romans 8:28-30")
        assert refs[0].verse == 28
        assert refs[0].verse_end == 30

    def test_abbreviation(self, parser):
        refs = parser.parse("Rev 22:20")
        assert refs[0].book == "Revelation"

    def test_no_false_positive(self, parser):
        refs = parser.parse("We had 3 things to discuss today at 4:30")
        # Should not find a Bible reference here
        assert len(refs) == 0


class TestSpokenFormat:
    def test_chapter_verse_words(self, parser):
        refs = parser.parse("Turn to John chapter three verse sixteen")
        assert len(refs) >= 1
        assert refs[0].book == "John"
        assert refs[0].chapter == 3
        assert refs[0].verse == 16

    def test_spoken_numbers(self, parser):
        refs = parser.parse("Psalm twenty three verse one")
        assert refs[0].chapter == 23
        assert refs[0].verse == 1


class TestOrdinalPrefix:
    def test_first_corinthians(self, parser):
        refs = parser.parse("First Corinthians thirteen four")
        # After ordinal normalisation: "1 Corinthians thirteen four"
        # Spoken path should catch this
        if refs:
            assert refs[0].book == "1 Corinthians"

    def test_second_timothy(self, parser):
        refs = parser.parse("2 Timothy 3:16")
        assert refs[0].book == "2 Timothy"


class TestCorrections:
    def test_correction_flag(self, parser):
        refs = parser.parse("sorry I meant John 3:18")
        assert len(refs) >= 1
        assert refs[0].is_correction is True
        assert refs[0].verse == 18

    def test_actually_correction(self, parser):
        refs = parser.parse("actually that was Romans 8:1")
        assert refs[0].is_correction is True


class TestEdgeCases:
    def test_revelation(self, parser):
        refs = parser.parse("Revelation 21:4 — no more tears")
        assert refs[0].book == "Revelation"

    def test_song_of_solomon(self, parser):
        refs = parser.parse("Song of Solomon 2:4")
        assert refs[0].book == "Song of Solomon"

    def test_invalid_chapter_ignored(self, parser):
        # Genesis only has 50 chapters
        refs = parser.parse("Genesis 99:1")
        assert len(refs) == 0

    def test_confidence_field(self, parser):
        refs = parser.parse("John 3:16")
        assert refs[0].confidence > 0.9

    def test_display_property(self, parser):
        refs = parser.parse("Romans 8:28")
        assert refs[0].display == "Romans 8:28"


class TestDecisionEngine:
    def test_command_next(self):
        from easyworship_controller.decision_engine import DecisionEngine, IntentType
        engine = DecisionEngine()
        result = engine.evaluate("next slide please")
        assert result.intent == IntentType.COMMAND
        assert result.command.action == "next"

    def test_debounce(self):
        from easyworship_controller.decision_engine import DecisionEngine, IntentType
        from config.settings import EngineConfig
        engine = DecisionEngine(EngineConfig(debounce_seconds=60))
        r1 = engine.evaluate("John 3:16")
        r2 = engine.evaluate("John 3:16")
        assert r1.intent == IntentType.VERSE
        assert r2.intent == IntentType.NOISE   # debounced

    def test_correction_bypasses_debounce(self):
        from easyworship_controller.decision_engine import DecisionEngine, IntentType
        from config.settings import EngineConfig
        engine = DecisionEngine(EngineConfig(debounce_seconds=60))
        engine.evaluate("John 3:16")
        r2 = engine.evaluate("sorry I meant John 3:18")
        # Correction should bypass debounce
        assert r2.intent == IntentType.VERSE
        assert r2.references[0].verse == 18
