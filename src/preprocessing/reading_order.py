def sort_frames_manga_style(frames: list, threshold: int = 50) -> list:
    """Sorts frames in manga reading order: Right→Left columns, Top→Bottom within columns."""
    if not frames: return []
    
    frames_by_x = sorted(frames, key=lambda k: k['center_x'])
    columns, current = [], [frames_by_x[0]]
    
    for i in range(1, len(frames_by_x)):
        if abs(frames_by_x[i]['center_x'] - current[-1]['center_x']) < threshold:
            current.append(frames_by_x[i])
        else:
            columns.append(current)
            current = [frames_by_x[i]]
    columns.append(current)
    
    columns.sort(key=lambda c: sum(f['center_x'] for f in c) / len(c), reverse=True)
    
    final = []
    for col in columns:
        final.extend(sorted(col, key=lambda k: k['center_y']))
    return final