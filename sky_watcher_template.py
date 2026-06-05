import cv2
import numpy as np
import time
import os
from collections import deque
from datetime import datetime, timedelta
from suntime import Sun
from timezonefinder import TimezoneFinder

# --- CONFIGURATION ---
RTSP_URL = "rtsp://YOUR_TAPO_USERNAME:YOUR_TAPO_PASSWORD@YOUR_CAMERA_IP:554/stream2"
SEGMENT_DURATION = 600  
MAX_SEGMENTS = 2        
OUTPUT_DIR = "./sky_buffer"
SNAPSHOT_BASE_DIR = "./snapshots"
MAX_STORAGE_BYTES = 2 * 1024 * 1024 * 1024 # 2 Gigabytes

# --- AUTOMATED SCHEDULING CONFIG ---
FORCE_RUN_FOR_TESTING = False  
LATITUDE = 43.7481            
LONGITUDE = -122.4645
BUFFER_MINUTES = 45           

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SNAPSHOT_BASE_DIR, exist_ok=True)

def is_dark_outside():
    if FORCE_RUN_FOR_TESTING:
        return True
    sun = Sun(LATITUDE, LONGITUDE)
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lng=LONGITUDE, lat=LATITUDE)
    now = datetime.now()
    try:
        today_sunset = sun.get_local_sunset_time(now)
        today_sunrise = sun.get_local_sunrise_time(now)
    except Exception:
        return True

    start_monitoring = today_sunset + timedelta(minutes=BUFFER_MINUTES)
    stop_monitoring = today_sunrise - timedelta(minutes=BUFFER_MINUTES)

    if start_monitoring > today_sunrise:  
        if now >= start_monitoring or now <= stop_monitoring:
            return True
    else:
        if start_monitoring <= now <= stop_monitoring:
            return True
    return False

def enforce_storage_limit():
    """Scans the entire snapshots directory tree and deletes oldest files if total size > 2GB."""
    all_files = []
    total_size = 0
    
    # Walk through all subdirectories (calendar days)
    for root, dirs, files in os.walk(SNAPSHOT_BASE_DIR):
        for file in files:
            if file.endswith('.jpg'):
                file_path = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(file_path)
                    all_files.append((file_path, os.path.getmtime(file_path), file_size))
                    total_size += file_size
                except os.error:
                    continue

    # If we are over our 2GB limit, sort by modification time (oldest first) and delete
    if total_size > MAX_STORAGE_BYTES:
        all_files.sort(key=lambda x: x[1])
        print(f"⚠️ Storage limit warning! Total snapshot size is {total_size / (1024*1024):.2f} MB.")
        
        for file_path, _, file_size in all_files:
            try:
                os.remove(file_path)
                total_size -= file_size
                print(f"🗑️ Recycled oldest snapshot: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
                
            if total_size <= MAX_STORAGE_BYTES:
                print("✅ Storage usage optimized below 2GB limit.")
                break

def open_video_stream():
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;5000000"
    cap = cv2.VideoCapture(RTSP_URL)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    return cap

def main():
    print("⏳ Sky Watcher Initialized. Checking schedule...")
    while True:
        if is_dark_outside():
            print("🌌 Night window active! Starting camera stream...")
            run_tracker()
        else:
            print(f"☀️ Daytime detected. Sleeping for 5 minutes... (Current time: {datetime.now().strftime('%H:%M:%S')})")
            time.sleep(300)

def run_tracker():
    cap = open_video_stream()
    if not cap.isOpened():
        print("Error: Could not connect to Tapo stream.")
        return

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
    fourcc = cv2.VideoWriter.fourcc(*'mp4v')

    segment_id = 1
    start_time = time.time()
    
    video_path = os.path.join(OUTPUT_DIR, f"segment_{segment_id}.mp4")
    out = cv2.VideoWriter(video_path, fourcc, fps, (frame_width, frame_height))
    frame_history = deque(maxlen=5)

    active_event_frames = []
    active_event_coords = []
    last_detection_time = 0
    EVENT_TIMEOUT = 2.0  

    print("🟢 Tracking active. Monitoring for meteors, satellites, and planes...")

    try:
        while cap.isOpened():
            current_time = time.time()
            
            if current_time - start_time > SEGMENT_DURATION:
                out.release()
                if not is_dark_outside():
                    print("🌅 Sunrise window approaching. Shutting down stream for the day.")
                    break
                segment_id = 2 if segment_id == 1 else 1
                video_path = os.path.join(OUTPUT_DIR, f"segment_{segment_id}.mp4")
                out = cv2.VideoWriter(video_path, fourcc, fps, (frame_width, frame_height))
                start_time = current_time
                print(f"🔄 Rotating buffer to segment_{segment_id}.mp4")

            ret, frame = cap.read()
            if not ret:
                print("Stream dropped. Reconnecting...")
                time.sleep(2)
                cap = open_video_stream()
                continue

            out.write(frame)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if os.path.exists("sky_mask.png"):
                mask = cv2.imread("sky_mask.png", cv2.IMREAD_GRAYSCALE)
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
                _, thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)
                
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
                active_event_frames.append(frame.copy())
                active_event_coords.append(current_coords)
                last_detection_time = current_time
            
            elif len(active_event_frames) > 0 and (current_time - last_detection_time > EVENT_TIMEOUT):
                total_frames = len(active_event_frames)
                
                if total_frames > 3:
                    middle_index = total_frames // 2
                    snapshot_frame = active_event_frames[middle_index]
                    target_x, target_y = active_event_coords[middle_index]
                    
                    # Date formatting for nested folder structure
                    date_folder = time.strftime('%Y-%m-%d', time.localtime(last_detection_time))
                    daily_dir = os.path.join(SNAPSHOT_BASE_DIR, date_folder)
                    os.makedirs(daily_dir, exist_ok=True)
                    
                    timestamp_file = time.strftime('%Y%m%d_%H%M%S', time.localtime(last_detection_time))
                    timestamp_log = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_detection_time))
                    
                    cv2.rectangle(snapshot_frame, (target_x - 15, target_y - 15), (target_x + 15, target_y + 15), (0, 0, 255), 2)
                    
                    snapshot_filename = f"event_{timestamp_file}.jpg"
                    # Path now incorporates the daily calendar subfolder
                    relative_path = f"{date_folder}/{snapshot_filename}"
                    snapshot_path = os.path.join(daily_dir, snapshot_filename)
                    
                    cv2.imwrite(snapshot_path, snapshot_frame)
                    print(f"📸 SNAPSHOT SAVED: {relative_path} ({total_frames} frames)")
                    
                    with open("detections_log.txt", "a") as log_file:
                        log_file.write(f"{timestamp_log} | {relative_path} | Tracking duration: {total_frames} frames.\n")
                    
                    # Run our maintenance engine to clear out space if needed
                    enforce_storage_limit()
                
                active_event_frames = []
                active_event_coords = []

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nStopping Sky Watcher gracefully...")
        raise KeyboardInterrupt
    finally:
        cap.release()
        out.release()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Goodbye!")