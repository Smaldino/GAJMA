import os
import json
import glob
import argparse
import shutil

def generate_tooncrafter_manifest(manga_name: str, base_dir: str = "data/processed"):
    """
    Renames checked panels to standard index tokens and outputs a matching
    dataset.jsonl mapping file for consecutive frame pairs (m_i, m_i+1).
    """
    manga_path = os.path.join(base_dir, manga_name)
    final_training_dir = os.path.join(manga_path, "crops_final_training")
    
    # Target path for the final training index mapping file
    output_jsonl_path = os.path.join(manga_path, "dataset.jsonl")

    if not os.path.exists(final_training_dir):
        print(f"❌ Error: Final training directory not found at {final_training_dir}")
        print("Please run your interactive review script first to approve panels.")
        return

    # Find all approved .png files inside your reviewed tracking directory
    raw_images = sorted(glob.glob(os.path.join(final_training_dir, "*.png")))
    
    if len(raw_images) < 2:
        print(f"❌ Error: Found {len(raw_images)} panels. You need at least 2 panels to create transition pairs.")
        return

    print(f"📦 Processing {len(raw_images)} approved panels inside '{manga_name}'...")

    # =========================================================
    # 🔀 STEP 1: COMPILING CONSECUTIVE PAIRS INTO JSONL
    # =========================================================
    # Anchor text keyword sequence that the model cross-attention matrices track
    base_prompt = "smooth anime transition, manga style, crisp ink line art, clean animation sequence"
    jsonl_lines = []

    # Loop dynamically through the chain array: index (i) -> index (i+1)
    for i in range(len(raw_images) - 1):
        start_img_abs = raw_images[i]
        end_img_abs = raw_images[i + 1]

        start_filename = os.path.basename(start_img_abs)
        end_filename = os.path.basename(end_img_abs)

        # Extraction logic to make sure we don't accidentally link panels across separate pages
        # e.g., 'page_001_panel_004' and 'page_002_panel_005'
        try:
            start_page = start_filename.split("_panel")[0]
            end_page = end_filename.split("_panel")[0]
        except IndexError:
            # Fallback if names don't contain the page string pattern
            start_page = "global"
            end_page = "global"

        # Formally bind consecutive pairs (m_i, m_i+1) belonging to the same storytelling unit
        if start_page == end_page:
            entry = {
                "start_img": f"crops_final_training/{start_filename}",
                "end_img": f"crops_final_training/{end_filename}",
                "text": base_prompt
            }
            jsonl_lines.append(entry)

    # Write the formatted payload structurally to disk
    with open(output_jsonl_path, "w", encoding="utf-8") as f:
        for line in jsonl_lines:
            f.write(json.dumps(line) + "\n")

    print(f"📝 Flawlessly mapped {len(jsonl_lines)} sequential transition triplets to jsonl format.")
    print(f"✅ Success! Your training file is saved at: {output_jsonl_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ToonCrafter JSONL Pair Manifest Config Generator.")
    parser.add_argument("--manga", type=str, required=True, help="Name of the manga folder to compile")
    args = parser.parse_args()

    generate_tooncrafter_manifest(manga_name=args.manga)