"""
ui/verse_history.py
Real-time verse detection history table widget.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Tuple

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QAbstractItemView,
    QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QFont


# Column indices
COL_TIME       = 0
COL_REFERENCE  = 1
COL_CONFIDENCE = 2
COL_STATUS     = 3
COL_ACTION     = 4

STATUS_COLORS = {
    "ew_success":       ("#4caf7d", "Displayed"),
    "overlay_fallback": ("#c9a84c", "Overlay"),
    "failed":           ("#e05555", "Failed"),
    "pending":          ("#8a8a9a", "Pending"),
    "correction":       ("#e2885a", "Correction"),
}


class VerseHistoryWidget(QWidget):
    """
    Table showing every verse detected in the current session,
    with real-time status updates and per-row resend action.
    """

    resend_requested = pyqtSignal(str)    # emits ref_display

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._rows: List[Tuple[str, str]] = []   # (ref_display, timestamp)
        self._resend_workers = []
        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header row
        header = QHBoxLayout()
        title = QLabel("VERSE DETECTION HISTORY")
        title.setStyleSheet(
            "color: #8a8a9a; font-size: 10px; font-weight: 700; letter-spacing: 2px;"
        )
        header.addWidget(title)
        header.addStretch()

        self._count_label = QLabel("0 verses")
        self._count_label.setStyleSheet("color: #4a4a5a; font-size: 11px;")
        header.addWidget(self._count_label)

        clear_btn = QPushButton("Clear History")
        clear_btn.setObjectName("dangerButton")
        clear_btn.setFixedHeight(28)
        clear_btn.clicked.connect(self._clear_history)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color: #1e1e2e; background: #1e1e2e; max-height: 1px;")
        layout.addWidget(div)

        # Table
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "TIME", "REFERENCE", "CONFIDENCE", "STATUS", "ACTION"
        ])
        self._table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Column sizing
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(COL_TIME,       QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_REFERENCE,  QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(COL_CONFIDENCE, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_STATUS,     QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_ACTION,     QHeaderView.ResizeMode.ResizeToContents)

        self._table.setRowHeight(0, 36)
        layout.addWidget(self._table, stretch=1)

        # Summary bar
        summary = QHBoxLayout()
        self._success_label = QLabel("✓ Displayed: 0")
        self._success_label.setStyleSheet("color: #4caf7d; font-size: 11px;")
        self._fallback_label = QLabel("◈ Overlay: 0")
        self._fallback_label.setStyleSheet("color: #c9a84c; font-size: 11px;")
        self._failed_label = QLabel("✗ Failed: 0")
        self._failed_label.setStyleSheet("color: #e05555; font-size: 11px;")

        summary.addWidget(self._success_label)
        summary.addSpacing(16)
        summary.addWidget(self._fallback_label)
        summary.addSpacing(16)
        summary.addWidget(self._failed_label)
        summary.addStretch()
        layout.addLayout(summary)

        self._counts = {"ew_success": 0, "overlay_fallback": 0, "failed": 0}

    # ── Public API ─────────────────────────────────────────────────────────

    @pyqtSlot(str, float, bool)
    def add_verse(self, ref_display: str, confidence: float, is_correction: bool) -> None:
        """Add a newly detected verse (status = pending)."""
        ts = datetime.now().strftime("%H:%M:%S")
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setRowHeight(row, 36)

        # Time
        time_item = QTableWidgetItem(ts)
        time_item.setForeground(QColor("#4a4a5a"))
        time_item.setFont(QFont("Consolas", 11))
        self._table.setItem(row, COL_TIME, time_item)

        # Reference
        ref_text = ("⟳ " if is_correction else "") + ref_display
        ref_item = QTableWidgetItem(ref_text)
        ref_item.setForeground(QColor("#e2885a" if is_correction else "#c9a84c"))
        ref_item.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self._table.setItem(row, COL_REFERENCE, ref_item)

        # Confidence
        pct = f"{confidence:.0%}"
        conf_item = QTableWidgetItem(pct)
        conf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        conf_color = "#4caf7d" if confidence >= 0.9 else (
            "#c9a84c" if confidence >= 0.75 else "#e05555"
        )
        conf_item.setForeground(QColor(conf_color))
        self._table.setItem(row, COL_CONFIDENCE, conf_item)

        # Status — starts as pending
        status_item = QTableWidgetItem("Pending…")
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_item.setForeground(QColor("#8a8a9a"))
        self._table.setItem(row, COL_STATUS, status_item)

        # Resend button
        resend_btn = QPushButton("Resend")
        resend_btn.setObjectName("resendButton")
        resend_btn.setFixedHeight(26)
        resend_btn.setFixedWidth(70)
        resend_btn.clicked.connect(lambda _, r=ref_display: self.resend_requested.emit(r))
        self._table.setCellWidget(row, COL_ACTION, _center_widget(resend_btn))

        self._rows.append((ref_display, ts))
        self._update_count_label()
        self._scroll_to_bottom()

    @pyqtSlot(str, str)
    def update_status(self, ref_display: str, status: str) -> None:
        """Update the status column for the most recent matching row."""
        # Find the last row with this reference
        for row in range(self._table.rowCount() - 1, -1, -1):
            item = self._table.item(row, COL_REFERENCE)
            if item and ref_display in item.text():
                color, label = STATUS_COLORS.get(status, ("#8a8a9a", status))
                status_item = QTableWidgetItem(label)
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                status_item.setForeground(QColor(color))
                self._table.setItem(row, COL_STATUS, status_item)

                if status in self._counts:
                    self._counts[status] += 1
                    self._update_summary()
                break

    def set_resend_result(self, success: bool, ref_display: str) -> None:
        """Called after a manual resend attempt finishes."""
        status = "ew_success" if success else "failed"
        self.update_status(ref_display, status)

    # ── Internal helpers ───────────────────────────────────────────────────

    def _clear_history(self) -> None:
        self._table.setRowCount(0)
        self._rows.clear()
        self._counts = {"ew_success": 0, "overlay_fallback": 0, "failed": 0}
        self._update_count_label()
        self._update_summary()

    def _update_count_label(self) -> None:
        n = self._table.rowCount()
        self._count_label.setText(f"{n} verse{'s' if n != 1 else ''}")

    def _update_summary(self) -> None:
        self._success_label.setText(f"✓ Displayed: {self._counts['ew_success']}")
        self._fallback_label.setText(f"◈ Overlay: {self._counts['overlay_fallback']}")
        self._failed_label.setText(f"✗ Failed: {self._counts['failed']}")

    def _scroll_to_bottom(self) -> None:
        self._table.scrollToBottom()


def _center_widget(widget: QWidget) -> QWidget:
    """Wrap a widget in a centred container for table cell use."""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(4, 2, 4, 2)
    layout.addStretch()
    layout.addWidget(widget)
    layout.addStretch()
    container.setStyleSheet("background: transparent;")
    return container
