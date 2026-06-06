import cv2
import numpy as np
import time
import os
import logging
import base64
from collections import deque
from datetime import datetime, timedelta, timezone
from suntime import Sun
from flask import Flask, render_template, Response, send_from_directory, request

# --- CONFIGURATION MATCHES ---
RTSP_URL = "rtsp://YOUR_TAPO_USERNAME:YOUR_TAPO_PASSWORD@YOUR_CAMERA_IP:554/stream2"
SEGMENT_DURATION = 600  
MAX_SEGMENTS = 2        
OUTPUT_DIR = "./sky_buffer"
SNAPSHOT_BASE_DIR = "./snapshots"
MAX_STORAGE_BYTES = 2 * 1024 * 1024 * 1024 

LATITUDE = 43.7481            
LONGITUDE = -122.4645
BUFFER_MINUTES = 45           

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SNAPSHOT_BASE_DIR, exist_ok=True)

# --- WEB BACKEND OVERRIDE FLAGS ---
STREAM_LINK_ENABLED = False     # Toggled on/off via the dashboard play button
FORCE_TRACKING_ENABLED = False  # Toggled via the Daytime Override switch

app = Flask(__name__, template_folder=".")
latest_web_frame = None  
import threading
frame_lock = threading.Lock()

def is_dark_outside():
    if FORCE_TRACKING_ENABLED:
        return True
    local_hour = datetime.now().hour
    if local_hour >= 21 or local_hour < 4:  
        return True
    try:
        sun = Sun(LATITUDE, LONGITUDE)
        sunset_utc = sun.get_sunset_time()
        sunrise_utc = sun.get_sunrise_time()
        now_utc = datetime.now(timezone.utc)
        start_monitoring_utc = sunset_utc + timedelta(minutes=BUFFER_MINUTES)
        stop_monitoring_utc = sunrise_utc - timedelta(minutes=BUFFER_MINUTES)
        if start_monitoring_utc > sunrise_utc:  
            if now_utc >= start_monitoring_utc or now_utc <= stop_monitoring_utc:
                return True
        else:
            if start_monitoring_utc <= now_utc <= stop_monitoring_utc:
                return True
    except Exception:
        return True
    return False

def open_video_stream():
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;5000000"
    cap = cv2.VideoCapture(RTSP_URL)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    return cap

def run_master_loop():
    global latest_web_frame
    cap = None
    frame_history = deque(maxlen=5)
    
    active_event_frames = []
    active_event_coords = []
    event_start_time_local = None  
    last_detection_time = 0
    EVENT_TIMEOUT = 2.0  
    
    print("⏳ TacoSam Observatory Main background loop initiated.")

    while True:
        should_be_connected = STREAM_LINK_ENABLED or is_dark_outside()
        
        if should_be_connected:
            if cap is None or not cap.isOpened():
                print("🟢 Opening low-res RTSP Camera Network Stream Link...")
                cap = open_video_stream()
                if not cap.isOpened():
                    print("Error: RTSP connection failed. Retrying in 5s...")
                    time.sleep(5)
                    continue
            
            ret, frame = cap.read()
            if not ret:
                print("Stream dropped. Attempting automated reconnection...")
                if cap is not None:
                    cap.release()
                cap = None
                time.sleep(1)
                continue
                
            # Cache the latest frame to disk for Mask Painter backdrop canvas updates
            cv2.imwrite(os.path.join(SNAPSHOT_BASE_DIR, "latest_frame.jpg"), frame)

            # Compress and encode frame for real-time dashboard broadcast
            _, encoded_jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            with frame_lock:
                latest_web_frame = encoded_jpeg.tobytes()

            # COMPUTER VISION ANALYSIS GATEWAY
            if is_dark_outside():
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if os.path.exists("sky_mask.png"):
                    mask = cv2.imread("sky_mask.png", cv2.IMREAD_GRAYSCALE)
                    if mask is not None:
                        if mask.shape[:2] != gray.shape[:2]:
                            mask = cv2.resize(mask, (gray.shape[1], gray.shape[0]))
                        gray = cv2.bitwise_and(gray, gray, mask=mask)
                else:
                    h, w = gray.shape
                    gray[0:int(h * 0.15), 0:w] = 0

                gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)
                frame_history.append(gray_blur)

                detected_this_frame = False
                current_coords = None

                if len(frame_history) == 5:
                    frame_delta = cv2.absdiff(frame_history[0], frame_history[-1])
                    
                    # DAYTIME VS NIGHTTIME SENSITIVITY CALIBRATION
                    # If manually testing in daylight, use a much higher threshold (65) to ignore clouds
                    current_hour = datetime.now().hour
                    is_actually_daytime = not (current_hour >= 21 or current_hour < 4)
                    
                    sensitivity_threshold = 65 if (FORCE_TRACKING_ENABLED and is_actually_daytime) else 25
                    
                    _, thresh = cv2.threshold(frame_delta, sensitivity_threshold, 255, cv2.THRESH_BINARY)
                    kernel = np.ones((2,2), np.uint8)
                    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    for contour in contours:
                        area = cv2.contourArea(contour)
                        if 2 < area < 50:
                            (x, y), radius = cv2.minEnclosingCircle(contour)
                            current_coords = (int(x), int(y))
                            detected_this_frame = True
                            break 

                if detected_this_frame:
                    if len(active_event_frames) == 0:
                        event_start_time_local = time.time()
                    active_event_frames.append(frame.copy())
                    active_event_coords.append(current_coords)
                    last_detection_time = time.time()
                
                elif len(active_event_frames) > 0 and (time.time() - last_detection_time > EVENT_TIMEOUT):
                    total_frames = len(active_event_frames)
                    if total_frames > 3:
                        middle_index = total_frames // 2
                        snapshot_frame = active_event_frames[middle_index]
                        target_x, target_y = active_event_coords[middle_index]
                        
                        date_folder = time.strftime('%Y-%m-%d', time.localtime(event_start_time_local))
                        daily_dir = os.path.join(SNAPSHOT_BASE_DIR, date_folder)
                        os.makedirs(daily_dir, exist_ok=True)
                        
                        timestamp_file = time.strftime('%Y%m%d_%H%M%S', time.localtime(event_start_time_local))
                        timestamp_log = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event_start_time_local))
                        
                        cv2.rectangle(snapshot_frame, (target_x - 15, target_y - 15), (target_x + 15, target_y + 15), (0, 0, 255), 2)
                        snapshot_filename = f"event_{timestamp_file}.jpg"
                        snapshot_path = os.path.join(daily_dir, snapshot_filename)
                        
                        cv2.imwrite(snapshot_path, snapshot_frame)
                        print(f"📸 SNAPSHOT SAVED: {snapshot_filename}")
                        
                        with open("detections_log.txt", "a") as log_file:
                            log_file.write(f"{timestamp_log} | {date_folder}/{snapshot_filename} | Tracking duration: {total_frames} frames.\n")
                    
                    active_event_frames = []
                    active_event_coords = []
                    event_start_time_local = None

            time.sleep(0.01)
        else:
            if cap is not None:
                print("💤 Closing camera link. Network entering standby sleep mode.")
                cap.release()
                cap = None
            with frame_lock:
                latest_web_frame = None
            time.sleep(1)

