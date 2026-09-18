import json
import xml.etree.ElementTree as ET
import os

def get_paths(svg_file):
    if not os.path.exists(svg_file): return []
    tree = ET.parse(svg_file)
    root = tree.getroot()
    # potrace generates paths in the <g> tags
    paths = []
    # Handle namespaces
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    for path in root.findall('.//svg:path', ns) + root.findall('.//path'):
        if 'd' in path.attrib:
            paths.append(path.attrib['d'])
    return paths

os.makedirs('scratch/assets', exist_ok=True)
data = {
    'wave': get_paths('scratch/build_assets/wave_raw.svg'),
    'ttc': get_paths('scratch/build_assets/text_raw.svg'), # We need to separate TTC from subtitle?
}
# wait, text_raw.svg has TTC and subtitle together. 
