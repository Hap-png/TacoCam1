🚀 How to Run the System
------------------------

### Step 1: Configure Your Personal Settings
Because your live settings file is protected from accidental commits via `.gitignore`, you need to initialize your local configuration parameters from the template:

1. Duplicate `settings_template.json` and rename the copy to exactly `settings.json`.
2. Open your new `settings.json` file and fill in your unique network, camera, and operational values:

```json
{
  "camera_ip": "192.168.X.X",
  "camera_user": "your_camera_username",
  "camera_pass": "your_camera_password",
  "latitude": 44.0000,
  "longitude": -123.0000,
  "min_object_size": 2,
  "max_object_size": 50,
  "tracking_engine_enabled": true,
  "sensitivity_threshold": 35,
  "start_hour": 21, 
  "end_hour": 4     
}
Note: Your sky_watcher.py engine will automatically read these variables at boot and securely construct your RTSP camera stream link in memory without ever hardcoding your passwords into the source files!

Step 2: Launch the Integrated Control Deck
Open a single terminal window and start the master background loop and web server using Python 3:

Bash
python3 sky_watcher.py
Step 3: Access Your Dashboard & Mask Painter
Open any web browser and navigate to:
👉 http://localhost:5000

Go to the Mask Painter tab.

Turn your stream connection LIVE to pull a baseline template frame.

Use the brush tool to paint out any unwanted moving tree clusters, houses, or horizon power lines.

Click 💾 Save & Apply New Mask to commit the layout directly to sky_mask.png.

🌙 Note on Scheduling & Testing
By default, the script operates on a predictable Manual Clock Schedule defined entirely inside your settings.json config file (start_hour and end_hour using a 24-hour clock).

Daytime Standby: Outside of tracking hours, the system enters a silent background sleep loop, completely disconnecting the camera feed to save network bandwidth and CPU cycles.

Nighttime Tracking: The system automatically initializes the live camera stream link exactly at your designated start_hour (e.g., 21 for 9:00 PM) and tracks until your end_hour (e.g., 4 for 4:00 AM).

Forced Manual Testing: If you want to bypass the timer block to test settings or capture daytime motion (birds, planes), toggle the mode button on the dashboard interface to FORCE TRACKING.