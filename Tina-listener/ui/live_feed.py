"""
ui/live_feed.py
Scrolling real-time transcript widget for the Live Feed tab.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat, QFont


MAX_LINES = 200   # keep at most this many lines in the widget

# Colour palette matching styles.py
_COL_VERSE   = "#c9a84c"    # gold — verse hits
_COL_COMMAND = "#4a9ecf"    # blue — commands
_COL_NOISE   = "#3a3a4a"    # dim grey — noise/ignored
_COL_NORMAL  = "#b0a898"    # regular transcript
_COL_TIMESTAMP = "#4a4a5a"  # dim timestamp
_COL_CORRECT = "#e2885a"    # orange — corrections


class LiveFeedWidget(QWidget):
    """
    Scrolling transcript display.

    Call append_transcript() for plain speech lines.
    Call highlight_verse() or highlight_command() to colour
    the *most recent* matching line in the feed.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("liveFeedWidget")
        self._line_count = 0
        self._last_verse_cursor_pos: Optional[int] = None
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._flash_done)
        self._flash_state = False
        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header row
        header = QHBoxLayout()
        title = QLabel("LIVE TRANSCRIPT")
        title.setStyleSheet(
            "color: #8a8a9a; font-size: 10px; font-weight: 700; letter-spacing: 2px;"
        )
        header.addWidget(title)
        header.addStretch()

        self._status_label = QLabel("● LISTENING")
        self._status_label.setStyleSheet(
            "color: #4caf7d; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )
        self._status_label.hide()
        header.addWidget(self._status_label)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(24)
        clear_btn.setFixedWidth(56)
        clear_btn.setStyleSheet(
            "font-size: 11px; padding: 2px 8px; color: #8a8a9a;"
            "background: #12121a; border: 1px solid #1e1e2e; border-radius: 4px;"
        )
        clear_btn.clicked.connect(self._clear)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        # Legend
        legend = QHBoxLayout()
        legend.setSpacing(16)
        for label_text, color in [
            ("■ Verse", _COL_VERSE),
            ("■ Command", _COL_COMMAND),
            ("■ Correction", _COL_CORRECT),
            ("■ Ignored", _COL_NOISE),
        ]:
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {color}; font-size: 10px;")
            legend.addWidget(lbl)
        legend.addStretch()
        layout.addLayout(legend)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color: #1e1e2e; background: #1e1e2e; max-height: 1px;")
        layout.addWidget(div)

        # Transcript display
        self._view = QTextEdit()
        self._view.setObjectName("transcriptView")
        self._view.setReadOnly(True)
        self._view.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Use a fixed-pitch font for alignment
        font = QFont("Consolas", 12)
        self._view.setFont(font)
        layout.addWidget(self._view, stretch=1)

        # Idle hint
        self._idle_hint = QLabel("Waiting for audio input…")
        self._idle_hint.setStyleSheet(
            "color: #2a2a3a; font-size: 13px; font-style: italic;"
        )
        self._idle_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._idle_hint)
        self._idle_hint.hide()

    # ── Public API ─────────────────────────────────────────────────────────

    @pyqtSlot(str, str)
    def append_transcript(self, text: str, timestamp: str) -> None:
        """Add a regular transcript line."""
        self._maybe_trim()
        self._idle_hint.hide()
        self._append_line(timestamp, text, _COL_NORMAL, _COL_TIMESTAMP)
        self._scroll_to_bottom()
        self._line_count += 1

    @pyqtSlot(str, float, bool)
    def highlight_verse(self, ref_display: str, confidence: float, is_correction: bool) -> None:
        """Append a special verse-detected line."""
        self._maybe_trim()
        ts = datetime.now().strftime("%H:%M:%S")
        color = _COL_CORRECT if is_correction else _COL_VERSE
        prefix = "⟳ CORRECTION" if is_correction else "📖 VERSE"
        line = f"{prefix}  {ref_display}  ({confidence:.0%})"
        self._append_line(ts, line, color, _COL_TIMESTAMP, bold=True)
        self._scroll_to_bottom()
        self._line_count += 1
        self._start_flash()

    @pyqtSlot(str)
    def highlight_command(self, action: str) -> None:
        """Append a command-detected line."""
        self._maybe_trim()
        ts = datetime.now().strftime("%H:%M:%S")
        self._append_line(ts, f"⌘  COMMAND: {action}", _COL_COMMAND, _COL_TIMESTAMP, bold=True)
        self._scroll_to_bottom()
        self._line_count += 1

    def set_listening(self, active: bool) -> None:
        if active:
            self._status_label.setText("● LISTENING")
            self._status_label.setStyleSheet(
                "color: #4caf7d; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
            )
            self._status_label.show()
        else:
            self._status_label.setText("◉ STOPPED")
            self._status_label.setStyleSheet(
                "color: #8a8a9a; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
            )

    def show_idle(self) -> None:
        self._idle_hint.show()

    # ── Internal helpers ───────────────────────────────────────────────────

    def _append_line(
        self,
        timestamp: str,
        text: str,
        text_color: str,
        ts_color: str,
        bold: bool = False,
    ) -> None:
        cursor = self._view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Timestamp
        ts_fmt = QTextCharFormat()
        ts_fmt.setForeground(QColor(ts_color))
        ts_fmt.setFontFamily("Consolas")
        ts_fmt.setFontPointSize(11)
        cursor.insertText(timestamp, ts_fmt)

        # Spacer
        spacer_fmt = QTextCharFormat()
        spacer_fmt.setForeground(QColor("#1e1e2e"))
        spacer_fmt.setFontFamily("Consolas")
        spacer_fmt.setFontPointSize(11)
        cursor.insertText("  │  ", spacer_fmt)

        # Main text
        txt_fmt = QTextCharFormat()
        txt_fmt.setForeground(QColor(text_color))
        txt_fmt.setFontFamily("Consolas")
        txt_fmt.setFontPointSize(12)
        if bold:
            txt_fmt.setFontWeight(QFont.Weight.Bold)
        cursor.insertText(text, txt_fmt)

        # Newline
        nl_fmt = QTextCharFormat()
        cursor.insertText("\n", nl_fmt)

    def _scroll_to_bottom(self) -> None:
        sb = self._view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _maybe_trim(self) -> None:
        """Remove oldest lines if we exceed MAX_LINES."""
        if self._line_count >= MAX_LINES:
            cursor = self._view.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(
                QTextCursor.MoveOperation.Down,
                QTextCursor.MoveMode.KeepAnchor,
                MAX_LINES // 4,
            )
            cursor.removeSelectedText()
            self._line_count -= MAX_LINES // 4

    def _clear(self) -> None:
        self._view.clear()
        self._line_count = 0
        self._idle_hint.show()

    def _start_flash(self) -> None:
        """Flash the background briefly to draw attention."""
        self._flash_state = True
        self._view.setStyleSheet(
            "QTextEdit#transcriptView { background-color: #1a160a; }"
        )
        self._flash_timer.start(250)

    def _flash_done(self) -> None:
        self._flash_state = False
        self._view.setStyleSheet("")   # revert to main stylesheet
