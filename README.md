# Gesture Recognition API (Face++)

A Python prototype that uses your webcam and the [Face++ Gesture Recognition API](https://www.faceplusplus.com/) (U.S. endpoint) to detect hand gestures and control your system volume. This repo was the starting point for a later project — **[gesture-app](https://github.com/annawang22/gesture-app)** — a browser-based app that uses MediaPipe and Spotify instead of Face++.

---

## What It Does

1. Captures frames from your webcam with OpenCV
2. Sends each frame to Face++ for gesture classification
3. When a **thumbs up** is detected (confidence above 50%), increases system volume
4. Rate-limits API calls and volume changes so you stay within Face++ free-tier limits

| Gesture | Action |
|---|---|
| 👍 Thumbs up | Increase system volume |

---

## Project Evolution

| Repo | Role |
|---|---|
| **gesture-recognition-api** (this repo) | Early class project: Face++ API + Python desktop scripts |
| **[gesture-app](https://github.com/annawang22/gesture-app)** | Expanded app: MediaPipe gestures, web UI, Spotify control, hosted backend |

If you want the full Spotify + browser experience, use **gesture-app**. This repo is useful as a minimal Face++ + OpenCV reference and as the history of how the idea started.

---

## How to Run

### Requirements

- Python 3.9+
- Webcam
- [Face++](https://www.faceplusplus.com/) account with API key and secret

### Install dependencies

```bash
pip install opencv-python requests pillow
```

> **GUI app only:** `gesture_volume_app.py` also needs Pillow and uses Tkinter (included with most Python installs on macOS).

### API credentials

Create a file named `facepp_keys.txt` in the project root (this file is gitignored):

```
YOUR_API_KEY
YOUR_API_SECRET
```

Line 1 = API key, line 2 = API secret. Never commit this file.

### CLI (recommended)

Stable, cross-platform volume control via OS commands (no keyboard simulation):

```bash
python3 facepp_gesture_volume_control_v2.py
```

- Show a thumbs up to raise volume
- Press **ESC** to quit

### Desktop GUI (experimental)

Tkinter-based UI with live preview and session stats:

```bash
python3 gesture_volume_app.py
```

On some Mac setups this script can crash with `illegal hardware instruction` (often OpenCV/architecture related). If that happens, use the CLI script above.

---

## Project Structure

```
gesture-recognition-api/
├── facepp_gesture_volume_control_v2.py   # Main CLI — webcam + Face++ + volume
├── gesture_volume_app.py                 # Optional Tkinter GUI
├── facepp_keys.txt                       # Your API credentials (local only, not in git)
├── PROMPT_HISTORY.txt                    # AI tools and prompts used while building
└── README.md
```

---

## How It Works

**Face++ request** — Each eligible frame is JPEG-encoded and posted to:

`https://api-us.faceplusplus.com/humanbodypp/v1/gesture`

**Response** — JSON with detected hands, gesture labels, and confidence scores. The code looks for `thumb_up` scores above 50% (or string labels like `thumb_up` / `thumbs_up`).

**Volume** — Instead of simulating keyboard keys, `facepp_gesture_volume_control_v2.py` uses OS-specific commands:

- **macOS:** AppleScript (`osascript`)
- **Windows:** PowerShell `SendKeys`
- **Linux:** `amixer` or `pactl` when available

**Throttling** — API calls are spaced at least 2 seconds apart; volume can only trigger once per second after a detection, which helps avoid `CONCURRENCY_LIMIT_EXCEEDED` and `FREE_CALL_COUNT_LIMIT` errors on the free tier.

---

## Tech Stack

- **Language:** Python 3
- **Computer vision:** OpenCV (`cv2`)
- **HTTP:** `requests`
- **GUI (optional):** Tkinter, Pillow
- **External API:** Face++ Gesture Recognition (U.S.)

---

## Attribution

Parts of this codebase were written with assistance from ChatGPT Pro, Claude, and Gemini (Feb 2026). Prompts and tools are documented in [`PROMPT_HISTORY.txt`](PROMPT_HISTORY.txt). All code was reviewed, tested, and edited as needed.
