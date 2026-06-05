# 🌮 TacoSam Sky Dashboard & Tracking Engine

An automated computer vision engine designed to track high-altitude objects (meteors, satellites, airplanes) against a clear sky window, while dynamically masking out wind-blown trees and structural obstructions. Includes a localized dark-mode web dashboard ledger sorted by calendar days.

---

## 🛠️ Mac Installation & Setup

Because macOS handles certain camera windows and python environments slightly differently than Windows, follow these quick steps to get running.

### 1. Install System Dependencies
Open your Mac Terminal and ensure you have Python 3 and the necessary system tools installed via Homebrew. If you don't have Homebrew, install it first from `brew.sh`.

```bash
# Update Homebrew
brew update

# Ensure FFmpeg is installed for smooth RTSP video streams
brew install ffmpeg

2. Install Python Packages
Navigate to this project directory in your terminal and install the required computer vision and calculation frameworks:

Bash
pip3 install opencv-python numpy suntime timezonefinder
🚀 How to Run the System
Step 1: Configure Your Camera Credentials
Because the core tracking and masking files are protected via .gitignore, you need to set up your own active local credential scripts from the templates provided:

Duplicate mask_painter_template.py and rename the copy to mask_painter.py.

Duplicate sky_watcher_template.py and rename the copy to sky_watcher.py.

Open both new files and update line 9 with your specific Tapo RTSP stream path:

Python
RTSP_URL = "rtsp://YOUR_USERNAME:YOUR_PASSWORD@YOUR_CAMERA_IP:554/stream2"
Step 2: Paint Your Custom Sky Mask
Before running the tracker, you need to block out tree clusters, houses, or string lights that might move in the wind and cause false positives.

Run the utility script:

Bash
python3 mask_painter.py
A live video window will appear. Left-click and drag your mouse over any ground objects or tree perimeters to paint them RED.

Once you have cleanly isolated your open window of clear sky, press the S key to save the mask layout and exit. This generates a local sky_mask.png asset.

Step 3: Launch the Tracking Engine
Open a terminal window and start the background computer vision analyzer:

Bash
python3 sky_watcher.py
💡 Note on Scheduling: By default, FORCE_RUN_FOR_TESTING is set to False. The script will automatically calculate your local solar coordinates, realize it's daytime, and enter a silent background sleep loop. It will automatically wake up and lock onto your live camera stream 45 minutes after sunset, then gracefully close down at dawn. If you want to test it against daytime birds, flip FORCE_RUN_FOR_TESTING = True on line 18.

Step 4: Open Your Local Command Deck
Open a second separate terminal window (or split your VS Code terminal) to run the lightweight local asset server:

Bash
python3 dashboard_server.py
Now, open any web browser on your Mac and navigate to:
👉 http://localhost:5000

📊 Features & Space Optimization
Rolling Buffer: The script continuously records rolling 10-minute dashcam segments (segment_1.mp4 / segment_2.mp4) inside the sky_buffer folder. It safely auto-recycles itself so your Mac storage never fills up.

Auto-Archiving Snapshot Engine: When an object crosses your unmasked sky, the code tracks it frame-by-frame, extracts the mathematical median frame, draws a red target box around it, and logs it by calendar folder paths (snapshots/YYYY-MM-DD/).

Auto-Recycle: The snapshots folder features a built-in safety sweep that automatically recycles the oldest images if the folder footprint crosses 2 GB (roughly 45,000 captures).

Historical Calendar Filtering: Use the calendar input box at the top of the webpage to quickly jump back and audit detections from previous nights when you've been away from your desk.