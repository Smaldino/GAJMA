import cv2
import numpy as np
import os
import glob

def lock_panel_borders(video_path, start_frame_path, end_frame_path, output_path):
    """
    Freezes the black panel borders to eliminate Warping Error, 
    while allowing the AI's animation to play inside the panel.
    """
    # 1. Load the original Clean Canvas start/end frames
    start_img = cv2.imread(start_frame_path)
    end_img = cv2.imread(end_frame_path)
    
    if start_img is None or end_img is None:
        print(f"⛔ Error: Could not load original frames for {video_path}")
        return

    # 2. Create a Border Mask (Detect pure black/dark lines in the original frame)
    # Manga borders are typically very dark. We threshold to isolate them.
    gray_start = cv2.cvtColor(start_img, cv2.COLOR_BGR2GRAY)
    # Pixels darker than 40 are considered "borders"
    _, border_mask = cv2.threshold(gray_start, 40, 255, cv2.THRESH_BINARY_INV) 
    
    # Dilate slightly to catch anti-aliased (gray) edges around the ink
    kernel = np.ones((3, 3), np.uint8)
    border_mask = cv2.dilate(border_mask, kernel, iterations=1)
    
    # Normalize mask to [0.0, 1.0] and expand to 3 channels for blending
    mask_3ch = cv2.merge([border_mask, border_mask, border_mask]) / 255.0
    
    # 3. Read the AI-generated video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"⛔ Error: Could not open video {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 8.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Ensure original frames match video dimensions
    start_img = cv2.resize(start_img, (width, height))
    end_img = cv2.resize(end_img, (width, height))
    mask_3ch = cv2.resize(mask_3ch, (width, height))
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    
    frame_idx = 0
    print(f"🔒 Locking borders for {total_frames} frames...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Alpha Composite: Keep AI generation where mask=0, force original border where mask=1
        # We use the start_img border for the first half, end_img border for the second half
        if frame_idx < total_frames / 2:
            locked_frame = (frame * (1.0 - mask_3ch) + start_img * mask_3ch)
        else:
            locked_frame = (frame * (1.0 - mask_3ch) + end_img * mask_3ch)
            
        out.write(locked_frame.astype(np.uint8))
        frame_idx += 1
        
    cap.release()
    out.release()
    print(f"✅ Border-locked video saved to: {output_path}")

if __name__ == "__main__":
    # Example usage for testing locally
    VIDEO_IN = "path/to/generated_clean_canvas.mp4"
    START_IMG = "path/to/panel_001.png"
    END_IMG = "path/to/panel_002.png"
    VIDEO_OUT = "path/to/final_locked.mp4"
    
    if os.path.exists(VIDEO_IN):
        lock_panel_borders(VIDEO_IN, START_IMG, END_IMG, VIDEO_OUT)
    else:
        print("Update the paths in the __main__ block to test the script.")