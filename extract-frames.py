import cv2
import numpy as np
from pathlib import Path

# ==========================================
# CONFIGURATION (UPDATE THESE PATHS)
# ==========================================
NAIVE_VIDEO = r"data\videos\z-others\final_compilation\Full_Manga_Animation_32fps.mp4"
PROPOSED_VIDEO = r"data\videos\TetsuSan\Dolly_Bokeh\final_compilation\Dolly_Bokeh_Final_32fps.mp4"

OUTPUT_DIR = Path("thesis_screenshots")
OUTPUT_DIR.mkdir(exist_ok=True)
OUT_NAME = "16_frame_cropped_ablation"

NUM_FRAMES_TO_EXTRACT = 16
AUTO_CROP_WHITE_BORDERS = True

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_video_metadata(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return total_frames, fps

def get_crop_box(video_path):
    """Analyzes the first frame to find the bounding box of the actual manga panel (ignoring white padding)."""
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return (0, 0, 100, 100) # Fallback
        
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # White padding is usually very bright (>230). Manga ink/screentones are darker.
    _, thresh = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY_INV)
    coords = cv2.findNonZero(thresh)
    
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        margin = 5 # Small margin so we don't clip the crisp panel border
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(frame.shape[1], x + w + margin)
        y2 = min(frame.shape[0], y + h + margin)
        return (x1, y1, x2, y2)
        
    return (0, 0, frame.shape[1], frame.shape[0])

def add_label(frame, text, color_bgr):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    # Dynamically scale banner height based on cropped frame size
    banner_h = min(45, h // 5) 
    cv2.rectangle(overlay, (0, 0), (w, banner_h), color_bgr, -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    
    # Dynamically scale font size
    font_scale = min(0.8, banner_h / 50.0)
    cv2.putText(frame, text, (10, banner_h - 10), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 2, cv2.LINE_AA)
    return frame

# ==========================================
# MAIN LOGIC
# ==========================================
def main():
    print("📊 Analyzing video metadata...")
    try:
        naive_frames, naive_fps = get_video_metadata(NAIVE_VIDEO)
        prop_frames, prop_fps = get_video_metadata(PROPOSED_VIDEO)
    except ValueError as e:
        print(f"❌ Error: {e}")
        return

    total_frames = min(naive_frames, prop_frames)
    fps = naive_fps 
    
    print(f"🎬 Naive: {naive_frames} frames | Proposed: {prop_frames} frames | FPS: {fps:.2f}")
    
    # Calculate 16 evenly spaced indices
    target_indices = [int(i * (total_frames - 1) / (NUM_FRAMES_TO_EXTRACT - 1)) for i in range(NUM_FRAMES_TO_EXTRACT)]
    target_indices = sorted(list(set(target_indices)))
    
    # Get Auto-Crop Box
    crop_box = (0, 0, 1000, 1000) # dummy init
    if AUTO_CROP_WHITE_BORDERS:
        print("✂️ Calculating auto-crop box to remove white padding...")
        crop_box = get_crop_box(NAIVE_VIDEO)
        print(f"   Crop region (x1, y1, x2, y2): {crop_box}")

    # Create folder for individual frames
    SINGULAR_DIR = OUTPUT_DIR / "singular_frames"
    SINGULAR_DIR.mkdir(exist_ok=True)
    print(f"📂 Individual frames will be saved to: {SINGULAR_DIR}")

    print(f"📸 Extracting and cropping {len(target_indices)} frames...")
    cap_n = cv2.VideoCapture(NAIVE_VIDEO)
    cap_p = cv2.VideoCapture(PROPOSED_VIDEO)

    rows = []
    
    for idx, f_num in enumerate(target_indices):
        cap_n.set(cv2.CAP_PROP_POS_FRAMES, f_num)
        ret_n, frame_n = cap_n.read()
        
        cap_p.set(cv2.CAP_PROP_POS_FRAMES, f_num)
        ret_p, frame_p = cap_p.read()
        
        if not ret_n or not ret_p:
            continue
            
        # Apply Auto-Crop
        x1, y1, x2, y2 = crop_box
        frame_n = frame_n[y1:y2, x1:x2]
        frame_p = frame_p[y1:y2, x1:x2]
        
        # Ensure both frames have the exact same dimensions after crop (safety check)
        h = min(frame_n.shape[0], frame_p.shape[0])
        w = min(frame_n.shape[1], frame_p.shape[1])
        frame_n = cv2.resize(frame_n, (w, h))
        frame_p = cv2.resize(frame_p, (w, h))
        
        timestamp = f_num / fps if fps > 0 else 0
        
        label_n = f"Naive (Raw Text) | Frame {f_num} ({timestamp:.2f}s)"
        label_p = f"Proposed (Clean Canvas) | Frame {f_num} ({timestamp:.2f}s)"
        
        frame_n = add_label(frame_n, label_n, (0, 0, 180))
        frame_p = add_label(frame_p, label_p, (0, 150, 0))
        
        # ==========================================
        # 💾 SAVE INDIVIDUAL FRAMES
        # ==========================================
        naive_out = SINGULAR_DIR / f"{idx:02d}_naive_frame{f_num:04d}_{timestamp:.2f}s.png"
        prop_out = SINGULAR_DIR / f"{idx:02d}_proposed_frame{f_num:04d}_{timestamp:.2f}s.png"
        cv2.imwrite(str(naive_out), frame_n)
        cv2.imwrite(str(prop_out), frame_p)
        
        # Stitch horizontally for the master timeline grid
        divider = np.ones((h, 4, 3), dtype=np.uint8) * 255
        row = np.hstack((frame_n, divider, frame_p))
        rows.append(row)

    cap_n.release()
    cap_p.release()
    
    if not rows:
        print("❌ No frames extracted.")
        return

    # ==========================================
    # 💾 SAVE MASTER TIMELINE GRID
    # ==========================================
    h_row, w_row = rows[0].shape[:2]
    h_divider = np.ones((4, w_row, 3), dtype=np.uint8) * 255
    
    final_grid = []
    for i, row in enumerate(rows):
        final_grid.append(row)
        if i < len(rows) - 1:
            final_grid.append(h_divider)
            
    final_image = np.vstack(final_grid)
    
    out_path = OUTPUT_DIR / f"{OUT_NAME}.png"
    cv2.imwrite(str(out_path), final_image)
    
    print(f"\n🎉 SUCCESS!")
    print(f"🖼️ Master Timeline saved to: {out_path}")
    print(f"📸 {len(target_indices)*2} Individual frames saved to: {SINGULAR_DIR}")
    print("👉 You can now pick the single best Naive/Proposed pair from the 'singular_frames' folder for your Overleaf Figure 1!")

if __name__ == "__main__":
    main()