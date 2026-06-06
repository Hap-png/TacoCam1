# 🌮 TacoSam Sky Dashboard & Tracking Engine

An automated computer vision engine designed to track high-altitude objects (meteors, satellites, airplanes) against a clear sky window, while dynamically masking out wind-blown trees and structural obstructions. Includes a localized dark-mode web dashboard ledger sorted by calendar days.

---

## 💻 Mac Installation & Setup

Because macOS handles python environments and system binaries differently than Windows, follow these quick steps to get running on a Mac.

### 1. Install System Dependencies
Open your Mac Terminal and ensure you have Python 3 and the necessary system tools installed via Homebrew. If you don't have Homebrew installed yet, grab it from `brew.sh`.

```bash
# Update Homebrew
brew update

# Ensure FFmpeg is installed for smooth RTSP video stream processing
brew install ffmpeg

2. Install Python Packages
Navigate to this project directory in your Mac terminal and install the required computer vision and calculation frameworks using pip3:

Bash
pip3 install opencv-python numpy suntime timezonefinder flask
🚀 How to Run the System
Step 1: Configure Your Camera Credentials
Because the active tracking file is protected via .gitignore, set up your local tracking script from the template provided:

Duplicate sky_watcher_template.py and rename the copy to sky_watcher.py.

Open your new sky_watcher.py file and update the RTSP line with your specific Tapo stream path:

Python
RTSP_URL = "rtsp://YOUR_USERNAME:YOUR_PASSWORD@YOUR_CAMERA_IP:554/stream2"
Step 2: Launch the Integrated Control Deck
Open a single terminal window and start the master background loop and web server using Python 3:

Bash
python3 sky_watcher.py
Step 3: Access Your Dashboard & Mask Painter
Open any web browser and navigate to:
👉 http://localhost:5000

Go to the Mask Painter tab.

Turn your stream connection LIVE to pull a daytime base template frame.

If you have an existing mask file on disk, click the gold 🎨 Apply Existing Mask Overlay button to load your trees and boundaries instantly.

Use the brush tool to paint out any unwanted moving tree clusters, houses, or horizon lights.

Click 💾 Save & Apply New Mask to commit the layout directly to sky_mask.png.

🌙 Note on Scheduling & Testing
By default, the script automatically calculates your local solar coordinates based on your position.

Daytime: It enters a silent background sleep loop to save CPU cycles.

Nighttime: It automatically wakes up and locks onto your live camera stream 45 minutes after sunset, gracefully closing down at dawn.

Bird & Daytime Testing: If you want to force the engine to stay active during the day (to track daytime birds or test your settings), toggle the mode button on the dashboard interface to FORCE TRACKING.

📦 Features & Space Optimization
Rolling Buffer: The script continuously records rolling 10-minute dashcam segments inside the sky_buffer folder, automatically recycling itself so storage never fills up.

Auto-Archiving Snapshot Engine: When an object crosses your unmasked sky, the code tracks it frame-by-frame, draws a red target box around it, and logs it into the snapshots/ folder.

Auto-Recycle Guard: Features a built-in safety sweep that automatically recycles the oldest images if the folder footprint crosses 2.0 GB.

Historical Calendar Filtering: Use the calendar input box at the top of the webpage to quickly jump back and audit detections from previous nights.