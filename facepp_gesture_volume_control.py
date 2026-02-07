"""
facepp_gesture_volume_control.py

Enhanced version that:
1) Opens your webcam and shows a live preview window.
2) Continuously captures frames and sends them to Face++ Gesture API.
3) When a "thumbs_up" gesture is detected, simulates pressing the volume up key.
4) Press ESC to quit.

Requirements:
  pip install opencv-python requests pynput
"""

import sys
import json
import time
from pathlib import Path

import cv2          # OpenCV: used to access webcam + encode images
import requests     # Used to make the HTTP POST request to Face++
from pynput.keyboard import Controller, Key  # Used to simulate keyboard presses


# Face++ US endpoint for gesture recognition
FACEPP_US_GESTURE_URL = "https://api-us.faceplusplus.com/humanbodypp/v1/gesture"

# Text file that stores your API key and secret (two lines)
KEYS_FILE = "facepp_keys.txt"

# How long to wait between API calls (seconds) - to avoid rate limiting
API_CALL_INTERVAL = 2.0

# Cooldown period after triggering volume up (to prevent repeated triggers)
COOLDOWN_PERIOD = 1.0


def read_keys_from_file(path: str):
    """
    Reads Face++ credentials from a text file.

    Expected format (two lines):
      API_KEY
      API_SECRET

    Returns:
      (api_key, api_secret)
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

    Returns:
      The response JSON as a Python dict, or None if there was an error
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

    Returns:
      True if thumbs up detected, False otherwise
    """
    if not payload:
        return False

    # Try to find hands in various possible keys
    hands = payload.get("hands") or payload.get("hand_gestures") or payload.get("result") or []

    if isinstance(hands, dict):
        hands = hands.get("hands", [])

    if not hands:
        return False

    # Check each detected hand for thumbs up gesture
    for hand in hands:
        gesture = hand.get("gesture") or hand.get("gesture_type") or hand.get("label")
        
        # If gesture is a dict of confidence scores, check thumb_up score
        if isinstance(gesture, dict):
            thumb_up_score = gesture.get("thumb_up", 0)
            print(f"Thumbs up confidence: {thumb_up_score}%")
            
            # If confidence is above 50%, consider it a thumbs up
            if thumb_up_score > 50:
                return True
        
        # If gesture is a string label
        elif isinstance(gesture, str):
            gesture_normalized = gesture.lower().replace("_", "").replace(" ", "")
            if gesture_normalized in ["thumbup", "thumbsup"]:
                return True

    return False


def simulate_volume_up():
    """
    Simulates pressing the volume up key.
    """
    keyboard = Controller()
    keyboard.press(Key.media_volume_up)
    keyboard.release(Key.media_volume_up)
    print("🔊 Volume UP triggered!")


def run_continuous_gesture_detection(api_key: str, api_secret: str, camera_index: int = 0):
    """
    Continuously captures frames from webcam and detects gestures.
    When thumbs up is detected, triggers volume up.
    
    Press ESC to quit.
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open webcam (index={camera_index}).")

    print("\n" + "="*60)
    print("GESTURE VOLUME CONTROL - Running")
    print("="*60)
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

        # Display the frame
        cv2.imshow("Gesture Volume Control (ESC to quit)", frame)

        # Check for ESC key
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break

        current_time = time.time()

        # Only make API calls at specified intervals to avoid rate limiting
        if current_time - last_api_call >= API_CALL_INTERVAL:
            last_api_call = current_time

            # Send frame to Face++
            payload = post_to_facepp_gesture(api_key, api_secret, frame)

            # Check for thumbs up
            if detect_thumbs_up(payload):
                # Only trigger if cooldown period has passed
                if current_time - last_trigger_time >= COOLDOWN_PERIOD:
                    simulate_volume_up()
                    last_trigger_time = current_time

    cap.release()
    cv2.destroyAllWindows()


def main():
    """
    Main program flow.
    """
    # Read API credentials
    try:
        api_key, api_secret = read_keys_from_file(KEYS_FILE)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Run continuous detection
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