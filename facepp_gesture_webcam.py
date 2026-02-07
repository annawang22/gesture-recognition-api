"""
facepp_gesture_webcam.py

What this program does:
1) Opens your webcam and shows a live preview window.
2) When you press SPACE, it captures the current frame (a single image).
3) It encodes that image as a JPEG (in memory).
4) It sends the JPEG to Face++ (US) Gesture API using your api_key + api_secret.
5) It prints back gesture-related info from the JSON response.

Requirements:
  pip install opencv-python requests
"""

import sys
import json
from pathlib import Path

import cv2          # OpenCV: used to access webcam + encode images
import requests     # Used to make the HTTP POST request to Face++


# Face++ US endpoint for gesture recognition
FACEPP_US_GESTURE_URL = "https://api-us.faceplusplus.com/humanbodypp/v1/gesture"

# Text file that stores your API key and secret (two lines)
# Line 1: API_KEY
# Line 2: API_SECRET
KEYS_FILE = "facepp_keys.txt"


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

    # If the file doesn't exist, stop and tell the user what to do.
    if not p.exists():
        raise FileNotFoundError(
            f"Keys file not found: {p.resolve()}\n"
            "Create it with two lines:\n"
            "API_KEY\\nAPI_SECRET"
        )

    # Read file, split into lines, strip whitespace, and ignore blank lines
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]

    # Make sure we have at least two lines
    if len(lines) < 2:
        raise ValueError(
            "Keys file must contain at least 2 non-empty lines:\n"
            "Line 1 = API_KEY\nLine 2 = API_SECRET"
        )

    # Return the first two lines as key + secret
    return lines[0], lines[1]


def capture_frame_from_webcam(camera_index: int = 0):
    """
    Opens the webcam and shows a preview window.

    Controls:
      - Press SPACE to capture one frame (image)
      - Press ESC to quit without capturing

    Returns:
      The captured image as a NumPy array (BGR format), or None if user quits.
    """
    # Try to open the webcam (index 0 is usually the default camera)
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open webcam (index={camera_index}).")

    print("Webcam opened. Press SPACE to capture a frame, or ESC to quit.")
    frame = None

    while True:
        # Read one frame from the webcam
        ok, img = cap.read()
        if not ok:
            cap.release()
            raise RuntimeError("Failed to read from webcam.")

        # Show the live camera feed in a window
        cv2.imshow("Face++ Gesture Capture", img)

        # Wait 1ms for keyboard input
        key = cv2.waitKey(1) & 0xFF

        if key == 27:  # ESC key
            cap.release()
            cv2.destroyAllWindows()
            return None

        if key == 32:  # SPACE key
            frame = img  # Save the current frame
            break

    # Clean up camera + window
    cap.release()
    cv2.destroyAllWindows()

    return frame


def post_to_facepp_gesture(api_key: str, api_secret: str, bgr_frame):
    """
    Sends the captured webcam frame to Face++ Gesture API.

    Steps:
      1) Convert the frame into JPEG bytes in memory (no file saved)
      2) POST those bytes to Face++ using requests
      3) Parse and return the JSON response

    Returns:
      The response JSON as a Python dict
    """
    # OpenCV images are numpy arrays (BGR). Face++ needs an image upload.
    # We encode the array to JPEG bytes (like saving as .jpg, but in memory).
    ok, jpg = cv2.imencode(".jpg", bgr_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    if not ok:
        raise RuntimeError("Failed to encode frame as JPEG.")

    # 'files' tells requests to upload a file (multipart/form-data)
    files = {
        "image_file": ("frame.jpg", jpg.tobytes(), "image/jpeg")
    }

    # 'data' is normal form fields (your Face++ credentials)
    data = {
        "api_key": api_key,
        "api_secret": api_secret
    }

    # Make the POST request to Face++
    resp = requests.post(FACEPP_US_GESTURE_URL, data=data, files=files, timeout=30)

    # Face++ typically returns JSON (even on errors)
    try:
        payload = resp.json()
    except Exception:
        raise RuntimeError(
            f"Non-JSON response (status={resp.status_code}): {resp.text[:300]}"
        )

    # If Face++ reports an error, it usually includes "error_message"
    if resp.status_code != 200 or "error_message" in payload:
        raise RuntimeError(f"Face++ error (status={resp.status_code}): {payload}")

    return payload


def pretty_print_gesture_result(payload: dict):
    """
    Face++ returns a JSON object. This function tries to pull out
    gesture-related fields and print them nicely.

    Because APIs sometimes change field names, we try several common keys.
    If we can't find anything, we print the full JSON so you can inspect it.
    """
    # Different Face++ responses may store hands under different keys.
    hands = payload.get("hands") or payload.get("hand_gestures") or payload.get("result") or []

    print("\n=== Gesture summary ===")

    # If we didn't find any hands, print the entire response for debugging
    if not hands:
        print("No hands/gestures detected (or unexpected response format).")
        print("Full JSON:\n")
        print(json.dumps(payload, indent=2))
        return

    # Sometimes 'hands' might itself be a dict that contains "hands"
    if isinstance(hands, dict):
        hands = hands.get("hands", [])

    # Loop over detected hands and print top info
    for i, hand in enumerate(hands):
        print(f"\nHand #{i+1}")

        # Many APIs provide a bounding rectangle around the hand
        rect = hand.get("hand_rectangle") or hand.get("rectangle") or hand.get("rect")
        if rect:
            print(f"  Bounding box: {rect}")

        # The main predicted gesture label might be under different keys
        label = hand.get("gesture") or hand.get("gesture_type") or hand.get("label")
        if label:
            print(f"  Top gesture: {label}")

        # Confidence scores might be a dict of {gesture_name: score}
        conf = hand.get("confidence") or hand.get("scores") or hand.get("gesture_confidence")
        if isinstance(conf, dict) and conf:
            # Sort the dict to print the top 3 highest confidence gestures
            top3 = sorted(conf.items(), key=lambda x: x[1], reverse=True)[:3]
            print("  Top-3 confidences:")
            for g, s in top3:
                print(f"    - {g}: {s}")
        elif conf is not None:
            # Sometimes confidence might just be a number
            print(f"  Confidence: {conf}")

        # If none of the above worked, print the whole hand object
        if not (rect or label or conf):
            print("  (Could not parse standard fields; printing this hand object.)")
            print(json.dumps(hand, indent=2))


def main():
    """
    Main program flow:
      - Read API credentials
      - Capture a webcam frame
      - Send it to Face++
      - Print results
    """
    # Step 1: Read credentials from the keys file
    try:
        api_key, api_secret = read_keys_from_file(KEYS_FILE)
    except Exception as e:
        print(e)
        sys.exit(1)

    # Step 2: Capture one frame from webcam
    frame = capture_frame_from_webcam(camera_index=0)
    if frame is None:
        print("Quit without capture.")
        return

    # Step 3: Send frame to Face++ and get JSON back
    print("Sending frame to Face++ (US) gesture API...")
    payload = post_to_facepp_gesture(api_key, api_secret, frame)

    # Step 4: Print result in a friendly way
    pretty_print_gesture_result(payload)


if __name__ == "__main__":
    main()
