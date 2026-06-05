import cv2
import numpy as np
import os

# --- CONFIGURATION ---
# Make sure this matches your sky_watcher.py credentials and IP!
RTSP_URL = "rtsp://YOUR_TAPO_USERNAME:YOUR_TAPO_PASSWORD@YOUR_CAMERA_IP:554/stream2"
MASK_OUTPUT_PATH = "sky_mask.png"

# Global variables to track mouse state
drawing = False
brush_size = 30  # Size of your eraser brush in pixels

def fetch_live_frame():
    """Connects to the Tapo camera and grabs a single fresh frame."""
    print("Connecting to Taco Sam live feed...")
    cap = cv2.VideoCapture(RTSP_URL)
    ret, frame = cap.read()
    cap.release()
    return ret, frame

def main():
    ret, img = fetch_live_frame()
    if not ret:
        print("❌ Error: Could not fetch a live frame from the camera.")
        print("Please check your network connection, IP, and credentials.")
        return

    h, w = img.shape[:2]
    
    # Initialize a clean white mask canvas (255 = white = watch area)
    mask = np.ones((h, w), dtype=np.uint8) * 255
    
    # Pre-mask the top-left clock area automatically (set to 0 = black = ignore)
    cv2.rectangle(mask, (0, 0), (int(w * 0.4), int(h * 0.12)), 0, -1)

    # Create a visual blend so the user can see the mask overlay on the live video
    # We will tint masked areas with a translucent red color
    def update_display():
        overlay = img.copy()
        # Anywhere the mask is black (0), make it red in the display overlay
        overlay[mask == 0] = [0, 0, 255] 
        # Blend the original image and the red overlay together
        return cv2.addWeighted(img, 0.7, overlay, 0.3, 0)

    global drawing
    drawing = False

    def paint_mask_callback(event, x, y, flags, param):
        global drawing
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            # Change the last 0 to (0,) so Pylance sees it as a proper Scalar tuple
            cv2.circle(mask, (x, y), brush_size, (0,), -1)
        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            cv2.circle(mask, (x, y), brush_size, (0,), -1)
        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False

    # Set up the interactive Windows desktop display window
    window_name = "TacoCam Mask Painter"
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, paint_mask_callback)

    print("\n🖌️ INSTRUCTIONS:")
    print("1. Left-Click and Drag your mouse over the trees/houses to paint them RED.")
    print("2. Press 'S' to SAVE your mask and exit.")
    print("3. Press 'R' to RESET and start over.")
    print("4. Press 'ESC' to quit without saving.")

    while True:
        display_img = update_display()
        cv2.imshow(window_name, display_img)
        
        key = cv2.waitKey(30) & 0xFF
        if key == ord('s') or key == ord('S'):
            cv2.imwrite(MASK_OUTPUT_PATH, mask)
            print(f"\n💾 SUCCESS: Mask saved as '{MASK_OUTPUT_PATH}'!")
            break
        elif key == ord('r') or key == ord('R'):
            mask.fill(255) # Reset mask to pure white
            cv2.rectangle(mask, (0, 0), (int(w * 0.4), int(h * 0.12)), 0, -1) # Re-add clock protection
            print("🔄 Mask reset.")
        elif key == 27: # ESC key
            print("❌ Canceled. No mask was saved.")
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()