# Tina Bible Listener for EasyWorship

> Real-time AI system that listens to a preacher, detects Bible verse references,
> and automatically displays them inside EasyWorship during live church services.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TINA BIBLE LISTENER                         │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  MICROPHONE  │───▶│  SPEECH STT  │───▶│   DECISION ENGINE    │  │
│  │  (sounddev.) │    │ (faster-     │    │                      │  │
│  │              │    │  whisper)    │    │  ┌────────────────┐  │  │
│  └──────────────┘    └──────────────┘    │  │  Bible Parser  │  │  │
│                                          │  │  (regex+fuzzy) │  │  │
│         Audio chunks (16kHz)             │  └────────────────┘  │  │
│         VAD → segment flush              │  ┌────────────────┐  │  │
│         ~300ms latency                   │  │  Debounce +    │  │  │
│                                          │  │  Correction    │  │  │
│                                          │  └────────────────┘  │  │
│                                          └──────────┬───────────┘  │
│                                                     │              │
│                          ┌──────────────────────────┼──────────┐   │
│                          │                          │          │   │
│                    VERSE │                    COMMAND│    NOISE │   │
│                          ▼                          ▼          ▼   │
│              ┌───────────────────┐    ┌─────────────────┐  ignore  │
│              │  EW UI AUTOMATION │    │  COMPANION TCP  │          │
│              │  (pywinauto)      │    │  (port 7979)    │          │
│              │                   │    │                 │          │
│              │  1. Ctrl+B        │    │  NEXT_SLIDE     │          │
│              │  2. Type verse    │    │  PREV_SLIDE     │          │
│              │  3. Enter         │    │  GO_LIVE etc.   │          │
│              │  4. F7 Go Live    │    └─────────────────┘          │
│              └────────┬──────────┘                                 │
│                       │  ▲ fail?                                   │
│                       │  └──────────────────────────────────────┐  │
│              ┌────────▼──────────────────────────────────────┐  │  │
│              │          FALLBACK OVERLAY WINDOW              │  │  │
│              │  (tkinter, always-on-top, bottom of screen)   │──┘  │
│              │  Shows verse reference + text immediately      │     │
│              └───────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### Threading Model

```
Main Thread:         Orchestrator.start() → blocks (keeps process alive)
  └─ sounddevice callback thread:  Audio capture → work queue
  └─ stt-worker thread:            VAD + Whisper inference → transcript callback
  └─ orchestrator-worker thread:   Decision engine + EW automation
  └─ overlay-gui thread:           tkinter event loop
  └─ companion-reconnect thread:   Background TCP reconnect
```

---

## Data Flow — End to End

```
Preacher speaks "John 3:16"
        │
        ▼  ~0ms
[sounddevice] captures 320ms audio chunks at 16kHz
        │
        ▼  ~300ms (VAD detects end of phrase)
[faster-whisper] transcribes: "John 3:16"
        │
        ▼  ~10ms
[BibleReferenceParser] extracts: BibleReference(book="John", chapter=3, verse=16)
        │
        ▼  ~1ms
[DecisionEngine] checks debounce, confidence → VERSE intent
        │
        ▼  ~5ms
[EasyWorshipAutomation] Ctrl+B → types "John 3:16" → Enter → F7
        │
        ▼  ~200ms (EW UI responds)
[EasyWorship] displays John 3:16 on projector
        │
        ▼  simultaneous
[VerseOverlay] shows "John 3:16" in operator monitoring window
```

**Typical end-to-end latency: 600ms–1.2s** (Whisper base on CPU)
**With GPU (cuda) + tiny model: 200–400ms**

---

## Folder Structure

```
tina_bible_listener/
├── main.py                          ← Entry point (CLI)
├── requirements.txt
├── .env.example
│
├── config/
│   ├── __init__.py
│   └── settings.py                  ← All configuration (dataclasses)
│
├── speech/
│   ├── __init__.py
│   └── capture.py                   ← Microphone + VAD + Whisper STT
│
├── bible_parser/
│   ├── __init__.py
│   ├── bible_data.py                ← Book names, aliases, number words
│   └── parser.py                    ← Regex + fuzzy reference extraction
│
├── easyworship_controller/
│   ├── __init__.py
│   ├── decision_engine.py           ← Intent classification + debounce
│   ├── companion_client.py          ← Official Companion TCP protocol
│   └── orchestrator.py             ← Central coordinator of all modules
│
├── automation/
│   ├── __init__.py
│   └── ew_automation.py             ← pywinauto UI automation for Bible search
│
├── overlay/
│   ├── __init__.py
│   └── verse_overlay.py             ← Tkinter fallback display window
│
├── utils/
│   ├── __init__.py
│   └── logging_setup.py             ← Loguru configuration
│
├── tests/
│   └── test_bible_parser.py         ← Pytest test suite
│
└── logs/                            ← Auto-created; daily log files
```

