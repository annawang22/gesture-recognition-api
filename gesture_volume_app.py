"""
Gesture Volume Control - Beautiful Desktop App
A sleek, modern interface for controlling your computer's volume with hand gestures.
"""

import sys
import json
import time
import platform
import subprocess
import threading
from pathlib import Path
from datetime import datetime

import cv2
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk


# Face++ Configuration
FACEPP_US_GESTURE_URL = "https://api-us.faceplusplus.com/humanbodypp/v1/gesture"
KEYS_FILE = "facepp_keys.txt"
API_CALL_INTERVAL = 2.0
COOLDOWN_PERIOD = 1.0


class GestureVolumeApp:
    """Beautiful gesture-controlled volume application"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Gesture Volume Control")
        self.root.geometry("900x650")
        self.root.resizable(False, False)
        
        # State variables
        self.is_running = False
        self.camera = None
        self.api_key = None
        self.api_secret = None
        self.last_api_call = 0
        self.last_trigger_time = 0
        self.stats = {
            'gestures_detected': 0,
            'volume_changes': 0,
            'session_start': None
        }
        
        # Setup UI
        self.setup_styles()
        self.create_ui()
        self.load_credentials()
        
    def setup_styles(self):
        """Configure modern color scheme and styles"""
        # Color palette - soft, modern aesthetic
        self.colors = {
            'bg_primary': '#0F172A',      # Deep slate
            'bg_secondary': '#1E293B',    # Lighter slate
            'bg_card': '#334155',         # Card background
            'accent': '#3B82F6',          # Bright blue
            'accent_hover': '#2563EB',    # Darker blue
            'success': '#10B981',         # Green
            'warning': '#F59E0B',         # Amber
            'text_primary': '#F8FAFC',    # Almost white
            'text_secondary': '#94A3B8',  # Gray
            'border': '#475569'           # Border gray
        }
        
        self.root.configure(bg=self.colors['bg_primary'])
        
        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Button style
        style.configure(
            'Accent.TButton',
            background=self.colors['accent'],
            foreground=self.colors['text_primary'],
            borderwidth=0,
            focuscolor='none',
            font=('Segoe UI', 11, 'bold'),
            padding=(20, 12)
        )
        style.map('Accent.TButton',
            background=[('active', self.colors['accent_hover'])]
        )
        
    def create_ui(self):
        """Build the modern UI layout"""
        # Main container
        main_frame = tk.Frame(self.root, bg=self.colors['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Header
        self.create_header(main_frame)
        
        # Content area (camera + stats)
        content_frame = tk.Frame(main_frame, bg=self.colors['bg_primary'])
        content_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # Left: Camera preview
        self.create_camera_section(content_frame)
        
        # Right: Stats and controls
        self.create_stats_section(content_frame)
        
        # Footer with start/stop button
        self.create_controls(main_frame)
        
    def create_header(self, parent):
        """Create app header with title"""
        header = tk.Frame(parent, bg=self.colors['bg_primary'])
        header.pack(fill=tk.X)
        
        # Title with emoji
        title = tk.Label(
            header,
            text="👋 Gesture Volume Control",
            font=('Segoe UI', 28, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_primary']
        )
        title.pack(anchor='w')
        
        # Subtitle
        subtitle = tk.Label(
            header,
            text="Control your volume with hand gestures",
            font=('Segoe UI', 12),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_primary']
        )
        subtitle.pack(anchor='w', pady=(5, 0))
        
    def create_camera_section(self, parent):
        """Create camera preview area"""
        camera_frame = tk.Frame(parent, bg=self.colors['bg_primary'])
        camera_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        # Camera card
        card = tk.Frame(
            camera_frame,
            bg=self.colors['bg_secondary'],
            highlightbackground=self.colors['border'],
            highlightthickness=1
        )
        card.pack(fill=tk.BOTH, expand=True)
        
        # Camera label
        self.camera_label = tk.Label(
            card,
            bg=self.colors['bg_secondary'],
            fg=self.colors['text_secondary'],
            font=('Segoe UI', 14),
            compound='none'  # Don't show text with images
        )
        self.camera_label.pack(expand=True, padx=20, pady=20)
        
        # Default message
        self.show_camera_placeholder()
        
    def create_stats_section(self, parent):
        """Create statistics and info panel"""
        stats_frame = tk.Frame(parent, bg=self.colors['bg_primary'])
        stats_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        
        # Stats card
        card = tk.Frame(
            stats_frame,
            bg=self.colors['bg_secondary'],
            highlightbackground=self.colors['border'],
            highlightthickness=1,
            width=280
        )
        card.pack(fill=tk.BOTH, expand=True)
        card.pack_propagate(False)
        
        # Card title
        title = tk.Label(
            card,
            text="Session Stats",
            font=('Segoe UI', 16, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_secondary']
        )
        title.pack(anchor='w', padx=20, pady=(20, 15))
        
        # Status indicator
        self.status_frame = tk.Frame(card, bg=self.colors['bg_secondary'])
        self.status_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        self.status_dot = tk.Canvas(
            self.status_frame,
            width=12,
            height=12,
            bg=self.colors['bg_secondary'],
            highlightthickness=0
        )
        self.status_dot.pack(side=tk.LEFT, padx=(0, 8))
        self.status_dot.create_oval(2, 2, 10, 10, fill=self.colors['text_secondary'], outline='')
        
        self.status_label = tk.Label(
            self.status_frame,
            text="Inactive",
            font=('Segoe UI', 11),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_secondary']
        )
        self.status_label.pack(side=tk.LEFT)
        
        # Separator
        sep = tk.Frame(card, bg=self.colors['border'], height=1)
        sep.pack(fill=tk.X, padx=20, pady=15)
        
        # Stats items
        self.gestures_label = self.create_stat_item(card, "👍 Gestures Detected", "0")
        self.volume_label = self.create_stat_item(card, "🔊 Volume Changes", "0")
        self.uptime_label = self.create_stat_item(card, "⏱️ Session Time", "00:00")
        
        # Separator
        sep2 = tk.Frame(card, bg=self.colors['border'], height=1)
        sep2.pack(fill=tk.X, padx=20, pady=15)
        
        # Instructions
        instructions = tk.Label(
            card,
            text="How to use:",
            font=('Segoe UI', 12, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_secondary']
        )
        instructions.pack(anchor='w', padx=20, pady=(10, 5))
        
        inst_text = tk.Label(
            card,
            text="• Click 'Start Detection'\n• Show thumbs up 👍\n• Volume increases!",
            font=('Segoe UI', 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_secondary'],
            justify=tk.LEFT
        )
        inst_text.pack(anchor='w', padx=20)
        
    def create_stat_item(self, parent, label, value):
        """Create a stat display item"""
        frame = tk.Frame(parent, bg=self.colors['bg_secondary'])
        frame.pack(fill=tk.X, padx=20, pady=8)
        
        label_widget = tk.Label(
            frame,
            text=label,
            font=('Segoe UI', 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_secondary']
        )
        label_widget.pack(anchor='w')
        
        value_widget = tk.Label(
            frame,
            text=value,
            font=('Segoe UI', 18, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_secondary']
        )
        value_widget.pack(anchor='w', pady=(2, 0))
        
        return value_widget
        
    def create_controls(self, parent):
        """Create control buttons"""
        controls = tk.Frame(parent, bg=self.colors['bg_primary'])
        controls.pack(fill=tk.X, pady=(20, 0))
        
        self.start_button = ttk.Button(
            controls,
            text="Start Detection",
            style='Accent.TButton',
            command=self.toggle_detection
        )
        self.start_button.pack(fill=tk.X)
        
    def show_camera_placeholder(self):
        """Show placeholder when camera is off"""
        self.camera_label.configure(
            text="📷\n\nCamera Inactive\n\nClick 'Start Detection' to begin",
            font=('Segoe UI', 14)
        )
        
    def load_credentials(self):
        """Load Face++ API credentials"""
        try:
            p = Path(KEYS_FILE)
            if not p.exists():
                return
            
            lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if len(lines) >= 2:
                self.api_key, self.api_secret = lines[0], lines[1]
        except Exception as e:
            print(f"Error loading credentials: {e}")
            
    def toggle_detection(self):
        """Start or stop gesture detection"""
        if not self.is_running:
            self.start_detection()
        else:
            self.stop_detection()
            
    def start_detection(self):
            """Start the gesture detection system"""
            if not self.api_key or not self.api_secret:
                messagebox.showerror(
                    "API Keys Missing",
                    f"Please create '{KEYS_FILE}' with your Face++ API credentials.\n\n"
                    "Line 1: API_KEY\nLine 2: API_SECRET"
                )
                return
                
            try:
                # Initialize camera hardware
                self.camera = cv2.VideoCapture(0)
                if not self.camera.isOpened():
                    raise RuntimeError("Could not open webcam or camera is being used by another app.")
                    
                # Set operational states
                self.is_running = True
                self.current_frame = None  # Shared resource for the detection thread
                self.stats['session_start'] = time.time()
                self.stats['gestures_detected'] = 0
                self.stats['volume_changes'] = 0
                
                # Update UI elements
                self.start_button.configure(text="Stop Detection")
                self.update_status(True)
                
                # 1. Start background thread for API calls
                thread = threading.Thread(target=self.detection_loop, daemon=True)
                thread.start()
                
                # 2. Start the UI recursive loops
                self.update_camera_feed()  # Handles frame captures and display
                self.update_stats()        # Handles session timer and counters
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start: {e}")
                self.stop_detection()
            
    def stop_detection(self):
        """Stop gesture detection"""
        self.is_running = False
        
        if self.camera:
            self.camera.release()
            self.camera = None
            
        self.start_button.configure(text="Start Detection")
        self.update_status(False)
        self.show_camera_placeholder()
        
    def update_status(self, active):
        """Update status indicator"""
        if active:
            self.status_dot.itemconfig(1, fill=self.colors['success'])
            self.status_label.configure(
                text="Active",
                fg=self.colors['success']
            )
        else:
            self.status_dot.itemconfig(1, fill=self.colors['text_secondary'])
            self.status_label.configure(
                text="Inactive",
                fg=self.colors['text_secondary']
            )
            
    def detection_loop(self):
        """Main detection loop - now uses the frame from the UI thread"""
        while self.is_running:
            current_time = time.time()
            
            # Check if it's time to call API and if we have a frame available
            if (current_time - self.last_api_call >= API_CALL_INTERVAL and 
                hasattr(self, 'current_frame')):
                
                self.last_api_call = current_time
                # Use the frame stored by the camera update function
                payload = self.call_gesture_api(self.current_frame)
                
                if self.detect_thumbs_up(payload):
                    self.stats['gestures_detected'] += 1
                    
                    if current_time - self.last_trigger_time >= COOLDOWN_PERIOD:
                        self.increase_volume()
                        self.stats['volume_changes'] += 1
                        self.last_trigger_time = current_time
                                    
            time.sleep(0.1)
            
    def update_camera_feed(self):
        """Update camera preview and store current frame for API"""
        if self.is_running and self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                # Store the raw frame for the detection thread to use
                self.current_frame = frame.copy()
                
                # Convert BGR to RGB for Tkinter
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize
                h, w = frame_rgb.shape[:2]
                target_w = 600
                target_h = int(h * (target_w / w))
                frame_resized = cv2.resize(frame_rgb, (target_w, target_h))
                
                # Update Image
                img = Image.fromarray(frame_resized)
                photo = ImageTk.PhotoImage(image=img)
                self.camera_label.configure(image=photo)
                self.camera_label.image = photo
                
            self.root.after(30, self.update_camera_feed)
        else:
            self.show_camera_placeholder()

            
    def update_stats(self):
        """Update statistics display"""
        if self.is_running:
            # Update gesture count
            self.gestures_label.configure(text=str(self.stats['gestures_detected']))
            
            # Update volume changes
            self.volume_label.configure(text=str(self.stats['volume_changes']))
            
            # Update uptime
            if self.stats['session_start']:
                elapsed = int(time.time() - self.stats['session_start'])
                minutes = elapsed // 60
                seconds = elapsed % 60
                self.uptime_label.configure(text=f"{minutes:02d}:{seconds:02d}")
                
            self.root.after(1000, self.update_stats)  # Update every second
            
    def call_gesture_api(self, frame):
        """Call Face++ API"""
        try:
            ok, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            if not ok:
                return None
                
            files = {"image_file": ("frame.jpg", jpg.tobytes(), "image/jpeg")}
            data = {"api_key": self.api_key, "api_secret": self.api_secret}
            
            resp = requests.post(FACEPP_US_GESTURE_URL, data=data, files=files, timeout=10)
            payload = resp.json()
            
            if resp.status_code == 200 and "error_message" not in payload:
                return payload
        except:
            pass
        return None
        
    def detect_thumbs_up(self, payload):
        """Check for thumbs up gesture"""
        if not payload:
            return False
            
        hands = payload.get("hands") or []
        if isinstance(hands, dict):
            hands = hands.get("hands", [])
            
        for hand in hands:
            gesture = hand.get("gesture") or {}
            if isinstance(gesture, dict):
                if gesture.get("thumb_up", 0) > 50:
                    return True
        return False
        
    def increase_volume(self):
        """Increase system volume"""
        system = platform.system()
        try:
            if system == "Windows":
                script = '$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]175)'
                subprocess.run(["powershell", "-Command", script], check=True, capture_output=True)
            elif system == "Darwin":
                subprocess.run(["osascript", "-e", 
                    "set volume output volume (output volume of (get volume settings) + 10)"], 
                    check=True)
            elif system == "Linux":
                try:
                    subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "5%+"], 
                        check=True, capture_output=True)
                except:
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"], 
                        check=True, capture_output=True)
        except:
            pass


def main():
    """Launch the application"""
    root = tk.Tk()
    app = GestureVolumeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()