import os
import shutil
import glob
from pathlib import Path

# ==============================================================================
# CONFIGURATION: Update these paths to match your local setup
# ==============================================================================
CONFIG = {
    # Where your raw processed data currently lives (e.g., "data/processed")
    "SOURCE_BASE_DIR": "./data/processed",
    
    # The names of the 5 mangas you want to include
    "MANGAS": [
        "Akuhamu", 
        "TetsuSan", 
        "YouchienBoueigumi", 
        "OL_Lunch", 
        "KoukouNohitotachi"
    ],
    
    # Where you want the final structured Kaggle package to be built
    "OUTPUT_PACKAGE_DIR": "./manga-grid-panels"
}

def build_production_package():
    source_base = Path(CONFIG["SOURCE_BASE_DIR"])
    output_base = Path(CONFIG["OUTPUT_PACKAGE_DIR"])
    
    # 1. Define the target paths for images and manifests
    target_images_dir = output_base / "images"
    target_manifests_dir = output_base / "manifests"
    
    print(f"📁 Initializing target output framework at: {output_base.resolve()}")
    target_images_dir.mkdir(parents=True, exist_ok=True)
    target_manifests_dir.mkdir(parents=True, exist_ok=True)
    
    total_images_copied = 0
    total_manifests_copied = 0
    
    # 2. Process each manga one by one
    for manga in CONFIG["MANGAS"]:
        print(f"\n🔎 Processing cohort: '{manga}'...")
        manga_source_path = source_base / manga
        
        # Path configurations matching your local structure
        final_crops_dir = manga_source_path / "crops_final_training"
        manifest_source_path = manga_source_path / "dataset.jsonl"
        
        # Check if the manga directory even exists
        if not manga_source_path.exists():
            print(f"⚠️  Warning: Source directory for '{manga}' not found. Skipping.")
            continue
            
        # --- Handle Images ---
        if final_crops_dir.exists():
            # Build the subfolder: manga-grid-panels/images/MangaName/
            manga_target_img_dir = target_images_dir / manga
            manga_target_img_dir.mkdir(exist_ok=True)
            
            # Find all images inside crops_final_training
            found_images = glob.glob(os.path.join(final_crops_dir, "*.png"))
            
            for img_path in found_images:
                shutil.copy2(img_path, manga_target_img_dir / os.path.basename(img_path))
                total_images_copied += 1
            print(f"  ✅ Copied {len(found_images)} images into images/{manga}/")
        else:
            print(f"  ❌ Missing folder: '{final_crops_dir}' (Run your review script first!)")
            
        # --- Handle Manifests ---
        if manifest_source_path.exists():
            # Rename to match layout: manga-grid-panels/manifests/MangaName_meta_lat.jsonl
            target_manifest_filename = f"{manga}_meta_lat.jsonl"
            shutil.copy2(manifest_source_path, target_manifests_dir / target_manifest_filename)
            total_manifests_copied += 1
            print(f"  ✅ Copied manifest as manifests/{target_manifest_filename}")
        else:
            print(f"  ❌ Missing manifest file at: '{manifest_source_path}'")

    # 3. Summary Block
    print("\n" + "="*80)
    print("🎉 STRUCTURE COMPILATION COMPLETE!")
    print(f"   -> Output Directory: {output_base.resolve()}")
    print(f"   -> Total Images Packaged: {total_images_copied}")
    print(f"   -> Total Manifests Packaged: {total_manifests_copied}")
    print("="*80)
    print("\n💡 NEXT STEP: Zip the 'manga-grid-panels' folder and upload it to Kaggle!")

if __name__ == "__main__":
    build_production_package()