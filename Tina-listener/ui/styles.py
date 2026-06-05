DARK_STYLESHEET = """
/* ═══════════════════════════════════════════════
   TINA BIBLE LISTENER — Dark Broadcast Stylesheet
   ═══════════════════════════════════════════════ */

QMainWindow, QDialog {
    background-color: #0f0f14;
    color: #f0e6d3;
    font-family: "Segoe UI";
    font-size: 13px;
}

QWidget {
    background-color: #0f0f14;
    color: #f0e6d3;
    font-family: "Segoe UI";
    font-size: 13px;
}

/* ── Sidebar ── */
#sidebar {
    background-color: #0a0a0f;
    border-right: 1px solid #1e1e2e;
    min-width: 200px;
    max-width: 240px;
}

#appTitle {
    color: #c9a84c;
    font-size: 22px;
    font-weight: 700;
    font-family: "Segoe UI";
    letter-spacing: 3px;
    padding: 0px;
}

#appSubtitle {
    color: #8a8a9a;
    font-size: 9px;
    letter-spacing: 2px;
    text-transform: uppercase;
}

/* ── Start/Stop Button ── */
#startButton {
    background-color: #1e4d2e;
    color: #4caf7d;
    border: 2px solid #4caf7d;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 12px 20px;
    min-height: 48px;
}
#startButton:hover {
    background-color: #2a6b3f;
    color: #6fcf97;
    border-color: #6fcf97;
}
#startButton:pressed {
    background-color: #4caf7d;
    color: #0a0a0f;
}

#stopButton {
    background-color: #4d1e1e;
    color: #e05555;
    border: 2px solid #e05555;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 12px 20px;
    min-height: 48px;
}
#stopButton:hover {
    background-color: #6b2a2a;
    color: #ff7070;
    border-color: #ff7070;
}
#stopButton:pressed {
    background-color: #e05555;
    color: #0a0a0f;
}

/* ── Status Indicators ── */
#statusPanel {
    background-color: #12121a;
    border-radius: 8px;
    border: 1px solid #1e1e2e;
    padding: 4px;
}

#statusLabel {
    color: #8a8a9a;
    font-size: 11px;
    letter-spacing: 1px;
}

#statusTitle {
    color: #8a8a9a;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}

#timerLabel {
    color: #c9a84c;
    font-size: 20px;
    font-family: "Courier New";
    font-weight: 700;
    letter-spacing: 2px;
}

#timerCaption {
    color: #8a8a9a;
    font-size: 9px;
    letter-spacing: 1px;
}

/* ── Tab Widget ── */
QTabWidget::pane {
    border: 1px solid #1e1e2e;
    background-color: #1a1a24;
    border-radius: 0px 8px 8px 8px;
}

QTabBar::tab {
    background-color: #12121a;
    color: #8a8a9a;
    border: 1px solid #1e1e2e;
    border-bottom: none;
    padding: 8px 20px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
    margin-right: 2px;
    border-radius: 6px 6px 0px 0px;
}

QTabBar::tab:selected {
    background-color: #1a1a24;
    color: #c9a84c;
    border-bottom: 1px solid #1a1a24;
}

QTabBar::tab:hover:!selected {
    background-color: #1a1a24;
    color: #f0e6d3;
}

/* ── Live Feed ── */
#liveFeedWidget {
    background-color: #1a1a24;
}

#transcriptView {
    background-color: #10101a;
    color: #f0e6d3;
    border: 1px solid #1e1e2e;
    border-radius: 6px;
    font-family: "Consolas";
    font-size: 12px;
    line-height: 1.6;
    padding: 8px;
    selection-background-color: #c9a84c;
    selection-color: #0f0f14;
}

/* ── Verse History ── */
QTableWidget {
    background-color: #10101a;
    alternate-background-color: #13131e;
    color: #f0e6d3;
    gridline-color: #1e1e2e;
    border: 1px solid #1e1e2e;
    border-radius: 6px;
    font-size: 12px;
    selection-background-color: #2a2a3e;
    selection-color: #f0e6d3;
}

QTableWidget::item {
    padding: 6px 10px;
    border: none;
}

QHeaderView::section {
    background-color: #0a0a0f;
    color: #8a8a9a;
    border: none;
    border-bottom: 1px solid #1e1e2e;
    border-right: 1px solid #1e1e2e;
    padding: 8px 10px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}

QTableWidget QScrollBar:vertical {
    background-color: #0f0f14;
    width: 8px;
    margin: 0;
}

QTableWidget QScrollBar::handle:vertical {
    background-color: #2a2a3a;
    border-radius: 4px;
    min-height: 20px;
}

QTableWidget QScrollBar::handle:vertical:hover {
    background-color: #3a3a4a;
}

QTableWidget QScrollBar::add-line:vertical,
QTableWidget QScrollBar::sub-line:vertical {
    height: 0px;
}

/* ── Scrollbars (general) ── */
QScrollBar:vertical {
    background-color: #0f0f14;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #2a2a3a;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #c9a84c;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0f0f14;
    height: 8px;
}

QScrollBar::handle:horizontal {
    background-color: #2a2a3a;
    border-radius: 4px;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ── Settings Panel ── */
#settingsPanel {
    background-color: #1a1a24;
    padding: 8px;
}

#settingGroup {
    background-color: #12121a;
    border: 1px solid #1e1e2e;
    border-radius: 8px;
    margin-bottom: 4px;
}

QGroupBox {
    background-color: #12121a;
    border: 1px solid #1e1e2e;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    font-size: 11px;
    font-weight: 600;
    color: #8a8a9a;
    letter-spacing: 1.5px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    color: #c9a84c;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
}

QLabel {
    color: #8a8a9a;
    font-size: 12px;
}

QComboBox {
    background-color: #10101a;
    color: #f0e6d3;
    border: 1px solid #2a2a3a;
    border-radius: 5px;
    padding: 6px 10px;
    font-size: 12px;
    min-height: 28px;
}

QComboBox:hover {
    border-color: #c9a84c;
}

QComboBox:focus {
    border-color: #c9a84c;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #8a8a9a;
    width: 0;
    height: 0;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1a1a24;
    color: #f0e6d3;
    border: 1px solid #2a2a3a;
    selection-background-color: #c9a84c;
    selection-color: #0f0f14;
    outline: none;
}

QLineEdit {
    background-color: #10101a;
    color: #f0e6d3;
    border: 1px solid #2a2a3a;
    border-radius: 5px;
    padding: 6px 10px;
    font-size: 12px;
    min-height: 28px;
}

QLineEdit:hover {
    border-color: #3a3a4a;
}

QLineEdit:focus {
    border-color: #c9a84c;
    background-color: #12121e;
}

QSpinBox, QDoubleSpinBox {
    background-color: #10101a;
    color: #f0e6d3;
    border: 1px solid #2a2a3a;
    border-radius: 5px;
    padding: 6px 8px;
    font-size: 12px;
    min-height: 28px;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #c9a84c;
}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background-color: #1a1a2a;
    border: none;
    width: 18px;
    border-radius: 3px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #2a2a3a;
}

QSlider::groove:horizontal {
    background-color: #1e1e2e;
    height: 4px;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background-color: #c9a84c;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background-color: #e2b85a;
    width: 18px;
    height: 18px;
    margin: -7px 0;
}

QSlider::sub-page:horizontal {
    background-color: #c9a84c;
    border-radius: 2px;
}

QRadioButton {
    color: #f0e6d3;
    font-size: 12px;
    spacing: 8px;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid #2a2a3a;
    background-color: #10101a;
}

QRadioButton::indicator:checked {
    background-color: #c9a84c;
    border-color: #c9a84c;
}

QRadioButton::indicator:hover {
    border-color: #c9a84c;
}

QCheckBox {
    color: #f0e6d3;
    font-size: 12px;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 2px solid #2a2a3a;
    background-color: #10101a;
}

QCheckBox::indicator:checked {
    background-color: #c9a84c;
    border-color: #c9a84c;
}

QCheckBox::indicator:hover {
    border-color: #c9a84c;
}

/* ── Buttons ── */
QPushButton {
    background-color: #1a1a2e;
    color: #f0e6d3;
    border: 1px solid #2a2a3a;
    border-radius: 5px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #24243a;
    border-color: #c9a84c;
    color: #c9a84c;
}

QPushButton:pressed {
    background-color: #c9a84c;
    color: #0f0f14;
    border-color: #c9a84c;
}

QPushButton:disabled {
    background-color: #12121a;
    color: #3a3a4a;
    border-color: #1e1e2e;
}

#primaryButton {
    background-color: #2a1f0a;
    color: #c9a84c;
    border: 1px solid #c9a84c;
    border-radius: 5px;
    padding: 8px 20px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}

#primaryButton:hover {
    background-color: #3a2b0e;
    color: #e2b85a;
    border-color: #e2b85a;
}

#primaryButton:pressed {
    background-color: #c9a84c;
    color: #0f0f14;
}

#resendButton {
    background-color: #0a1a2a;
    color: #4a9ecf;
    border: 1px solid #2a4a6a;
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}

#resendButton:hover {
    background-color: #0d2035;
    border-color: #4a9ecf;
}

#dangerButton {
    background-color: #1a0a0a;
    color: #e05555;
    border: 1px solid #4a1e1e;
    border-radius: 5px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 600;
}

#dangerButton:hover {
    background-color: #2a0f0f;
    border-color: #e05555;
}

/* ── Splitter ── */
QSplitter::handle {
    background-color: #1e1e2e;
    width: 1px;
}

/* ── ScrollArea ── */
QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* ── Tooltips ── */
QToolTip {
    background-color: #1a1a24;
    color: #f0e6d3;
    border: 1px solid #c9a84c;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}

/* ── Separator ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #1e1e2e;
    border: none;
    background-color: #1e1e2e;
    max-height: 1px;
}
"""

# Verse monitor stylesheet (secondary window)
MONITOR_STYLESHEET = """
QWidget {
    background-color: #080810;
    color: #f0e6d3;
    font-family: "Segoe UI";
}

#monitorRef {
    color: #c9a84c;
    font-size: 36px;
    font-weight: 700;
    font-family: "Segoe UI";
    letter-spacing: 2px;
}

#monitorText {
    color: #f0e6d3;
    font-size: 20px;
    font-family: "Segoe UI";
    line-height: 1.5;
}

#monitorIdle {
    color: #2a2a3a;
    font-size: 18px;
    font-family: "Segoe UI";
    font-style: italic;
}

#monitorBar {
    background-color: #c9a84c;
    min-height: 3px;
    max-height: 3px;
}

QPushButton {
    background-color: #1a1a24;
    color: #8a8a9a;
    border: 1px solid #1e1e2e;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 11px;
}

QPushButton:hover {
    color: #c9a84c;
    border-color: #c9a84c;
}
"""
