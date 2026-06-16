import os
import glob
import cv2
import shutil
import numpy as np
from typing import Optional, Union
from tqdm import tqdm

def pad_and_resize_image(input_path: str, output_path: str, target_size: int = 512) -> bool:
    """Pads image to square using WHITE backgrounds instead of black, and resizes."""
    img = cv2.imread(input_path)
    if img is None:
        return False

    h, w = img.shape[:2]
    max_dim = max(h, w)
    pad_x, pad_y = (max_dim - w) // 2, (max_dim - h) // 2

    # FIX: Value=[255, 255, 255] matches manga gutters/borders perfectly
    padded = cv2.copyMakeBorder(img, pad_y, pad_y, pad_x, pad_x, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    resized = cv2.resize(padded, (target_size, target_size), interpolation=cv2.INTER_AREA)
    cv2.imwrite(output_path, resized)
    return True

def process_crops_folder(crops_dir: str, output_dir: str, target_size: int = 512, show_progress: bool = True) -> None:
    """Batch pads and resizes all crops in a directory."""
    os.makedirs(output_dir, exist_ok=True)
    files = glob.glob(os.path.join(crops_dir, "*.[jp][pn][g]"))

    if not files:
        print(f"No images found in {crops_dir}")
        return

    # Use tqdm progress bar
    if show_progress:
        file_iter = tqdm(files, desc="Padding & resizing", unit="img", leave=True)
    else:
        file_iter = files

    success = 0
    total = len(files)

    for idx, f in enumerate(file_iter, 1):
        if pad_and_resize_image(f, os.path.join(output_dir, os.path.basename(f).rsplit('.', 1)[0] + '.png'), target_size):
            success += 1

        # Update progress description with count
        if show_progress and hasattr(file_iter, 'set_description'):
            file_iter.set_description(f"Processing [{idx}/{total}]")

    print(f"Processed {success}/{total} images -> {output_dir}")

import os
import shutil

def prepare_tooncrafter_input(src_dir: str, output_dir: str, panel_indices: list, prompt: str = "anime style"):
    """
    Formats cropped panels for ToonCrafter's --interp mode.
    Creates [P1, P2, P2, P3, P3, P4...] sequence + matching prompt lines.
    """
    os.makedirs(output_dir, exist_ok=True)
    if len(panel_indices) < 2:
        print("⚠️  Need at least 2 panels to generate transitions.")
        return output_dir

    n_transitions = len(panel_indices) - 1

    # 1. Write prompts (one per transition)
    with open(os.path.join(output_dir, "prompt.txt"), "w") as f:
        for _ in range(n_transitions):
            f.write(prompt + "\n")

    # 2. Build strict even-length sequence: [P1, P2, P2, P3, P3, P4...]
    paired_indices = []
    for i in range(n_transitions):
        paired_indices.append(panel_indices[i])     # Start frame
        paired_indices.append(panel_indices[i+1])   # End frame

    # 3. Copy & rename sequentially
    for idx, panel_num in enumerate(paired_indices, start=1):
        # Try PNG first, fallback to JPG
        src_file = next((
            os.path.join(src_dir, f"panel_{str(panel_num).zfill(3)}.{ext}")
            for ext in ["png", "jpg"]
        ), None)
        if not src_file or not os.path.exists(src_file):
            raise FileNotFoundError(f"Missing panel {panel_num} in {src_dir}")

        dst_file = os.path.join(output_dir, f"{str(idx).zfill(2)}.png")
        shutil.copy2(src_file, dst_file)

    print(f"✅ Prepared {len(paired_indices)} files for {n_transitions} transitions in {output_dir}")
    return output_dir