---

## Installation

### Prerequisites

- Windows 10/11 (required for pywinauto and EasyWorship)
- Python 3.10+
- EasyWorship installed and running
- A working microphone

### Steps

```bash
# 1. Clone / download the project
cd tina_bible_listener

# 2. Create a virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) GPU acceleration — install CUDA-compatible PyTorch first
#    Then faster-whisper will automatically use CUDA

# 5. Copy and configure environment
copy .env.example .env
# Edit .env with your settings

# 6. Find your microphone index
python main.py --list-devices

# 7. Run!
python main.py --audio-device 1
```

---

## Usage

```bash
# Basic run (system default microphone, base Whisper model)
python main.py

# Use a specific microphone
python main.py --audio-device 2

# Use faster model for lower latency
python main.py --model tiny

# GPU acceleration (requires CUDA)
python main.py --device cuda --model small

# Test the Bible parser without audio
python main.py --test-parser "First Corinthians thirteen four"
python main.py --test-parser "Psalm twenty three verse one"

# Debug mode (verbose logs)
python main.py --debug

# No overlay window (headless / second-monitor setup)
python main.py --no-overlay
```

---

## EasyWorship Configuration

### Companion Protocol
1. Open EasyWorship → Settings → Companion
2. Enable Companion
3. Note the port (default: 7979)
4. Set `EW_PORT` in your `.env` if different

### Bible Search Keyboard Shortcut
The automation uses `Ctrl+B` to open EasyWorship's Bible search.
Verify this shortcut works in your version:
- EasyWorship 7: `Ctrl+B` or check Edit menu
- EasyWorship 6: may differ — update `bible_search_hotkey` in `config/settings.py`

### Go Live Hotkey
Default: `F7`. Update `go_live_key` in settings if your version differs.

---

## Tuning for Your Environment

### Speech Recognition Quality

| Setting | Location | Effect |
|---------|----------|--------|
| `model_size` | `WhisperConfig` | `small` > `base` > `tiny` for accuracy |
| `initial_prompt` | `WhisperConfig` | Seeds Whisper with Bible vocabulary |
| `vad_threshold` | `AudioConfig` | Lower = picks up quieter speech |
| `silence_timeout` | `AudioConfig` | Increase if preacher pauses mid-verse |

### Verse Detection

| Setting | Location | Effect |
|---------|----------|--------|
| `min_confidence` | `EngineConfig` | Lower = more detections, more false positives |
| `debounce_seconds` | `EngineConfig` | Higher = avoids same verse repeating |

---

## Extending: Local Bible Text Database

To show actual verse text in the overlay, integrate a local Bible database:

```python
# In orchestrator.py → _get_verse_text()
import sqlite3

def _get_verse_text(self, ref: BibleReference) -> str:
    with sqlite3.connect("bible.db") as conn:
        row = conn.execute(
            "SELECT text FROM verses WHERE book=? AND chapter=? AND verse=?",
            (ref.book, ref.chapter, ref.verse)
        ).fetchone()
        return row[0] if row else f"({ref.display})"
```

Free SQLite Bible databases (KJV, NIV, ESV) are available from:
- https://github.com/scrollmapper/bible_databases
- OpenSong Bible modules

---

## Troubleshooting

**"EasyWorship window not found"**
→ Ensure EasyWorship is open before starting Tina
→ Try running both as Administrator

**Bible search not opening**
→ Verify `Ctrl+B` works manually in EasyWorship
→ Update `bible_search_hotkey` in settings to match your EW version

**High latency (>2 seconds)**
→ Switch to `--model tiny` for fastest transcription
→ Use `--device cuda` if you have an NVIDIA GPU
→ Check CPU usage; close other applications

**False verse detections**
→ Increase `min_confidence` in `EngineConfig`
→ Increase `debounce_seconds`

**Verse detected but not displaying in EW**
→ Run with `--debug` to see automation steps
→ The overlay will still show the verse as a fallback
→ Check EW shortcut keys match your EW version

---

## Running Tests

```bash
pytest tests/ -v
```

---

## License

MIT — use freely in your church. Contributions welcome.
