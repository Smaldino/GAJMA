import os
import xml.etree.ElementTree as ET

def find_manga_files(manga_name: str, base_path: str = "Manga109") -> list:
    """Searches Manga109 annotation folders for a manga's XML files using a uniform filename."""
    subfolders = [
        "annotations",
        "annotations_COO",
        "annotations Manga 109Dialog",
        "annotations_MangaSeg"  # Your converted XML folder path
    ]
    target = f"{manga_name}.xml"
    found = []
    
    for subdir in subfolders:
        path = os.path.join(base_path, subdir, target)
        if os.path.exists(path):
            # Pass a tuple: (full_file_path, is_manga_seg_folder_flag)
            found.append((path, "annotations_MangaSeg" in subdir))
            print(f"  Found: {path}")
    return found

def merge_xml_files(file_tuples: list, output_path: str) -> None:
    """Merges multiple Manga109 XML layers into one master timeline file."""
    if not file_tuples:
        print("No input files found to merge.")
        return

    merged_data = {}
    page_attrs = {}
    
    for file_path, is_manga_seg in file_tuples:
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # ---------------------------------------------------------
            # BRANCH A: PARSING STANDARD MANGA109 STRUCTURAL REGIONS
            # ---------------------------------------------------------
            if not is_manga_seg:
                pages = root.find('pages')
                if pages is None: 
                    continue
                
                for page in pages.findall('page'):
                    idx = int(page.get('index', 0))
                    if idx not in page_attrs:
                        page_attrs[idx] = {'width': page.get('width'), 'height': page.get('height')}
                    if idx not in merged_data:
                        merged_data[idx] = []
                        
                    for child in page:
                        merged_data[idx].append(child)
                        
            # ---------------------------------------------------------
            # BRANCH B: PARSING MANGASEG SEGMENTATION MASKS
            # ---------------------------------------------------------
            else:
                annotations = root.find('annotations')
                images = root.find('images')
                if annotations is None or images is None:
                    continue
                
                # Build an internal image_id -> page_index timeline lookup map
                image_id_to_index = {}
                for img in images.findall('image'):
                    img_id = img.find('id').text
                    file_name = img.find('file_name').text
                    try:
                        # Extracts integers from names like "Akuhamu/002.jpg" -> 2
                        page_num = int(os.path.splitext(os.path.basename(file_name))[0])
                        image_id_to_index[img_id] = page_num
                    except ValueError:
                        continue
                
                # Assign annotations to their corresponding page index arrays
                for ann in annotations.findall('annotation'):
                    img_id_el = ann.find('image_id')
                    if img_id_el is not None and img_id_el.text in image_id_to_index:
                        idx = image_id_to_index[img_id_el.text]
                        
                        if idx not in merged_data:
                            merged_data[idx] = []
                        
                        # Wrap the pixel-level data tightly to prevent layout scattering
                        seg_wrapper = ET.Element('segmentation_mask')
                        for sub_child in ann:
                            seg_wrapper.append(sub_child)
                        
                        merged_data[idx].append(seg_wrapper)
                        
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

    # ---------------------------------------------------------
    # GENERATE THE UNIFIED master DOM DOCUMENT
    # ---------------------------------------------------------
    new_root = ET.Element('book')
    new_root.set('title', 'Merged_Annotations')
    pages_new = ET.SubElement(new_root, 'pages')
    
    for idx in sorted(merged_data.keys()):
        new_page = ET.SubElement(pages_new, 'page')
        new_page.set('index', str(idx))
        
        if idx in page_attrs:
            if page_attrs[idx]['width']: new_page.set('width', page_attrs[idx]['width'])
            if page_attrs[idx]['height']: new_page.set('height', page_attrs[idx]['height'])
        
        # Deduplicate elements by tracking processed ID values safely
        seen_ids = set()
        for elem in merged_data[idx]:
            eid = elem.get('id')
            if eid:
                if eid in seen_ids:
                    continue
                seen_ids.add(eid)
            
            new_page.append(elem)

    tree = ET.ElementTree(new_root)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    print(f"🎉 Successfully completed master build -> {output_path}")

def find_merged_xml(manga_name: str, base_path: str = "Manga109") -> str:
    """Locates the pre-merged XML file, or creates it if not found."""
    path = os.path.join(base_path, "annotations_merged", f"{manga_name}_Complete.xml")
    if os.path.exists(path):
        return path
    
    print(f"Merged XML not found at {path}. Creating merged XML...")
    xml_files_tuples = find_manga_files(manga_name, base_path)
    
    if not xml_files_tuples:
        raise FileNotFoundError(f"No XML files located for manga: {manga_name}")
    
    os.makedirs(os.path.dirname(path), exist_ok=True)
    merge_xml_files(xml_files_tuples, path)
    return path