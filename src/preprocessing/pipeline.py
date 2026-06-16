import os
import cv2
import glob
import numpy as np
from pycocotools import mask as coco_mask
import xml.etree.ElementTree as ET

# Assuming these imports exist in your project structure
from .xml_parser import parse_manga_xml_full  
from .annotation_utils import find_merged_xml
from .bbox_utils import filter_valid_frames
from .reading_order import sort_frames_manga_style
from .image_utils import prepare_tooncrafter_input

def pad_and_resize_to_square(img_np, width_target_size=512, height_target_size=320) -> np.ndarray:
    """
    Pads an image crop to a perfect square using a clean WHITE background, 
    then resizes it to target_size x target_size.
    """
    h, w = img_np.shape[:2]
    max_dim = max(h, w)
    pad_x, pad_y = (max_dim - w) // 2, (max_dim - h) // 2

    # Using [255, 255, 255] for a crisp, native white manga gutter background
    padded = cv2.copyMakeBorder(img_np, pad_y, pad_y, pad_x, pad_x, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    resized = cv2.resize(padded, (width_target_size, height_target_size), interpolation=cv2.INTER_AREA)
    return resized

def process_specific_page(manga_name: str, page_number: int, start_panel_idx: int = 0, 
                          base_path: str = "Manga109", output_dir: str = "data/processed",
                          create_visualization: bool = True, width_target_size: int = 512, height_target_size: int = 320,
                          consolidated_output: bool = False, remove_text: bool = True):
    """
    Processes a specific page and saves all outputs to a user-defined destination folder.
    Separates panel detection and speech bubble detection visualizations.
    
    :param remove_text: If True, applies Clean Canvas inpainting. If False, keeps raw text (Naive Baseline).
    """
    
    # region 1. Locate & Parse Master Unified XML
    try:
        xml_path = find_merged_xml(manga_name, base_path)
        print(f"📄 Using Master XML: {xml_path}")
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        pages_node = root.find('pages')
        target_page_node = None
        
        if pages_node is not None:
            for p in pages_node.findall('page'):
                if int(p.get('index', 0)) == page_number:
                    target_page_node = p
                    break
                    
        if target_page_node is None:
            raise ValueError(f"Page index {page_number} not found in master dataset XML mappings.")
    except Exception as e:
        print(f"❌ XML Error: {e}")
        return 0
    # endregion

    # region 2. Locate & Load Image
    manga_img_folder = os.path.join(base_path, "manga", manga_name)
    if not os.path.exists(manga_img_folder):
        raise FileNotFoundError(f"Manga image folder not found: {manga_img_folder}")

    potential_names = [
        f"{str(page_number).zfill(3)}.jpg", f"{str(page_number).zfill(4)}.jpg",
        f"{page_number}.jpg", f"{str(page_number+1).zfill(3)}.jpg", f"{str(page_number+1).zfill(4)}.jpg"
    ]
    image_path = next((os.path.join(manga_img_folder, n) for n in potential_names if os.path.exists(os.path.join(manga_img_folder, n))), None)
    
    if not image_path:
        raise FileNotFoundError(f"Could not find image for page {page_number}")
    print(f"🖼️ Processing Image: {image_path}")

    img = cv2.imread(image_path)
    if img is None:
        raise Exception(f"Could not load image from {image_path}")
    h, w = img.shape[:2]

    page_data_all = parse_manga_xml_full(xml_path)
    page_info = page_data_all[page_number]
    all_frames = page_info['frames']
    texts = page_info['texts']
    onomatopoeias = page_info['onomatopoeias']

    if not all_frames:
        print("⚠️ No frames found on this page structure.")
        return 0
    # endregion

    # region 3: Flattened Destination Folders
    output_dir = os.path.abspath(output_dir)
    manga_keeper_base = os.path.join(output_dir, manga_name)
    
    page_folder_str = f"page_{str(page_number).zfill(3)}" 

    # Add a suffix to the folder name if we are generating the naive baseline
    suffix = "_naive" if not remove_text else ""
    prepared_dir = os.path.join(manga_keeper_base, f"crops_resized{suffix}")
    
    detected_panel_dir = os.path.join(manga_keeper_base, f"detected_panels{suffix}") if create_visualization else None
    detected_speech_dir = os.path.join(manga_keeper_base, f"detected_speech{suffix}") if create_visualization else None

    os.makedirs(prepared_dir, exist_ok=True)
    if detected_panel_dir:
        os.makedirs(detected_panel_dir, exist_ok=True)
    if detected_speech_dir:
        os.makedirs(detected_speech_dir, exist_ok=True)
    # endregion

    # region 4: SURGICAL TEXT INPAINTING (The "Clean Canvas" Strategy)
    clean_img = img.copy()
    text_mask = np.zeros((h, w), dtype=np.uint8)

    if remove_text:
        # 1. Draw masks for Text blocks using Bounding Boxes
        for txt in texts:
            x1 = max(0, int(txt.get('xmin', txt.get('x', 0))))
            y1 = max(0, int(txt.get('ymin', txt.get('y', 0))))
            x2 = min(w, int(txt.get('xmax', txt.get('x2', 0))))
            y2 = min(h, int(txt.get('ymax', txt.get('y2', 0))))
            if y2 > y1 and x2 > x1:
                cv2.rectangle(text_mask, (x1, y1), (x2, y2), 255, -1)

        # 2. Draw masks for Onomatopoeia using Polygons
        for ope in onomatopoeias:
            xs = [int(ope.get(f'x{i}')) for i in range(20) if ope.get(f'x{i}')]
            ys = [int(ope.get(f'y{i}')) for i in range(20) if ope.get(f'y{i}')]
            if len(xs) > 2 and len(ys) > 2:
                pts = np.array(list(zip(xs, ys)), dtype=np.int32)
                cv2.fillPoly(text_mask, [pts], 255)

        # 3. Dilate the mask slightly to cover "ink bleed" or drop shadows around text
        kernel = np.ones((5, 5), dtype=np.uint8)
        text_mask = cv2.dilate(text_mask, kernel, iterations=1)

        # 4. INPAINT: Mathematically erase the text and fill with surrounding pixels
        if np.any(text_mask > 0):
            clean_img = cv2.inpaint(clean_img, text_mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
            print(f"✨ Inpainted {len(texts)} text blocks and {len(onomatopoeias)} sound effects.")
        else:
            print("ℹ️ No text detected on this panel. Skipping inpaint.")
    else:
        print("ℹ️ Text removal disabled (Naive Baseline). Keeping original text and onomatopoeia.")

    masked_img = clean_img 
    # endregion

    # region 5: FILTER & SORT PANELS
    valid_frames = filter_valid_frames(all_frames, page_info['texts'], page_info['faces'],
                                       page_info['bodies'], page_info['onomatopoeias'])
    if not valid_frames:
        print(f"⏩ Page {page_number} skipped: No semantic content.")
        return 0

    sorted_frames = sort_frames_manga_style(valid_frames)
    #endregion

    # region 6: VISUALIZATION (SEPARATED)
    panel_vis = masked_img.copy() if create_visualization else None
    speech_vis = masked_img.copy() if create_visualization else None

    if create_visualization:
        # --- Draw Text Bounding Boxes on speech_vis ---
        for i, txt in enumerate(texts):
            x1 = max(0, int(txt.get('xmin', txt.get('x', 0))))
            y1 = max(0, int(txt.get('ymin', txt.get('y', 0))))
            x2 = min(w, int(txt.get('xmax', txt.get('x2', 0))))
            y2 = min(h, int(txt.get('ymax', txt.get('y2', 0))))
            
            if y2 > y1 and x2 > x1:
                cv2.rectangle(speech_vis, (x1, y1), (x2, y2), (0, 255, 0), 2) # Green
                cv2.putText(speech_vis, f"T_{i}", (x1 + 5, y1 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
        
        # Draw the actual inpainted text mask contours on speech_vis (Only if inpainting was run)
        if remove_text and np.any(text_mask > 0):
            contours, _ = cv2.findContours(text_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                x, y, wc, hc = cv2.boundingRect(cnt)
                if wc * hc > 100: # Filter out tiny noise
                    cv2.drawContours(speech_vis, [cnt], -1, (0, 255, 255), 2) # Cyan
    # endregion

    # region 7: AUTOMATED PROCESSING AND SAVING
    local_saved_count = 0
    for i, frame in enumerate(sorted_frames):
        xmin, ymin = max(0, frame['xmin']), max(0, frame['ymin'])
        xmax, ymax = min(w, frame['xmax']), min(h, frame['ymax'])

        raw_crop = masked_img[ymin:ymax, xmin:xmax]
        
        # FIX: Corrected parameter names to match the function signature
        model_ready_panel = pad_and_resize_to_square(raw_crop, width_target_size=width_target_size, height_target_size=height_target_size)

        resized_filename = f"page{str(page_number).zfill(3)}_panel{str(i + 1).zfill(2)}.png"
        cv2.imwrite(os.path.join(prepared_dir, resized_filename), model_ready_panel)

        if create_visualization and panel_vis is not None:
            cv2.rectangle(panel_vis, (xmin, ymin), (xmax, ymax), (255, 0, 0), 2) # Blue
            cv2.putText(panel_vis, f"P{i+1}", (xmin + 5, ymin + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
        local_saved_count += 1

    if local_saved_count == 0:
        return 0

    if create_visualization:
        panel_vis_filename = f"{page_folder_str}_panels.jpg"
        cv2.imwrite(os.path.join(detected_panel_dir, panel_vis_filename), panel_vis)

        speech_vis_filename = f"{page_folder_str}_speech.jpg"
        cv2.imwrite(os.path.join(detected_speech_dir, speech_vis_filename), speech_vis)

    print(f"✅ Saved {local_saved_count} panels to: {prepared_dir}")
    return local_saved_count
    # endregion


def process_all_pages_of_manga(manga_name: str, base_path: str = "Manga109",
                               output_dir: str = "data/processed",
                               create_visualization: bool = True, 
                               width_target_size: int = 512, height_target_size: int = 320,
                               remove_text: bool = True):
    """Process all pages automatically while updating a running index parameter across loops."""
    
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        xml_path = find_merged_xml(manga_name, base_path)
        mode_str = "Clean Canvas" if remove_text else "NAIVE BASELINE (Raw Text)"
        print(f"📚 Mass automated compilation triggering for: {manga_name} [{mode_str}]")
        
        tree = ET.parse(xml_path)
        pages_node = tree.getroot().find('pages')
        if pages_node is None:
            print(f"❌ Error structure parsed out for {manga_name}")
            return
            
        page_indices = sorted([int(p.get('index', 0)) for p in pages_node.findall('page')])
    except Exception as e:
        print(f"❌ Failed to load XML for {manga_name}: {e}")
        return
    
    running_panel_total = 0
    valid_story_pages = []

    for page_num in page_indices:
        try:
            print(f"\n{'-'*50}\n🔄 Processing page {page_num}...")
            saved_on_page = process_specific_page(
                manga_name=manga_name, page_number=page_num, 
                start_panel_idx=running_panel_total, base_path=base_path,
                output_dir=output_dir, create_visualization=create_visualization,
                width_target_size=width_target_size, height_target_size=height_target_size,
                consolidated_output=True,
                remove_text=remove_text # 👈 Passed down to the page processor
            )
            running_panel_total += saved_on_page
            if saved_on_page >= 2:
                valid_story_pages.append((page_num, running_panel_total - saved_on_page))
        except Exception as e:
            print(f"⚠️ Exception on page {page_num}: {e}")

    # Final Summary
    print(f"\n{'='*50}")
    print(f"🎉 Mass Processing Complete!")
    print(f"📊 Total panels processed: {running_panel_total}")
    print(f"📖 Pages with valid transitions (>=2 panels): {len(valid_story_pages)}")
    print(f"📁 All outputs saved in: {output_dir}")
    print(f"{'='*50}")