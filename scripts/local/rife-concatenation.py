# ==============================================================================
# MASTER PIPELINE: INTERPOLATION & COMPILATION (FLAT OR STYLE-BASED)
# ==============================================================================
import os
import glob
import re
import subprocess
import shutil

# 0. CONFIGURATION
from pathlib import Path
GAJMA_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = GAJMA_ROOT / "data" / "videos" / "z-others"

# 👇 SET TO FALSE to process flat/specific files without creating style folders
USE_STYLE_FOLDERS = False

# 👇 Optional: Specify exact files to process if USE_STYLE_FOLDERS is False. 
# Leave empty [] to automatically process ALL .mp4 files in INPUT_DIR.
SPECIFIC_FILES = [
]

STYLES = ["Parallax_Smooth", "Parallax_Intense", "Dolly_Subtle", "Dolly_Bokeh", "Dynamic_Controlled", "Rack_Focus"]

# ==============================================================================
# HELPER FUNCTION: Interpolate and Concatenate
# ==============================================================================
def interpolate_and_concat(video_list, output_dir, output_name):
    """Interpolates a list of videos to 32fps and stitches them chronologically."""
    smoothed_dir = os.path.join(output_dir, "smoothed_clips")
    final_dir = os.path.join(output_dir, "final_compilation")
    os.makedirs(smoothed_dir, exist_ok=True)
    os.makedirs(final_dir, exist_ok=True)
    
    smoothed_list = []
    
    # 1. Interpolate each video
    for video_path in video_list:
        base_name = os.path.basename(video_path)
        out_video = os.path.join(smoothed_dir, base_name.replace(".mp4", "_smoothed.mp4"))
        
        # Skip if already smoothed (saves time if script is restarted)
        if os.path.exists(out_video):
            print(f"  ⏭️ Already smoothed: {base_name}")
            smoothed_list.append(out_video)
            continue

        print(f"  🧠 Interpolating: {base_name}")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-filter:v", "minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1:fps=32'",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            out_video
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        smoothed_list.append(out_video)
        
    # 2. Sort chronologically based on pgXXX_pYYY_to
    def sort_key(filepath):
        match = re.search(r"pg(\d+)_p(\d+)_to", os.path.basename(filepath))
        if match:
            # Cast to int so page 10 correctly comes after page 9
            return (int(match.group(1)), int(match.group(2)))
        return (999, 999) # Fallback for unmatching names
        
    smoothed_list.sort(key=sort_key)
    
    # 3. Concatenate
    concat_file = os.path.join(output_dir, "temp_concat.txt")
    with open(concat_file, "w", encoding="utf-8") as f:
        for file in smoothed_list:
            # FFmpeg concat demuxer requires forward slashes on Windows
            safe_path = file.replace('\\', '/') 
            f.write(f"file '{safe_path}'\n")
            
    final_output = os.path.join(final_dir, output_name)
    print(f"🚀 Stitching {len(smoothed_list)} clips into {final_output}...")
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-r", "32", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        final_output
    ], check=True)
    
    os.remove(concat_file)
    print(f"✅ Finished: {output_name}\n")


# ==============================================================================
# EXECUTION LOGIC
# ==============================================================================
if USE_STYLE_FOLDERS:
    print("📂 MODE: Style-Based Folder Organization")
    
    # 1. ORGANIZE FILES INTO STYLE FOLDERS
    for style in STYLES:
        style_dir = os.path.join(INPUT_DIR, style)
        os.makedirs(style_dir, exist_ok=True)
        
        for video_path in glob.glob(os.path.join(INPUT_DIR, f"*{style}*.mp4")):
            if os.path.isfile(video_path):
                shutil.move(video_path, os.path.join(style_dir, os.path.basename(video_path)))

    # 2. PROCESS EACH STYLE FOLDER
    for style in STYLES:
        style_dir = os.path.join(INPUT_DIR, style)
        folder_videos = [f for f in glob.glob(os.path.join(style_dir, "*.mp4")) if "smoothed" not in f]
        if not folder_videos: 
            continue
        
        print(f"\n📁 Processing Style: {style}")
        interpolate_and_concat(folder_videos, style_dir, f"{style}_Final_32fps.mp4")

else:
    print("📂 MODE: Flat / Specific Files Processing (No Style Folders)")
    
    # Determine which files to process
    if SPECIFIC_FILES:
        target_videos = [f for f in SPECIFIC_FILES if os.path.exists(f) and "smoothed" not in f]
    else:
        # Grab all .mp4 files in the root INPUT_DIR, excluding already smoothed ones
        target_videos = [f for f in glob.glob(os.path.join(INPUT_DIR, "*.mp4")) if "smoothed" not in f]
        
    if not target_videos:
        print("⚠️ No target videos found to process.")
    else:
        print(f"🎬 Found {len(target_videos)} videos to process.")
        interpolate_and_concat(target_videos, INPUT_DIR, "Full_Manga_Animation_32fps.mp4")

print("\n🎉 ALL COMPILATIONS COMPLETE!")