import os
import cv2
import glob
import argparse
import shutil

def review_manga_dataset(manga_name: str, base_dir: str = "data/processed"):
    """
    Interactively reviews pre-resized 512x512 panels from the flattened crops_resized folder,
    allowing manual selection and copying to the final training set.
    """
    manga_path = os.path.join(base_dir, manga_name)
    pipeline_resized_dir = os.path.join(manga_path, "crops_resized")
    final_training_dir = os.path.join(manga_path, "crops_final_training")

    if not os.path.exists(pipeline_resized_dir):
        print(f"❌ Error: Pipeline resized directory not found at {pipeline_resized_dir}")
        print("Please run your main automated preprocessing pipeline script first.")
        return

    # Ensure the finalized target training directory exists
    os.makedirs(final_training_dir, exist_ok=True)

    # 🔍 Gather all images directly from the flattened crops_resized folder
    # The new naming convention (pageXXX_panelYY.png) ensures they sort chronologically!
    found_images = sorted(glob.glob(os.path.join(pipeline_resized_dir, "*.png")))

    if not found_images:
        print(f"❌ No pre-resized panels found in: {pipeline_resized_dir}")
        return

    print(f"📚 Found {len(found_images)} panels in the flattened directory for '{manga_name}'.")
    print("\n⌨️  [INTERACTIVE SELECTION MODE ACTIVE]")
    print("   -> Reviewing fully padded & resized 512x512 canvas outcomes.")
    print("   -> Press 'y' to APPROVE a panel and commit it to your training set.")
    print("   -> Press 'n' to SKIP/DISCARD.")
    print("   -> Press 'a' to APPROVE ALL remaining panels automatically.")
    print("   -> Press 'q' to SAVE PROGRESS AND QUIT.")

    approved_counter = 0
    approve_all_mode = False  # Track if the user opted to fast-forward all entries

    for idx, img_path in enumerate(found_images):
        filename = os.path.basename(img_path)
        
        # Load the pre-resized panel matrix directly
        model_ready_panel = cv2.imread(img_path)
        if model_ready_panel is None:
            continue

        if not approve_all_mode:
            # Open the preview window container
            window_title = f"[{idx+1}/{len(found_images)}] Review: {filename}"
            cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
            cv2.imshow(window_title, model_ready_panel)
            
            # Force a safe default execution size mapping the 512x512 canvas geometry
            h, w = model_ready_panel.shape[:2]
            cv2.resizeWindow(window_title, w, h)
            
            # Keep window topmost on local Windows desktops
            cv2.setWindowProperty(window_title, cv2.WND_PROP_TOPMOST, 1)

            # Handle keyboard hardware inputs
            user_choice = None
            while user_choice not in [ord('y'), ord('n'), ord('a'), ord('q')]:
                user_choice = cv2.waitKey(0) & 0xFF

            cv2.destroyWindow(window_title)

            if user_choice == ord('q'):
                print("\n🛑 Review paused. Progress saved up to this item tracking point.")
                break

            if user_choice == ord('n'):
                print(f"🗑️  Discarded: {filename}")
                continue

            if user_choice == ord('a'):
                print("\n⚡ 'Approve All' mode activated! Processing all remaining frames...")
                approve_all_mode = True

        # Increment approved global tracker 
        approved_counter += 1
        
        # 🌟 CRITICAL: Keep the original filename (e.g., page001_panel01.png)
        # prepare_manifest.py relies on splitting by "_panel" to prevent cross-page transitions.
        new_filename = filename
        final_save_path = os.path.join(final_training_dir, new_filename)
        
        # High-speed file system file block replication without re-encoding quality loss
        shutil.copy2(img_path, final_save_path)
        
        if approve_all_mode:
            print(f"⚡ [AUTO-APPROVED] {filename} -> Saved to final training set")
        else:
            print(f"✅ Approved [{approved_counter}]: {filename} -> Saved to final training set")

    cv2.destroyAllWindows()
    print(f"\n🎉 Process Complete! Generated {approved_counter} approved training frames inside: {final_training_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flattened Manga Dataset Review Filter.")
    parser.add_argument("--manga", type=str, required=True, help="Name of the manga folder to review")
    # Kept for backward compatibility with run_pipeline.ps1, but no longer used for folder traversal
    parser.add_argument("--page_range", type=str, required=False, default="0-999", help="Deprecated: Now processes the whole flattened folder.")
    args = parser.parse_args()

    review_manga_dataset(manga_name=args.manga)