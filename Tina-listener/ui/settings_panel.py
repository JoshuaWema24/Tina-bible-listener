"""
ui/settings_panel.py
Settings tab — all configurable options with persistence via QSettings / JSON.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QSlider,
    QRadioButton, QCheckBox, QPushButton, QGroupBox, QScrollArea,
    QFrame, QButtonGroup, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from PyQt6.QtGui import QFont

try:
    import sounddevice as sd
    _SD_AVAILABLE = True
except Exception:
    _SD_AVAILABLE = False


SETTINGS_FILE = Path.home() / ".tina_bible_listener" / "settings.json"

WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
COMPUTE_DEVICES = ["cpu", "cuda", "auto"]
SCREEN_EDGES = ["top", "bottom"]
FONT_SIZES = list(range(12, 41, 2))


class SettingsPanel(QWidget):
    """
    Full settings tab.  Emits settings_saved(dict) when the user hits Save.
    """

    settings_saved = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("settingsPanel")
        self._build_ui()
        self._load_settings()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet("background-color: #1a1a24;")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # ── Audio / Microphone ────────────────────────────────────────────
        audio_group = self._make_group("🎙  AUDIO & MICROPHONE")
        ag = QGridLayout()
        ag.setSpacing(10)

        ag.addWidget(_label("Input Device"), 0, 0)
        self.mic_combo = QComboBox()
        self.mic_combo.setMinimumWidth(300)
        self._populate_mic_devices()
        ag.addWidget(self.mic_combo, 0, 1)

        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setFixedWidth(80)
        refresh_btn.clicked.connect(self._populate_mic_devices)
        ag.addWidget(refresh_btn, 0, 2)

        ag.setColumnStretch(3, 1)
        audio_group.layout().addLayout(ag)
        layout.addWidget(audio_group)

        # ── Whisper / STT ─────────────────────────────────────────────────
        stt_group = self._make_group("🧠  SPEECH-TO-TEXT (WHISPER)")
        sg = QGridLayout()
        sg.setSpacing(10)

        sg.addWidget(_label("Model Size"), 0, 0)
        self.model_combo = QComboBox()
        self.model_combo.addItems(WHISPER_MODELS)
        self.model_combo.setCurrentText("base")
        sg.addWidget(self.model_combo, 0, 1)

        sg.addWidget(_label("Compute Device"), 1, 0)
        self._compute_group = QButtonGroup(self)
        compute_row = QHBoxLayout()
        for dev in COMPUTE_DEVICES:
            rb = QRadioButton(dev.upper())
            self._compute_group.addButton(rb)
            rb.setProperty("value", dev)
            compute_row.addWidget(rb)
            if dev == "cpu":
                rb.setChecked(True)
        compute_row.addStretch()
        sg.addLayout(compute_row, 1, 1)

        sg.addWidget(_label("Language"), 2, 0)
        self.lang_edit = QLineEdit("en")
        self.lang_edit.setMaximumWidth(80)
        sg.addWidget(self.lang_edit, 2, 1)

        sg.setColumnStretch(2, 1)
        stt_group.layout().addLayout(sg)
        layout.addWidget(stt_group)

        # ── EasyWorship ───────────────────────────────────────────────────
        ew_group = self._make_group("🎞  EASYWORSHIP INTEGRATION")
        eg = QGridLayout()
        eg.setSpacing(10)

        eg.addWidget(_label("Companion Host"), 0, 0)
        self.companion_host = QLineEdit("localhost")
        eg.addWidget(self.companion_host, 0, 1)

        eg.addWidget(_label("Companion Port"), 1, 0)
        self.companion_port = QSpinBox()
        self.companion_port.setRange(1024, 65535)
        self.companion_port.setValue(7979)
        self.companion_port.setMaximumWidth(100)
        eg.addWidget(self.companion_port, 1, 1)

        eg.addWidget(_label("Bible Search Hotkey"), 2, 0)
        self.bible_hotkey = QLineEdit("ctrl+b")
        eg.addWidget(self.bible_hotkey, 2, 1)

        eg.addWidget(_label("Go Live Hotkey"), 3, 0)
        self.golive_hotkey = QLineEdit("F7")
        eg.addWidget(self.golive_hotkey, 3, 1)

        eg.setColumnStretch(2, 1)
        ew_group.layout().addLayout(eg)
        layout.addWidget(ew_group)

        # ── Detection ─────────────────────────────────────────────────────
        det_group = self._make_group("🔍  DETECTION SETTINGS")
        dg = QGridLayout()
        dg.setSpacing(10)

        dg.addWidget(_label("Confidence Threshold"), 0, 0)
        conf_row = QHBoxLayout()
        self.conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.conf_slider.setRange(50, 100)
        self.conf_slider.setValue(75)
        self.conf_slider.setMaximumWidth(240)
        self._conf_val_label = QLabel("0.75")
        self._conf_val_label.setStyleSheet("color: #c9a84c; font-weight: 700; min-width: 36px;")
        self.conf_slider.valueChanged.connect(
            lambda v: self._conf_val_label.setText(f"{v/100:.2f}")
        )
        conf_row.addWidget(self.conf_slider)
        conf_row.addWidget(self._conf_val_label)
        conf_row.addStretch()
        dg.addLayout(conf_row, 0, 1)

        dg.addWidget(_label("Debounce (seconds)"), 1, 0)
        self.debounce_spin = QDoubleSpinBox()
        self.debounce_spin.setRange(0.5, 10.0)
        self.debounce_spin.setSingleStep(0.5)
        self.debounce_spin.setValue(2.0)
        self.debounce_spin.setMaximumWidth(100)
        dg.addWidget(self.debounce_spin, 1, 1)

        dg.addWidget(_label("Fuzzy Match Threshold"), 2, 0)
        fuzzy_row = QHBoxLayout()
        self.fuzzy_slider = QSlider(Qt.Orientation.Horizontal)
        self.fuzzy_slider.setRange(60, 100)
        self.fuzzy_slider.setValue(80)
        self.fuzzy_slider.setMaximumWidth(240)
        self._fuzzy_val_label = QLabel("80")
        self._fuzzy_val_label.setStyleSheet("color: #c9a84c; font-weight: 700; min-width: 36px;")
        self.fuzzy_slider.valueChanged.connect(
            lambda v: self._fuzzy_val_label.setText(str(v))
        )
        fuzzy_row.addWidget(self.fuzzy_slider)
        fuzzy_row.addWidget(self._fuzzy_val_label)
        fuzzy_row.addStretch()
        dg.addLayout(fuzzy_row, 2, 1)

        dg.setColumnStretch(2, 1)
        det_group.layout().addLayout(dg)
        layout.addWidget(det_group)

        # ── Overlay ───────────────────────────────────────────────────────
        ov_group = self._make_group("📺  VERSE OVERLAY")
        og = QGridLayout()
        og.setSpacing(10)

        og.addWidget(_label("Enable Overlay"), 0, 0)
        self.overlay_check = QCheckBox("Show verse overlay strip")
        self.overlay_check.setChecked(True)
        og.addWidget(self.overlay_check, 0, 1)

        og.addWidget(_label("Screen Edge"), 1, 0)
        self._edge_group = QButtonGroup(self)
        edge_row = QHBoxLayout()
        for edge in SCREEN_EDGES:
            rb = QRadioButton(edge.capitalize())
            self._edge_group.addButton(rb)
            rb.setProperty("value", edge)
            edge_row.addWidget(rb)
            if edge == "bottom":
                rb.setChecked(True)
        edge_row.addStretch()
        og.addLayout(edge_row, 1, 1)

        og.addWidget(_label("Font Size"), 2, 0)
        font_row = QHBoxLayout()
        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setRange(12, 40)
        self.font_slider.setValue(24)
        self.font_slider.setMaximumWidth(200)
        self._font_val_label = QLabel("24px")
        self._font_val_label.setStyleSheet("color: #c9a84c; font-weight: 700; min-width: 40px;")
        self.font_slider.valueChanged.connect(
            lambda v: self._font_val_label.setText(f"{v}px")
        )
        font_row.addWidget(self.font_slider)
        font_row.addWidget(self._font_val_label)
        font_row.addStretch()
        og.addLayout(font_row, 2, 1)

        og.addWidget(_label("Display Duration (s)"), 3, 0)
        self.overlay_duration = QSpinBox()
        self.overlay_duration.setRange(1, 60)
        self.overlay_duration.setValue(8)
        self.overlay_duration.setMaximumWidth(80)
        og.addWidget(self.overlay_duration, 3, 1)

        og.setColumnStretch(2, 1)
        ov_group.layout().addLayout(og)
        layout.addWidget(ov_group)

        # ── Save ─────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        btn_row.addWidget(reset_btn)

        save_btn = QPushButton("💾  Save Settings")
        save_btn.setObjectName("primaryButton")
        save_btn.setFixedHeight(36)
        save_btn.setMinimumWidth(140)
        save_btn.clicked.connect(self._save_settings)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)
        layout.addStretch()

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _make_group(title: str) -> QGroupBox:
        g = QGroupBox(title)
        layout = QVBoxLayout(g)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(8)
        return g

    def _populate_mic_devices(self) -> None:
        self.mic_combo.clear()
        if _SD_AVAILABLE:
            try:
                devices = sd.query_devices()
                for i, d in enumerate(devices):
                    if d["max_input_channels"] > 0:
                        self.mic_combo.addItem(f"{i}: {d['name']}", i)
                return
            except Exception:
                pass
        self.mic_combo.addItem("Default System Microphone", -1)

    def _get_selected_radio(self, group: QButtonGroup) -> str:
        for btn in group.buttons():
            if btn.isChecked():
                return btn.property("value") or btn.text().lower()
        return ""

    # ── Persistence ────────────────────────────────────────────────────────

    def _build_dict(self) -> Dict[str, Any]:
        return {
            "audio": {
                "device_index": self.mic_combo.currentData(),
                "device_name": self.mic_combo.currentText(),
            },
            "whisper": {
                "model": self.model_combo.currentText(),
                "compute_device": self._get_selected_radio(self._compute_group),
                "language": self.lang_edit.text().strip() or "en",
            },
            "companion": {
                "host": self.companion_host.text().strip(),
                "port": self.companion_port.value(),
            },
            "easyworship": {
                "bible_hotkey": self.bible_hotkey.text().strip(),
                "golive_hotkey": self.golive_hotkey.text().strip(),
            },
            "detection": {
                "confidence_threshold": self.conf_slider.value() / 100,
                "debounce_seconds": self.debounce_spin.value(),
                "fuzzy_threshold": self.fuzzy_slider.value(),
            },
            "overlay": {
                "enabled": self.overlay_check.isChecked(),
                "edge": self._get_selected_radio(self._edge_group),
                "font_size": self.font_slider.value(),
                "duration_seconds": self.overlay_duration.value(),
            },
        }

    def _save_settings(self) -> None:
        data = self._build_dict()
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        self.settings_saved.emit(data)

        # Visual feedback
        save_btn = self.findChild(QPushButton, "primaryButton")
        # (button found by iteration since object name not unique here)
        for btn in self.findChildren(QPushButton):
            if "Save Settings" in btn.text():
                original = btn.text()
                btn.setText("✓  Saved!")
                btn.setEnabled(False)
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(1500, lambda: (btn.setText(original), btn.setEnabled(True)))
                break

    def _load_settings(self) -> None:
        if not SETTINGS_FILE.exists():
            return
        try:
            with open(SETTINGS_FILE) as f:
                data = json.load(f)
        except Exception:
            return

        a = data.get("audio", {})
        w = data.get("whisper", {})
        c = data.get("companion", {})
        e = data.get("easyworship", {})
        d = data.get("detection", {})
        o = data.get("overlay", {})

        # Audio
        if a.get("device_name"):
            idx = self.mic_combo.findText(a["device_name"])
            if idx >= 0:
                self.mic_combo.setCurrentIndex(idx)

        # Whisper
        if w.get("model"):
            self.model_combo.setCurrentText(w["model"])
        if w.get("language"):
            self.lang_edit.setText(w["language"])
        if w.get("compute_device"):
            for btn in self._compute_group.buttons():
                if btn.property("value") == w["compute_device"]:
                    btn.setChecked(True)

        # Companion
        if c.get("host"):
            self.companion_host.setText(c["host"])
        if c.get("port"):
            self.companion_port.setValue(c["port"])

        # EasyWorship
        if e.get("bible_hotkey"):
            self.bible_hotkey.setText(e["bible_hotkey"])
        if e.get("golive_hotkey"):
            self.golive_hotkey.setText(e["golive_hotkey"])

        # Detection
        if d.get("confidence_threshold"):
            self.conf_slider.setValue(int(d["confidence_threshold"] * 100))
        if d.get("debounce_seconds"):
            self.debounce_spin.setValue(d["debounce_seconds"])
        if d.get("fuzzy_threshold"):
            self.fuzzy_slider.setValue(d["fuzzy_threshold"])

        # Overlay
        self.overlay_check.setChecked(o.get("enabled", True))
        if o.get("font_size"):
            self.font_slider.setValue(o["font_size"])
        if o.get("duration_seconds"):
            self.overlay_duration.setValue(o["duration_seconds"])
        if o.get("edge"):
            for btn in self._edge_group.buttons():
                if btn.property("value") == o["edge"]:
                    btn.setChecked(True)

    def _reset_defaults(self) -> None:
        self.model_combo.setCurrentText("base")
        self.lang_edit.setText("en")
        self.companion_host.setText("localhost")
        self.companion_port.setValue(7979)
        self.bible_hotkey.setText("ctrl+b")
        self.golive_hotkey.setText("F7")
        self.conf_slider.setValue(75)
        self.debounce_spin.setValue(2.0)
        self.fuzzy_slider.setValue(80)
        self.overlay_check.setChecked(True)
        self.font_slider.setValue(24)
        self.overlay_duration.setValue(8)
        for btn in self._compute_group.buttons():
            if btn.property("value") == "cpu":
                btn.setChecked(True)
        for btn in self._edge_group.buttons():
            if btn.property("value") == "bottom":
                btn.setChecked(True)

    def get_current_model(self) -> str:
        return self.model_combo.currentText()


def _label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color: #8a8a9a; font-size: 12px;")
    lbl.setMinimumWidth(180)
    return lbl
