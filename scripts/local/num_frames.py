import cv2
import os
from pathlib import Path

GAJMA_ROOT = Path(__file__).resolve().parents[2]
folder_path = str(GAJMA_ROOT / "data" / "videos")

# 1. Check if the folder actually exists at that path
if not os.path.exists(folder_path):
    print(f"Error: Python cannot find any file at '{folder_path}'. Check your paths.")
else:
    for video in os.listdir(folder_path):
        video_path = os.path.join(folder_path, video)
        
        # Check if it's a file and has a video extension
        if os.path.isfile(video_path) and video.lower().endswith(('.mp4', '.avi', '.mkv')):
            
            # OPTIONAL: Uncomment the next 2 lines if you ONLY want to check the raw 8fps ToonCrafter videos 
            # and want to ignore the 32fps RIFE smoothed videos or the final concatenated master video.
            # if "_smoothed" in video or "Full_Manga" in video:
            #     continue

            print(f"\n{'='*50}")
            print(f"🎬 Processing: {video}")
            print(f"{'='*50}")
            
            video_capture = cv2.VideoCapture(video_path)

            if not video_capture.isOpened():
                print("⛔ Error: The file exists, but OpenCV could not open it. It might be corrupt or unsupported.")
            else:
                total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = video_capture.get(cv2.CAP_PROP_FPS)

                # 2. Final safety check before doing the math
                if fps > 0:
                    duration_seconds = total_frames / fps
                    
                    # FIX: Changed 'os.path.basename(folder_path)' to 'video'
                    print(f"📂 File: {video}") 
                    print(f"🖼️ Total Frames: {total_frames}")
                    print(f"🎞️ FPS: {fps}")
                    print(f"⏱️ Duration: {duration_seconds:.2f} seconds")
                else:
                    print("⛔ Error: The video opened, but the FPS metadata is reading as 0.0.")

                # 3. Always release the capture object to free up memory
                video_capture.release()
                
print("\n✅ Finished scanning all videos in the folder.")