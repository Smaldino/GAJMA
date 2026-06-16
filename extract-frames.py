import cv2
import numpy as np
from pathlib import Path

# ==========================================
# CONFIGURATION (UPDATE THESE PATHS)
# ==========================================
# 👇 Point these to your actual Naive and Proposed videos
NAIVE_VIDEO = r"C:\Users\Fabbro\Documents\CODING\UNIVERSITA\CV\Post-Processing\video_input\baseline_outputs\Naive_pg001_p006_to_pg001_p008.mp4"
PROPOSED_VIDEO = r"C:\Users\Fabbro\Documents\CODING\UNIVERSITA\CV\Post-Processing\video_input\final_outputs\Proposed_pg001_p006_to_pg001_p008.mp4"

# Which frames to extract? (0 is start, 15 is end for a 16-frame video)
# We pick 5 key moments to show the evolution of the "melting" vs "rigid" balloons
TARGET_FRAMES = [0, 4, 8, 11, 15] 

OUTPUT_DIR = Path("thesis_screenshots")
OUTPUT_DIR.mkdir(exist_ok=True)
OUT_NAME = "manga_ablation_timeline"

# ==========================================
# EXTRACTION LOGIC
# ==========================================
def get_frame(cap, frame_idx):
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    if not ret:
        return None
    return frame

def add_label(frame, text, color_bgr):
    h, w = frame.shape[:2]
    # Add a semi-transparent banner at the top
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 45), color_bgr, -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    
    # Add text
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, text, (15, 32), font, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    return frame

def main():
    print("📸 Generating Timeline Contact Sheet...")
    cap_n = cv2.VideoCapture(NAIVE_VIDEO)
    cap_p = cv2.VideoCapture(PROPOSED_VIDEO)
    
    if not cap_n.isOpened() or not cap_p.isOpened():
        print("❌ Error: Could not open video files. Check paths!")
        return

    rows = []
    
    for idx, f_num in enumerate(TARGET_FRAMES):
        frame_n = get_frame(cap_n, f_num)
        frame_p = get_frame(cap_p, f_num)
        
        if frame_n is None or frame_p is None:
            print(f"⚠️ Warning: Could not read frame {f_num}. Skipping.")
            continue
            
        # Resize to match heights just in case they differ slightly
        h = min(frame_n.shape[0], frame_p.shape[0])
        w_n = int(frame_n.shape[1] * (h / frame_n.shape[0]))
        w_p = int(frame_p.shape[1] * (h / frame_p.shape[0]))
        
        frame_n = cv2.resize(frame_n, (w_n, h))
        frame_p = cv2.resize(frame_p, (w_p, h))
        
        # Add Labels (Red for Naive, Green for Proposed)
        frame_n = add_label(frame_n, f"Naive Baseline (Frame {f_num})", (0, 0, 180))
        frame_p = add_label(frame_p, f"Proposed Pipeline (Frame {f_num})", (0, 150, 0))
        
        # Stitch horizontally with a white divider
        divider = np.ones((h, 4, 3), dtype=np.uint8) * 255
        row = np.hstack((frame_n, divider, frame_p))
        rows.append(row)

    cap_n.release()
    cap_p.release()
    
    if not rows:
        print("❌ No frames were extracted.")
        return

    # Stack all rows vertically with a horizontal white divider
    h_row, w_row = rows[0].shape[:2]
    h_divider = np.ones((4, w_row, 3), dtype=np.uint8) * 255
    
    final_grid = []
    for i, row in enumerate(rows):
        final_grid.append(row)
        if i < len(rows) - 1:
            final_grid.append(h_divider)
            
    final_image = np.vstack(final_grid)
    
    # Save the masterpiece
    out_path = OUTPUT_DIR / f"{OUT_NAME}.png"
    cv2.imwrite(str(out_path), final_image)
    print(f"\n🎉 SUCCESS! Saved timeline grid to: {out_path}")
    print("👉 Open this image, find the row where the text melting is most obvious, and crop it for your LaTeX Figure 1!")

if __name__ == "__main__":
    main()