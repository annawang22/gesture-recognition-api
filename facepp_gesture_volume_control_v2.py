"""
facepp_gesture_volume_control_v2.py

Uses system commands to control volume instead of keyboard simulation.
Works on Windows, macOS, and Linux.
"""

import sys
import json
import time
import platform
import subprocess
from pathlib import Path

import cv2
import requests


# Face++ US endpoint for gesture recognition
FACEPP_US_GESTURE_URL = "https://api-us.faceplusplus.com/humanbodypp/v1/gesture"

# Text file that stores your API key and secret (two lines)
KEYS_FILE = "facepp_keys.txt"

# How long to wait between API calls (seconds)
API_CALL_INTERVAL = 2.0

# Cooldown period after triggering volume up (seconds)
COOLDOWN_PERIOD = 1.0


def read_keys_from_file(path: str):
    """
    Reads Face++ credentials from a text file.
    """
    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(
            f"Keys file not found: {p.resolve()}\n"
            "Create it with two lines:\n"
            "API_KEY\\nAPI_SECRET"
        )

    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]

    if len(lines) < 2:
        raise ValueError(
            "Keys file must contain at least 2 non-empty lines:\n"
            "Line 1 = API_KEY\nLine 2 = API_SECRET"
        )

    return lines[0], lines[1]


def post_to_facepp_gesture(api_key: str, api_secret: str, bgr_frame):
    """
    Sends the captured webcam frame to Face++ Gesture API.
    """
    try:
        ok, jpg = cv2.imencode(".jpg", bgr_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            return None

        files = {
            "image_file": ("frame.jpg", jpg.tobytes(), "image/jpeg")
        }

        data = {
            "api_key": api_key,
            "api_secret": api_secret
        }

        resp = requests.post(FACEPP_US_GESTURE_URL, data=data, files=files, timeout=10)

        payload = resp.json()

        if resp.status_code != 200 or "error_message" in payload:
            print(f"API error: {payload.get('error_message', 'Unknown error')}")
            return None

        return payload

    except Exception as e:
        print(f"Request error: {e}")
        return None


def detect_thumbs_up(payload: dict):
    """
    Checks if a thumbs-up gesture was detected in the Face++ response.
    """
    if not payload:
        return False

    hands = payload.get("hands") or payload.get("hand_gestures") or payload.get("result") or []

    if isinstance(hands, dict):
        hands = hands.get("hands", [])

    if not hands:
        return False

    for hand in hands:
        gesture = hand.get("gesture") or hand.get("gesture_type") or hand.get("label")
        
        if isinstance(gesture, dict):
            thumb_up_score = gesture.get("thumb_up", 0)
            
            if thumb_up_score > 50:
                print(f"👍 Thumbs up detected! Confidence: {thumb_up_score}%")
                return True
        
        elif isinstance(gesture, str):
            gesture_normalized = gesture.lower().replace("_", "").replace(" ", "")
            if gesture_normalized in ["thumbup", "thumbsup"]:
                print(f"👍 Thumbs up detected!")
                return True

    return False


def increase_volume():
    """
    Increases system volume using OS-specific commands.
    """
    system = platform.system()
    
    try:
        if system == "Windows":
            # Windows: Use NirCmd (needs to be installed) or PowerShell
            # Method 1: Try PowerShell (built-in)
            script = '''
            $obj = New-Object -ComObject WScript.Shell
            $obj.SendKeys([char]175)
            '''
            subprocess.run(["powershell", "-Command", script], check=True, capture_output=True)
            print("🔊 Volume UP (Windows)")
            
        elif system == "Darwin":  # macOS
            # Increase volume by 10% (0-100 scale)
            subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10)"], check=True)
            print("🔊 Volume UP (macOS)")
            
        elif system == "Linux":
            # Try multiple methods for Linux
            try:
                # Method 1: amixer (ALSA)
                subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "5%+"], check=True, capture_output=True)
                print("🔊 Volume UP (Linux - amixer)")
            except:
                try:
                    # Method 2: pactl (PulseAudio)
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"], check=True, capture_output=True)
                    print("🔊 Volume UP (Linux - pactl)")
                except:
                    print("⚠️ Could not increase volume. Install alsa-utils or pulseaudio-utils")
        else:
            print(f"⚠️ Unsupported OS: {system}")
            
    except Exception as e:
        print(f"⚠️ Volume control error: {e}")


def run_continuous_gesture_detection(api_key: str, api_secret: str, camera_index: int = 0):
    """
    Continuously captures frames from webcam and detects gestures.
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open webcam (index={camera_index}).")

    system = platform.system()
    print("\n" + "="*60)
    print("GESTURE VOLUME CONTROL - Running")
    print("="*60)
    print(f"Operating System: {system}")
    print("👍 Show a THUMBS UP gesture to increase volume")
    print("⌨️  Press ESC to quit")
    print("="*60 + "\n")

    last_api_call = 0
    last_trigger_time = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Failed to read from webcam.")
            break

        cv2.imshow("Gesture Volume Control (ESC to quit)", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break

        current_time = time.time()

        if current_time - last_api_call >= API_CALL_INTERVAL:
            last_api_call = current_time

            payload = post_to_facepp_gesture(api_key, api_secret, frame)

            if detect_thumbs_up(payload):
                if current_time - last_trigger_time >= COOLDOWN_PERIOD:
                    increase_volume()
                    last_trigger_time = current_time

    cap.release()
    cv2.destroyAllWindows()


def main():
    """
    Main program flow.
    """
    try:
        api_key, api_secret = read_keys_from_file(KEYS_FILE)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    try:
        run_continuous_gesture_detection(api_key, api_secret, camera_index=0)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("Goodbye!")


if __name__ == "__main__":
    main()
