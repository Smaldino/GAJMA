import xml.etree.ElementTree as ET

def parse_manga_xml_full(xml_file_path: str) -> dict:
    """Parses XML and extracts frames + semantic elements."""
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    pages_container = root.find('pages')
    if pages_container is None:
        raise ValueError("Could not find 'pages' container.")

    page_data = {}
    for page in pages_container.findall('page'):
        page_idx = int(page.get('index'))
        frames, texts, faces, bodies, onomatopoeias = [], [], [], [], []

        # Extract Frames
        for frame in page.findall('frame'):
            xmin = int(frame.get('xmin'))
            ymin = int(frame.get('ymin'))
            xmax = int(frame.get('xmax'))
            ymax = int(frame.get('ymax'))
            frames.append({
                'id': frame.get('id'), 'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax,
                'center_x': (xmin + xmax) / 2, 'center_y': (ymin + ymax) / 2
            })

        # Extract Texts
        for text in page.findall('text'):
            texts.append({
                'xmin': int(text.get('xmin')), 'ymin': int(text.get('ymin')),
                'xmax': int(text.get('xmax')), 'ymax': int(text.get('ymax'))
            })

        # Extract Faces
        for face in page.findall('face'):
            faces.append({
                'xmin': int(face.get('xmin')), 'ymin': int(face.get('ymin')),
                'xmax': int(face.get('xmax')), 'ymax': int(face.get('ymax'))
            })

        # Extract Bodies
        for body in page.findall('body'):
            bodies.append({
                'xmin': int(body.get('xmin')), 'ymin': int(body.get('ymin')),
                'xmax': int(body.get('xmax')), 'ymax': int(body.get('ymax'))
            })

        # Extract Onomatopoeias
        for ope in page.findall('onomatopoeia'):
            xs = [int(ope.get(f'x{i}')) for i in range(20) if ope.get(f'x{i}')]
            ys = [int(ope.get(f'y{i}')) for i in range(20) if ope.get(f'y{i}')]
            if xs and ys:
                onomatopoeias.append({
                    'xmin': min(xs), 'ymin': min(ys),
                    'xmax': max(xs), 'ymax': max(ys)
                })

        page_data[page_idx] = {
            'frames': frames, 'texts': texts, 'faces': faces, 
            'bodies': bodies, 'onomatopoeias': onomatopoeias
        }
    return page_data