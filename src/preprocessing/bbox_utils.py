def do_rectangles_overlap(r1: dict, r2: dict) -> bool:
    """Check if two axis-aligned bounding boxes intersect."""
    return not (r1['xmax'] < r2['xmin'] or r1['xmin'] > r2['xmax'] or
                r1['ymax'] < r2['ymin'] or r1['ymin'] > r2['ymax'])

def filter_valid_frames(frames, texts, faces, bodies, onomatopoeias) -> list:
    """Filters out empty panels that contain no semantic content safely."""
    valid = []
    for frame in frames:
        # 1. Filter out tiny artifacts or rule line fragments
        width = frame['xmax'] - frame['xmin']
        height = frame['ymax'] - frame['ymin']
        if width < 50 or height < 50:
            continue

        # 2. Check if the frame overlaps with any storytelling element
        has_content = False
        
        # We process each dataset layer safely regardless of if it's a list or dict
        for items_collection in [texts, faces, bodies, onomatopoeias]:
            # If it's a dictionary, extract its values; if it's a list, use it directly
            if isinstance(items_collection, dict):
                current_items = items_collection.values()
            elif isinstance(items_collection, list):
                current_items = items_collection
            else:
                continue # Skip if empty/None
                
            if any(do_rectangles_overlap(frame, item) for item in current_items):
                has_content = True
                break
                
        if has_content:
            valid.append(frame)
        else:
            print(f"BBox Filter ✂️: Dropping empty panel frame: [{frame['xmin']}, {frame['ymin']}, {frame['xmax']}, {frame['ymax']}]")
            
    return valid