# --- WEB SERVER ROUTING INTERACTION LAYER --

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sky_mask.png')
def get_current_mask():
    if os.path.exists("sky_mask.png"):
        return send_from_directory(".", "sky_mask.png", mimetype="image/png")
    return "No mask yet", 404

@app.route('/control')
def control():
    global STREAM_LINK_ENABLED, FORCE_TRACKING_ENABLED
    stream_param = request.args.get('stream')
    tracking_param = request.args.get('tracking')
    
    if stream_param == 'on': STREAM_LINK_ENABLED = True
    if stream_param == 'off': STREAM_LINK_ENABLED = False
    if tracking_param == 'force': FORCE_TRACKING_ENABLED = True
    if tracking_param == 'auto': FORCE_TRACKING_ENABLED = False
    return "OK"

@app.route('/save_mask', methods=['POST'])
def save_mask():
    data = request.json['image']
    # Extract the base64 raw binary bytes from the HTML Canvas transmission header
    header, encoded = data.split(',', 1)
    binary_data = base64.b64decode(encoded)
    
    # Temporarily read inside openCV, invert it so painted marks mask movement zones
    nparr = np.frombuffer(binary_data, np.uint8)
    mask_rgba = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    
    if mask_rgba is not None:
        # Extract alpha channel to read locations where the user painted strokes
        alpha_channel = mask_rgba[:, :, 3]
        _, binary_mask = cv2.threshold(alpha_channel, 10, 255, cv2.THRESH_BINARY_INV)
        cv2.imwrite("sky_mask.png", binary_mask)
        return "Saved"
    return "Error Processing Image", 400

@app.route('/detections_log.txt')
def get_log():
    if os.path.exists("detections_log.txt"):
        return send_from_directory(".", "detections_log.txt", mimetype="text/plain")
    return "", 404

@app.route('/snapshots/<path:filename>')
def get_snapshot(filename):
    return send_from_directory(os.path.abspath("./snapshots"), filename)

def generate_web_stream():
    global latest_web_frame
    while True:
        with frame_lock:
            frame_bytes = latest_web_frame
        if frame_bytes is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.05)
        else:
            time.sleep(0.2)

@app.route('/video_feed')
def video_feed():
    return Response(generate_web_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    tracker_thread = threading.Thread(target=run_master_loop, daemon=True)
    tracker_thread.start()
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)