"""
Simple test to check if volume control works on your system
"""

from pynput.keyboard import Controller, Key
import time

keyboard = Controller()

print("Testing volume control...")
print("Press Ctrl+C to stop")
print()

for i in range(5):
    print(f"Pressing Volume UP... ({i+1}/5)")
    keyboard.press(Key.media_volume_up)
    keyboard.release(Key.media_volume_up)
    time.sleep(1)

print("\nDone! Did your volume increase?")
print("If not, your system might not support media keys via pynput.")
